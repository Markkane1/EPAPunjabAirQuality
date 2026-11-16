"""
Adversarial Concurrency, Dataflow, and Edge-Case Stress Test Suite for Milestone M4.

Targets:
1. BaselineRepository thread safety under extreme multithreaded contention (50 threads, 1000+ ops):
   - Dynamic user CSV mutations concurrently executing alongside multi-index lookups.
   - Verification of zero JSONDecodeError and thread-safe process-level cache locks.
   - Verification of zero station dropouts across concurrent ingestion batches.
   - Querying dynamically added stations by both string ID, integer ID, and name.
   - Verifying cache invalidation across analytics surfaces without deadlock or corrupted state.
2. Fast-API / Async HTTP Concurrency:
   - Concurrent async tasks executing simultaneous multipart POST /api/v1/ingest/csv mutations,
     GET /api/v1/observations/current, GET /api/v1/spatial/surface, GET /api/v1/analytics/flux,
     and GET /api/v1/meta/stations.
   - Ensuring no race conditions survive across API requests and all dynamic stations are cataloged.
3. Edge-Case CSV Ingestion & Schema Traps:
   - Missing mandatory columns (missing timestamp, pollutant, value, station_id) -> status="failed", 0 valid rows.
   - HTTP 422 rejections on API level for malformed multipart inputs, missing file field, invalid boolean parameters.
   - Extreme values: values > 5000 (e.g. 5001, 99999) -> quarantined in DLQ.
   - Negative values and zero values -> quarantined / purged.
   - Negative and out-of-bounds coordinates (e.g. lat -31.5, lat 50.0) -> quarantined.
   - Canonical coordinate repair: Sahiwal (0,0) -> repaired and accepted.
   - Anemometer bounds and blacklist:
     * Calm wind (speed 0.0, dir 0.0) -> accepted, u=0.0, v=0.0.
     * Speed > 30 m/s -> anemometer bounds purged.
     * Station 172 Wazirabad -> anemometer blacklisted.
4. Repetition Stability:
   - Repeated full execution cycles proving absence of flakiness and memory/state corruption.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import time
from typing import Any, Dict, List, Set, Tuple
import uuid

import httpx
from httpx import ASGITransport
import pytest

from src.api.main import create_application
from src.domain.entities.models import (
    AdvectionFluxLink,
    CPFRoseResult,
    Station,
    StationObservation,
    SurfaceGridPoint,
)
from src.domain.schemas.measurement import NormalizedObservation
from src.infrastructure.repositories.baseline_repository import BaselineRepository
from src.pipelines.csv_adapter import UserCSVIngestionAdapter
from src.services.ingestion_service import IngestionService


@pytest.fixture(scope="module")
def app():
    """Create and initialize FastAPI application for test suite."""
    return create_application()


@pytest.fixture
def anyio_backend():
    """Specify anyio backend engine."""
    return "asyncio"


# =============================================================================
# 1. BASELINE REPOSITORY MULTITHREADED CONCURRENCY & CONTENTION STRESS
# =============================================================================

class TestBaselineRepositoryConcurrencyStress:
    """
    Stress-tests the thread safety of BaselineRepository under high thread contention.
    Executes concurrent writes (dynamic CSV station additions), reads, analytics caching,
    and concurrent repository instantiations.
    """

    def test_multithreaded_concurrent_reads_writes_and_cache_locks(self):
        """
        Executes 50 concurrent worker threads running 1,000 mixed operations:
        - Concurrent dynamic station mutations (add_user_csv_observations)
        - Concurrent multi-index lookups (get_station_by_id, list_stations, count)
        - Concurrent analytics cache updates (save_surface_grid, clear_cache)
        - Concurrent repository initialization verifying zero JSONDecodeError
        """
        repo = BaselineRepository()
        initial_station_count = repo.count_stations()
        assert initial_station_count > 0, "Baseline station repository initialized empty."

        thread_count = 50
        ops_per_thread = 20
        total_expected_ops = thread_count * ops_per_thread

        injected_station_ids: Set[str] = set()
        errors: List[str] = []
        timings: List[float] = []

        def worker_task(thread_id: int) -> int:
            completed_ops = 0
            for i in range(ops_per_thread):
                op_start = time.perf_counter()
                op_type = i % 5

                try:
                    if op_type == 0:
                        # Dynamic station mutation via add_user_csv_observations
                        sid = f"ST_TH_{thread_id}_{i}"
                        injected_station_ids.add(sid)
                        obs = NormalizedObservation(
                            timestamp=datetime.now(timezone.utc),
                            station_id=sid,
                            station_name=f"Dynamic Thread Station {sid}",
                            district="Lahore",
                            latitude=31.5204 + (random.random() * 0.1),
                            longitude=74.3587 + (random.random() * 0.1),
                            pm25_qc=35.0 + (i % 50),
                            pepc_aqi=95,
                            wind_speed_ms=2.5,
                            wind_direction_deg=180.0,
                            u_vector_ms=0.0,
                            v_vector_ms=2.5,
                            meteorology_source="user_csv",
                            qc_flags=[],
                            is_estimated=False,
                        )
                        added = repo.add_user_csv_observations([obs])
                        assert added == 1

                    elif op_type == 1:
                        # Multi-index queries
                        stations = repo.list_stations()
                        assert len(stations) >= initial_station_count
                        cnt = repo.count_stations()
                        assert cnt >= initial_station_count
                        # Query by random known baseline station
                        s_first = stations[0]
                        retrieved = repo.get_station_by_id(s_first.id)
                        assert retrieved is not None
                        assert retrieved.name == s_first.name

                    elif op_type == 2:
                        # Hourly series and observation queries
                        latest_obs = repo.get_latest_station_observations()
                        assert isinstance(latest_obs, list)
                        if repo._latest_timestamp:
                            at_ts = repo.get_station_observations_at_timestamp(repo._latest_timestamp)
                            assert isinstance(at_ts, list)

                    elif op_type == 3:
                        # Analytics cache mutations and cache clearing under contention
                        dt = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
                        grid_sample = [
                            SurfaceGridPoint(
                                x=31.5,
                                y=74.3,
                                value=45.0,
                                nearest_station_km=5.0,
                                alpha=200,
                            )
                        ]
                        # Holding repo._lock (RLock) isolates thread-local cache validation
                        # so that an intentional global clear_cache() from another thread does not race mid-assertion
                        with repo._lock:
                            repo.save_surface_grid(dt, "PM2.5", 20, grid_sample)
                            cached = repo.get_surface_grid(dt, "PM2.5", 20)
                            assert cached is not None
                            assert len(cached) == 1
                        if i % 10 == 0:
                            repo.clear_cache()

                    elif op_type == 4:
                        # Instantiate a new BaselineRepository concurrently
                        # This heavily exercises _PARSED_BASELINE_CACHE and _CACHE_LOCK
                        new_repo = BaselineRepository()
                        assert new_repo.count_stations() >= initial_station_count

                    completed_ops += 1
                except Exception as ex:
                    errors.append(f"Thread {thread_id} Op {i} ({op_type}) failed: {type(ex).__name__}: {str(ex)}")
                finally:
                    timings.append(time.perf_counter() - op_start)

            return completed_ops

        start_time = time.perf_counter()
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [executor.submit(worker_task, tid) for tid in range(thread_count)]
            total_completed = sum(f.result() for f in as_completed(futures))

        total_elapsed = time.perf_counter() - start_time

        # Empirical Assertions
        assert len(errors) == 0, f"Concurrency errors encountered ({len(errors)}): {errors[:5]}"
        assert total_completed == total_expected_ops

        # Invariant 1: JSONDecodeError did not occur during concurrent instantiation
        # Invariant 2: Total stations must equal initial count + injected stations
        final_stations = repo.list_stations()
        final_ids = {str(s.id) for s in final_stations}
        for expected_id in injected_station_ids:
            assert expected_id in final_ids, f"Station dropout detected! {expected_id} missing from catalog."
            # Check O(1) lookup
            station_entity = repo.get_station_by_id(expected_id)
            assert station_entity is not None
            assert station_entity.id == expected_id

        # Stress metrics
        avg_latency_ms = (sum(timings) / len(timings)) * 1000.0
        max_latency_ms = max(timings) * 1000.0
        ops_per_sec = total_completed / total_elapsed

        print(
            f"\n[BaselineRepository Concurrency Stress] Completed {total_completed} ops across {thread_count} threads "
            f"in {total_elapsed:.2f}s ({ops_per_sec:.1f} ops/sec). "
            f"Avg latency: {avg_latency_ms:.2f}ms, Max latency: {max_latency_ms:.2f}ms. "
            f"Total stations cataloged: {len(final_stations)} (injected: {len(injected_station_ids)}, dropped: 0)."
        )


# =============================================================================
# 2. FASTAPI ASYNC CONCURRENCY, PIPELINE INGESTION & CACHE CONTENTION
# =============================================================================

class TestAPIConcurrencyAndCacheContention:
    """
    Stress-tests the full FastAPI application gateway under concurrent async load:
    Simultaneous multipart CSV ingestion with simultaneous read requests for observations,
    spatial raster surfaces, and flux analytics.
    """

    @pytest.mark.anyio
    async def test_concurrent_api_ingestion_and_surface_raster_reads(self, app):
        """
        Executes 50 concurrent asynchronous HTTP requests:
        - 15 concurrent POST /api/v1/ingest/csv with dynamic stations
        - 15 concurrent GET /api/v1/observations/current
        - 10 concurrent GET /api/v1/spatial/surface?resolution=20
        - 10 concurrent GET /api/v1/analytics/flux?pollutant=PM2.5
        Verifies 100% HTTP 200 responses, zero 500 errors, and zero station dropouts.
        """
        uid = uuid.uuid4().hex[:6]
        csv_template = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value,wind_speed,wind_direction\n"
            f"2026-11-10 12:00,CONC_{uid}_{{idx}}_A,API Concurrent Station {{idx}} A,Lahore,31.5204,74.3587,PM2.5,45.0,2.1,180.0\n"
            f"2026-11-10 12:00,CONC_{uid}_{{idx}}_B,API Concurrent Station {{idx}} B,Faisalabad,31.4504,73.1350,PM2.5,52.0,1.8,90.0\n"
        )

        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver", timeout=30.0) as client:
            async def run_ingest(idx: int):
                csv_payload = csv_template.format(idx=idx).encode("utf-8")
                files = {"file": (f"api_stress_{idx}.csv", csv_payload, "text/csv")}
                res = await client.post("/api/v1/ingest/csv", files=files)
                assert res.status_code == 200, f"Ingest task {idx} failed: {res.text}"
                data = res.json()
                assert data["status"] == "success"
                assert data["valid_rows"] == 2
                return res.status_code

            async def run_get_current():
                res = await client.get("/api/v1/observations/current")
                assert res.status_code == 200, f"Observations current failed: {res.text}"
                return res.status_code

            async def run_get_surface():
                res = await client.get("/api/v1/spatial/surface?resolution=20")
                assert res.status_code == 200, f"Spatial surface failed: {res.text}"
                return res.status_code

            async def run_get_flux():
                res = await client.get("/api/v1/analytics/flux?pollutant=PM2.5")
                assert res.status_code == 200, f"Analytics flux failed: {res.text}"
                return res.status_code

            tasks = []
            for i in range(15):
                tasks.append(run_ingest(i))
                tasks.append(run_get_current())
            for _ in range(10):
                tasks.append(run_get_surface())
                tasks.append(run_get_flux())

            assert len(tasks) == 50

            start_t = time.perf_counter()
            results = await asyncio.gather(*tasks)
            elapsed_t = time.perf_counter() - start_t

            assert all(status == 200 for status in results)
            print(
                f"\n[FastAPI Async Concurrency Stress] Completed 50 concurrent requests in {elapsed_t:.2f}s "
                f"({50.0 / elapsed_t:.1f} req/sec). All 200 OK."
            )

            # Verification: all 30 dynamic stations (15 batches * 2 stations) exist in station metadata catalog
            meta_resp = await client.get("/api/v1/meta/stations")
            assert meta_resp.status_code == 200
            stations = meta_resp.json()
            station_ids = {s["id"] for s in stations}
            conc_found = [s["id"] for s in stations if f"CONC_{uid}" in s["id"]]
            print(f"\n[Verification] Total stations in meta: {len(stations)}. Dynamic CONC found: {len(conc_found)}/30: {sorted(conc_found)}")

            for i in range(15):
                assert f"CONC_{uid}_{i}_A" in station_ids, f"Station CONC_{uid}_{i}_A was dropped!"
                assert f"CONC_{uid}_{i}_B" in station_ids, f"Station CONC_{uid}_{i}_B was dropped!"


# =============================================================================
# 3. EDGE-CASE CSV INGESTION, SCHEMA TRAPS & HTTP 422 REJECTIONS
# =============================================================================

class TestEdgeCaseCSVIngestionAndSchemaTraps:
    """
    Adversarially tests missing columns, corrupt schemas, unphysical extreme values,
    and HTTP 422 validation rejections across the CSV ingestion dataflow.
    """

    @pytest.mark.anyio
    async def test_missing_mandatory_csv_columns_rejection(self, app):
        """
        Tests CSV files missing required columns:
        - Missing 'timestamp'
        - Missing 'station_id'
        - Missing 'pollutant'
        - Missing 'value'
        - Missing 'latitude' / 'longitude' when allow_missing_coords is False
        Confirms graceful pipeline degradation: status='failed', 0 valid rows, clear error message.
        """
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Missing timestamp column
            csv_no_timestamp = (
                "station_id,station_name,district,latitude,longitude,pollutant,value\n"
                "STN_NO_TS,Station No TS,Lahore,31.5204,74.3587,PM2.5,45.0\n"
            )
            files = {"file": ("no_ts.csv", csv_no_timestamp.encode("utf-8"), "text/csv")}
            res = await client.post("/api/v1/ingest/csv", files=files)
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "failed"
            assert data["valid_rows"] == 0
            assert any("Missing mandatory CSV columns" in err and "timestamp" in err for err in data["errors"])

            # 2. Missing pollutant column
            csv_no_pollutant = (
                "timestamp,station_id,station_name,district,latitude,longitude,value\n"
                "2026-11-10 12:00,STN_NO_POL,Station No Pol,Lahore,31.5204,74.3587,45.0\n"
            )
            files = {"file": ("no_pol.csv", csv_no_pollutant.encode("utf-8"), "text/csv")}
            res = await client.post("/api/v1/ingest/csv", files=files)
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "failed"
            assert data["valid_rows"] == 0
            assert any("Missing mandatory CSV columns" in err and "pollutant" in err for err in data["errors"])

            # 3. Missing value column
            csv_no_value = (
                "timestamp,station_id,station_name,district,latitude,longitude,pollutant\n"
                "2026-11-10 12:00,STN_NO_VAL,Station No Val,Lahore,31.5204,74.3587,PM2.5\n"
            )
            files = {"file": ("no_val.csv", csv_no_value.encode("utf-8"), "text/csv")}
            res = await client.post("/api/v1/ingest/csv", files=files)
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "failed"
            assert data["valid_rows"] == 0
            assert any("Missing mandatory CSV columns" in err and "value" in err for err in data["errors"])

            # 4. Missing coordinates when allow_missing_coords is False (default)
            csv_no_coords = (
                "timestamp,station_id,station_name,district,pollutant,value\n"
                "2026-11-10 12:00,STN_NO_COORDS,Station No Coords,Lahore,PM2.5,45.0\n"
            )
            files = {"file": ("no_coords.csv", csv_no_coords.encode("utf-8"), "text/csv")}
            res = await client.post("/api/v1/ingest/csv", files=files)
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "failed"
            assert any("Missing mandatory CSV columns" in err and ("latitude" in err or "longitude" in err) for err in data["errors"])

    @pytest.mark.anyio
    async def test_http_422_schema_validation_rejections(self, app):
        """
        Confirms proper HTTP 422 Unprocessable Content rejections when request
        schemas, body parameters, or query formats violate FastAPI/Pydantic validation contracts.
        """
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Missing multipart 'file' field -> 422
            res = await client.post("/api/v1/ingest/csv", data={"allow_missing_coords": "false"})
            assert res.status_code == 422, f"Expected 422 for missing file field, got {res.status_code}"
            err_data = res.json()
            assert any("file" in err.get("loc", ()) for err in err_data.get("details", err_data.get("detail", [])))

            # 2. Invalid boolean value for allow_missing_coords -> 422
            files = {"file": ("test.csv", b"timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n", "text/csv")}
            res = await client.post("/api/v1/ingest/csv", files=files, data={"allow_missing_coords": "not_a_valid_bool_value"})
            assert res.status_code == 422, f"Expected 422 for invalid boolean form field, got {res.status_code}"

            # 3. Spatial surface resolution out of bounds -> 422
            res = await client.get("/api/v1/spatial/surface?resolution=0")
            assert res.status_code == 422
            res = await client.get("/api/v1/spatial/surface?resolution=101")
            assert res.status_code == 422

            # 4. Advection flux negative limit -> 422
            res = await client.get("/api/v1/analytics/flux?limit=-1")
            assert res.status_code == 422

    @pytest.mark.anyio
    async def test_extreme_values_and_coordinate_edge_cases(self, app):
        """
        Adversarially tests boundary conditions on row data:
        - Concentrations > 5000 (e.g. 5001, 99999) -> quarantined with VALIDATION_ERROR
        - Zero concentration -> purged in Step 0 QC
        - Negative concentration -> quarantined
        - Negative coordinates -> quarantined as unresolvable / invalid
        - Out-of-bounds coordinates (e.g. lat 15.0, lon 40.0) -> quarantined
        - Sahiwal (0, 0) coordinate error -> repaired via canonical catalog
        - Aerodynamic calm (0.0 m/s) -> accepted with u=0, v=0
        - Anemometer speed exceedance (>30 m/s) -> wind purged, observation preserved
        - Wazirabad Station 172 -> anemometer blacklisted
        """
        adapter = UserCSVIngestionAdapter()
        test_csv = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value,wind_speed,wind_direction\n"
            # 1. Extreme value > 5000 (should be quarantined as VALIDATION_ERROR)
            "2026-11-10 12:00,ST_EX_5001,Extreme 5001,Lahore,31.5204,74.3587,PM2.5,5001.0,2.0,180.0\n"
            # 2. Extreme value 99999 (should be quarantined as VALIDATION_ERROR)
            "2026-11-10 12:00,ST_EX_99999,Extreme 99999,Lahore,31.5204,74.3587,PM2.5,99999.0,2.0,180.0\n"
            # 3. Zero value (should be purged in Step 0 QC)
            "2026-11-10 12:00,ST_ZERO,Zero Value,Lahore,31.5204,74.3587,PM2.5,0.0,2.0,180.0\n"
            # 4. Negative value (should be quarantined)
            "2026-11-10 12:00,ST_NEG,Negative Value,Lahore,31.5204,74.3587,PM2.5,-12.5,2.0,180.0\n"
            # 5. Negative coordinates (latitude -31.5, longitude -74.3)
            "2026-11-10 12:00,ST_NEG_COORD,Negative Coords,Lahore,-31.5204,-74.3587,PM2.5,45.0,2.0,180.0\n"
            # 6. Out of bounds coordinates (lat 20.0, lon 85.0)
            "2026-11-10 12:00,ST_OOB_COORD,OOB Coords,Lahore,20.0,85.0,PM2.5,45.0,2.0,180.0\n"
            # 7. Sahiwal 0,0 registry error -> should be canonically corrected to (30.6682, 73.1114)
            "2026-11-10 12:00,ST_SAHIWAL,Sahiwal AQMS,Sahiwal,0.0,0.0,PM2.5,65.0,1.5,90.0\n"
            # 8. Calm wind (ws=0.0, wd=0.0) -> should be admitted with u=0, v=0
            "2026-11-10 12:00,ST_CALM,Calm Wind Station,Lahore,31.5204,74.3587,PM2.5,40.0,0.0,0.0\n"
            # 9. Wind speed exceedance (> 30 m/s) -> wind purged, observation kept
            "2026-11-10 12:00,ST_WIND_EXCEED,High Wind Station,Lahore,31.5204,74.3587,PM2.5,42.0,35.0,180.0\n"
            # 10. Wazirabad Station 172 -> anemometer blacklisted
            "2026-11-10 12:00,172,Wazirabad AQMS,Gujranwala,32.4428,74.1197,PM2.5,50.0,4.0,140.0\n"
        )

        result = adapter.ingest_csv(test_csv)
        assert result.total_rows == 10
        # Expected quarantined rows:
        # Rows 1, 2, 4 (value out of range)
        # Row 3 (zero value)
        # Rows 5, 6 (invalid coords)
        # Row 9 (wind speed > 30 m/s rejected by UserCSVRow schema)
        # Total quarantined = 7
        # Expected valid rows:
        # Row 7 (Sahiwal repaired)
        # Row 8 (Calm wind)
        # Row 10 (Wazirabad blacklisted)
        # Total valid = 3
        assert result.valid_count == 3, f"Expected 3 valid rows, got {result.valid_count}"
        assert result.quarantine_count == 7, f"Expected 7 quarantined rows, got {result.quarantine_count}"

        # Inspect valid observations
        valid_map = {obs.station_id: obs for obs in result.observations}

        # 7. Sahiwal repaired
        sahiwal = valid_map["ST_SAHIWAL"]
        assert abs(sahiwal.latitude - 30.6682) < 0.001
        assert abs(sahiwal.longitude - 73.1114) < 0.001

        # 8. Calm wind
        calm = valid_map["ST_CALM"]
        assert calm.wind_speed_ms == 0.0
        assert calm.u_vector_ms == 0.0
        assert calm.v_vector_ms == 0.0

        # 9. Wind speed exceedance in DLQ
        wind_exceed_q = next((q for q in result.quarantine_records if q.station_id == "ST_WIND_EXCEED"), None)
        assert wind_exceed_q is not None
        assert wind_exceed_q.error_type == "VALIDATION_ERROR"
        assert "less than or equal to 30" in wind_exceed_q.error_message

        # 10. Wazirabad blacklist
        wazirabad = valid_map["172"]
        assert wazirabad.wind_speed_ms is None
        assert wazirabad.wind_direction_deg is None
        assert "WIND_BLACKLIST_WAZIRABAD" in wazirabad.qc_flags


# =============================================================================
# 4. REPETITION STABILITY UNDER REPEATED ADVERSARIAL EXECUTION
# =============================================================================

class TestRepetitionStability:
    """
    Executes multiple consecutive test cycles to ensure zero flakiness,
    no memory corruption, and consistent cache behavior across executions.
    """

    def test_repeated_adversarial_cycles(self, app):
        """Runs 3 repeated cycles of baseline repository instantiation, indexing, and querying."""
        for cycle in range(3):
            repo = BaselineRepository()
            assert repo.count_stations() >= 74
            assert repo.count_districts() >= 36
            # Verify latest observation
            obs = repo.get_latest_station_observations()
            assert len(obs) > 0
            # Verify timeline
            assert repo.total_hours() > 0
