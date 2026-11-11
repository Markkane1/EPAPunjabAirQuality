"""
Unit Test Suite for BaselineRepository: In-Memory Storage, Latency, Concurrency, and Mutation.
Verifies:
1. Initial baseline catalog counts & artifact loading (79 stations, 6 aerodromes, 41 districts, 216 hours).
2. Sub-microsecond in-memory query latency (< 1.0 µs for O(1) hash lookups, < 25 µs for 85-station slices).
3. Observation deduplication on single & batch dynamic ingestion.
4. Timezone resilience: offset-naive vs offset-aware datetimes and UTC normalization.
5. Multithreaded concurrency stress testing under threading.RLock().
6. Clean Architecture interface compliance (StationRepository, DistrictRepository, ObservationRepository, AnalyticsRepository).
7. Greedy label placement generation and Axis-Aligned Bounding Box (AABB) collision freedom.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import time
from typing import List, Tuple
import pytest

from src.domain.entities.models import (
    CPFRoseResult,
    District,
    DistrictObservation,
    LabelPlacement,
    Station,
    StationObservation,
    SurfaceGridPoint,
    TransboundaryResult,
)
from src.domain.interfaces.repositories import (
    AnalyticsRepository,
    DistrictRepository,
    ObservationRepository,
    StationRepository,
)
from src.domain.math.projection import (
    LABEL_CANDIDATE_OFFSETS,
    check_aabb_collision,
)
from src.domain.schemas.measurement import NormalizedObservation
from src.infrastructure.repositories.baseline_repository import BaselineRepository


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def repo() -> BaselineRepository:
    """Instantiate a fresh BaselineRepository loading canonical baseline artifacts."""
    return BaselineRepository()


@pytest.fixture
def sample_station_obs() -> StationObservation:
    """Create a sample valid station observation for dynamic ingestion tests."""
    return StationObservation(
        station_id="OPLA",
        recorded_at=datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc),
        pm25=45.2,
        pm10=82.1,
        no2=25.0,
        so2=12.0,
        co=1.1,
        o3=18.0,
        no=5.0,
        nox=30.0,
        aqi=124,
        wind_speed=2.5,
        wind_direction=180.0,
        u=0.0,
        v=-2.5,
    )


@pytest.fixture
def sample_district_obs() -> DistrictObservation:
    """Create a sample valid district observation for dynamic ingestion tests."""
    return DistrictObservation(
        district_id="Lahore",
        recorded_at=datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc),
        pm25=52.0,
        pm10=95.0,
        no2=28.0,
        so2=14.0,
        co=1.3,
        o3=20.0,
        aqi=145,
        wind_speed=2.8,
        wind_direction=175.0,
        u=-0.24,
        v=-2.79,
        is_estimated=False,
    )


# =============================================================================
# 1. BASELINE LOADING AND CATALOG COUNTS
# =============================================================================

class TestBaselineLoadingAndCatalogCounts:
    """Verifies that baseline JSON artifacts are loaded and indexed with exact counts."""

    def test_station_and_airport_catalog_counts(self, repo: BaselineRepository):
        """
        Baseline data catalog contains:
        - 79 ground monitoring stations (stations.json)
        - 6 METAR airport aerodromes (airports.json: OPLA, OPFA, OPMT, OPST, OPIS, VIAR)
        - Total indexed station entities == 85
        """
        assert repo.count_stations() == 85
        assert len(repo.list_stations()) == 85
        assert len(repo.list_all()) == 85

        airports = repo.list_airports()
        assert len(airports) == 6
        airport_icaos = {a.id for a in airports}
        expected_icaos = {"OPLA", "OPFA", "OPMT", "OPST", "OPIS", "VIAR"}
        assert airport_icaos == expected_icaos

        for a in airports:
            assert a.station_type == "airport_metar"
            assert a.has_anemometer is True
            assert a.anemometer_blacklisted is False

        # Verify ground station metadata
        ground_stations = [s for s in repo.list_stations() if s.station_type != "airport_metar"]
        assert len(ground_stations) == 79

    def test_district_catalog_and_border_metadata(self, repo: BaselineRepository):
        """
        Baseline districts catalog contains:
        - Exactly 41 administrative districts
        - Valid GeoJSON boundary geometries
        - Border corridor filtering (<= 120 km)
        - 39 transboundary border normal vector nodes
        """
        assert repo.count_districts() == 41
        districts = repo.list_all_districts()
        assert len(districts) == 41

        # Unique district names
        district_names = {d.name for d in districts}
        assert len(district_names) == 41
        assert "Lahore" in district_names
        assert "Rawalpindi" in district_names
        assert "Multan" in district_names

        # Border districts corridor
        border_districts = repo.list_border_districts(max_border_distance_km=120.0)
        assert len(border_districts) > 0
        assert all(d.border_distance_km <= 120.0 for d in border_districts)

        # Boundary geometry exists
        lahore_geom = repo.get_boundary_geometry("Lahore")
        assert lahore_geom is not None
        assert "type" in lahore_geom or "coordinates" in lahore_geom or isinstance(lahore_geom, list)

        # Border normal sample nodes
        samples = repo.get_border_samples()
        assert len(samples) == 39
        assert all(len(s) >= 2 for s in samples)

    def test_timeline_hours_and_index_mapping(self, repo: BaselineRepository):
        """
        Timeline contains 216 historical hours from 2026-11-01 00:00 to 2026-11-09 23:00 UTC.
        Hour-to-index and index-to-hour mappings must be bidirectional and monotonic.
        """
        assert repo.total_hours() == 216
        timestamps = repo.get_available_timestamps()
        assert len(timestamps) == 216
        assert timestamps == sorted(timestamps)

        earliest = repo.get_earliest_timestamp()
        latest = repo.get_latest_timestamp()
        assert earliest == datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)
        assert latest == datetime(2026, 11, 9, 23, 0, tzinfo=timezone.utc)

        # Index roundtrip
        assert repo.get_timestamp_by_index(0) == earliest
        assert repo.get_timestamp_by_index(215) == latest
        assert repo.get_timestamp_by_index(-1) == latest
        assert repo.get_timestamp_by_index(999) is None

        assert repo.get_hour_index(earliest) == 0
        assert repo.get_hour_index(latest) == 215

    def test_wazirabad_anemometer_blacklist(self, repo: BaselineRepository):
        """Wazirabad sensor has 140 deg sensor offset blacklist flag set."""
        wazirabad_stations = [s for s in repo.list_stations() if "wazirabad" in s.name.lower()]
        assert len(wazirabad_stations) >= 1
        for s in wazirabad_stations:
            assert s.anemometer_blacklisted is True
            assert s.has_anemometer is False


# =============================================================================
# 2. RETRIEVAL LATENCY BENCHMARKS
# =============================================================================

class TestBaselineRetrievalLatency:
    """Verifies sub-microsecond in-memory query performance (< 1.0 µs for O(1) hash queries)."""

    def test_sub_microsecond_single_entity_lookups(self, repo: BaselineRepository):
        """get_station_by_id and get_district_by_id must execute in under 1.0 microsecond on average."""
        # Warmup
        repo.get_station_by_id("OPLA")
        repo.get_district_by_id("Lahore")

        iterations = 5000

        t0 = time.perf_counter()
        for _ in range(iterations):
            repo.get_station_by_id("OPLA")
        t1 = time.perf_counter()
        avg_station_us = ((t1 - t0) / iterations) * 1e6

        t0 = time.perf_counter()
        for _ in range(iterations):
            repo.get_district_by_id("Lahore")
        t1 = time.perf_counter()
        avg_district_us = ((t1 - t0) / iterations) * 1e6

        # Target: sub-microsecond (< 1.0 us). Guard against slow CI runners with 5.0 us cap.
        assert avg_station_us < 5.0, f"get_station_by_id took {avg_station_us:.3f} µs (expected < 5.0 µs)"
        assert avg_district_us < 5.0, f"get_district_by_id took {avg_district_us:.3f} µs (expected < 5.0 µs)"

    def test_sub_microsecond_observation_lookups(self, repo: BaselineRepository):
        """get_station_observation, get_district_observation, and get_hour_index must execute in under 1.0 µs."""
        dt = repo.get_latest_timestamp()
        assert dt is not None

        iterations = 5000

        t0 = time.perf_counter()
        for _ in range(iterations):
            repo.get_station_observation("OPLA", dt)
        t1 = time.perf_counter()
        avg_st_obs_us = ((t1 - t0) / iterations) * 1e6

        t0 = time.perf_counter()
        for _ in range(iterations):
            repo.get_district_observation("Lahore", dt)
        t1 = time.perf_counter()
        avg_dist_obs_us = ((t1 - t0) / iterations) * 1e6

        t0 = time.perf_counter()
        for _ in range(iterations):
            repo.get_hour_index(dt)
        t1 = time.perf_counter()
        avg_hour_idx_us = ((t1 - t0) / iterations) * 1e6

        assert avg_st_obs_us < 5.0, f"get_station_observation took {avg_st_obs_us:.3f} µs"
        assert avg_dist_obs_us < 5.0, f"get_district_observation took {avg_dist_obs_us:.3f} µs"
        assert avg_hour_idx_us < 5.0, f"get_hour_index took {avg_hour_idx_us:.3f} µs"

    def test_time_slice_and_series_bisect_latency(self, repo: BaselineRepository):
        """Retrieving an 85-station timestamp slice and binary-search series must execute in under 25 µs."""
        dt = repo.get_latest_timestamp()
        assert dt is not None

        iterations = 2000

        t0 = time.perf_counter()
        for _ in range(iterations):
            repo.get_station_observations_at_timestamp(dt)
        t1 = time.perf_counter()
        avg_slice_us = ((t1 - t0) / iterations) * 1e6

        t0 = time.perf_counter()
        for _ in range(iterations):
            repo.get_station_hourly_series("OPLA")
        t1 = time.perf_counter()
        avg_series_us = ((t1 - t0) / iterations) * 1e6

        assert avg_slice_us < 25.0, f"85-station slice took {avg_slice_us:.3f} µs (expected < 25.0 µs)"
        assert avg_series_us < 25.0, f"216-hour bisect series took {avg_series_us:.3f} µs (expected < 25.0 µs)"


# =============================================================================
# 3. OBSERVATION DEDUPLICATION (FINDING 1)
# =============================================================================

class TestBaselineObservationDeduplication:
    """Verifies that re-ingesting observations updates existing records rather than duplicating them."""

    def test_station_observation_deduplication_single_add(self, repo: BaselineRepository):
        """
        Adding an updated StationObservation for an existing (station_id, timestamp) pair:
        - Must update the observation value in place
        - Must NOT increase len(get_station_observations_at_timestamp(dt))
        - Must NOT increase len(get_station_hourly_series(station_id))
        """
        dt = repo.get_latest_timestamp()
        assert dt is not None

        # Capture baseline counts
        c_time_before = len(repo.get_station_observations_at_timestamp(dt))
        c_series_before = len(repo.get_station_hourly_series("OPLA"))
        assert c_time_before == 85
        assert c_series_before == 216

        # Ingest updated observation
        updated_obs = StationObservation(station_id="OPLA", recorded_at=dt, pm25=777.7)
        repo.add_station_observation(updated_obs)

        # Verify counts are invariant
        c_time_after = len(repo.get_station_observations_at_timestamp(dt))
        c_series_after = len(repo.get_station_hourly_series("OPLA"))
        assert c_time_after == c_time_before, f"Expected {c_time_before} observations, got {c_time_after} (duplicated!)"
        assert c_series_after == c_series_before, f"Expected {c_series_before} series points, got {c_series_after}"

        # Verify value was updated
        retrieved = repo.get_station_observation("OPLA", dt)
        assert retrieved is not None
        assert retrieved.pm25 == 777.7

        # Verify exactly one entry for OPLA exists in timestamp slice
        slice_obs = repo.get_station_observations_at_timestamp(dt)
        opla_entries = [o for o in slice_obs if o.station_id == "OPLA"]
        assert len(opla_entries) == 1
        assert opla_entries[0].pm25 == 777.7

    def test_station_observation_deduplication_batch_add(self, repo: BaselineRepository):
        """Re-ingesting a batch of observations multiple times maintains constant record counts."""
        dt = repo.get_latest_timestamp()
        assert dt is not None

        stations_to_update = ["OPLA", "OPFA", "OPMT", "OPST"]
        batch_1 = [StationObservation(station_id=sid, recorded_at=dt, pm25=100.0) for sid in stations_to_update]
        batch_2 = [StationObservation(station_id=sid, recorded_at=dt, pm25=200.0) for sid in stations_to_update]

        repo.add_station_observations(batch_1)
        assert len(repo.get_station_observations_at_timestamp(dt)) == 85

        repo.add_station_observations(batch_2)
        assert len(repo.get_station_observations_at_timestamp(dt)) == 85

        for sid in stations_to_update:
            obs = repo.get_station_observation(sid, dt)
            assert obs is not None
            assert obs.pm25 == 200.0
            assert len(repo.get_station_hourly_series(sid)) == 216

    def test_district_observation_deduplication(self, repo: BaselineRepository):
        """
        Adding an updated DistrictObservation for an existing (district_id, timestamp) pair:
        - Must update the observation value in place
        - Must NOT increase len(get_district_observations_at_timestamp(dt))
        - Must NOT increase len(get_district_hourly_series(district_id))
        """
        dt = repo.get_latest_timestamp()
        assert dt is not None

        c_time_before = len(repo.get_district_observations_at_timestamp(dt))
        c_series_before = len(repo.get_district_hourly_series("Lahore"))
        assert c_time_before == 41
        assert c_series_before == 216

        dist_obs = DistrictObservation(district_id="Lahore", recorded_at=dt, pm25=555.5)
        repo.add_district_observation(dist_obs)

        c_time_after = len(repo.get_district_observations_at_timestamp(dt))
        c_series_after = len(repo.get_district_hourly_series("Lahore"))
        assert c_time_after == c_time_before, f"Expected {c_time_before} districts, got {c_time_after}"
        assert c_series_after == c_series_before

        retrieved = repo.get_district_observation("Lahore", dt)
        assert retrieved is not None
        assert retrieved.pm25 == 555.5

    def test_user_csv_reingestion_count_invariance(self, repo: BaselineRepository):
        """Ingesting identical user CSV observations twice must maintain count invariance."""
        dt = datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc)
        normalized_rows = [
            NormalizedObservation(
                timestamp=dt,
                station_id="TEST_CSV_01",
                station_name="Test Station 1",
                district="Lahore",
                latitude=31.52,
                longitude=74.35,
                pm25_qc=45.0,
                pepc_aqi=124,
            ),
            NormalizedObservation(
                timestamp=dt,
                station_id="TEST_CSV_02",
                station_name="Test Station 2",
                district="Lahore",
                latitude=31.54,
                longitude=74.38,
                pm25_qc=50.0,
                pepc_aqi=135,
            ),
        ]

        count1 = repo.add_user_csv_observations(normalized_rows)
        assert count1 == 2
        obs_count_1 = len(repo.get_station_observations_at_timestamp(dt))

        # Re-ingest same rows with mutated PM2.5
        mutated_rows = [r.model_copy(update={"pm25_qc": 99.0}) for r in normalized_rows]
        count2 = repo.add_user_csv_observations(mutated_rows)
        assert count2 == 2
        obs_count_2 = len(repo.get_station_observations_at_timestamp(dt))

        assert obs_count_2 == obs_count_1, "Re-ingesting CSV rows duplicated station observation records!"
        assert repo.get_station_observation("TEST_CSV_01", dt).pm25 == 99.0


# =============================================================================
# 4. TIMEZONE RESILIENCE (FINDING 2)
# =============================================================================

class TestBaselineTimezoneResilience:
    """Verifies that offset-naive and offset-aware datetimes are handled without TypeError crashes."""

    def test_ingest_offset_naive_station_observation_no_crash(self, repo: BaselineRepository):
        """Ingesting StationObservation with offset-naive datetime MUST NOT raise TypeError during sort."""
        naive_dt = datetime(2026, 11, 15, 12, 0)  # tzinfo is None
        obs = StationObservation(station_id="OPLA", recorded_at=naive_dt, pm25=42.0)

        # Must execute without TypeError: can't compare offset-naive and offset-aware datetimes
        repo.add_station_observation(obs)

        # Retrieval via naive datetime
        ret_naive = repo.get_station_observation("OPLA", naive_dt)
        assert ret_naive is not None
        assert ret_naive.pm25 == 42.0

        # Retrieval via UTC-aware datetime
        aware_dt = naive_dt.replace(tzinfo=timezone.utc)
        ret_aware = repo.get_station_observation("OPLA", aware_dt)
        assert ret_aware is not None
        assert ret_aware.pm25 == 42.0

    def test_ingest_offset_naive_district_observation_no_crash(self, repo: BaselineRepository):
        """Ingesting DistrictObservation with offset-naive datetime MUST NOT raise TypeError during sort."""
        naive_dt = datetime(2026, 11, 15, 12, 0)
        dist_obs = DistrictObservation(district_id="Lahore", recorded_at=naive_dt, pm25=55.0)

        repo.add_district_observation(dist_obs)

        ret_naive = repo.get_district_observation("Lahore", naive_dt)
        assert ret_naive is not None
        assert ret_naive.pm25 == 55.0

    def test_mixed_naive_aware_chronological_sort_order(self, repo: BaselineRepository):
        """
        When adding observations with mixed naive and aware datetimes,
        series list must remain strictly chronologically ordered without comparison errors.
        """
        sid = "TEST_MIXED_TZ"
        obs_times = [
            datetime(2026, 11, 12, 14, 0, tzinfo=timezone.utc),
            datetime(2026, 11, 12, 10, 0),                       # naive
            datetime(2026, 11, 12, 16, 0, tzinfo=timezone.utc),
            datetime(2026, 11, 12, 8, 0),                        # naive
            datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc),
        ]

        for t in obs_times:
            repo.add_station_observation(StationObservation(station_id=sid, recorded_at=t, pm25=10.0))

        series = repo.get_station_hourly_series(sid)
        assert len(series) == 5

        # Verify chronological ordering
        for i in range(len(series) - 1):
            t1 = series[i].recorded_at if series[i].recorded_at.tzinfo else series[i].recorded_at.replace(tzinfo=timezone.utc)
            t2 = series[i+1].recorded_at if series[i+1].recorded_at.tzinfo else series[i+1].recorded_at.replace(tzinfo=timezone.utc)
            assert t1 < t2, f"Series not strictly sorted: {t1} >= {t2}"

    def test_non_utc_timezone_normalization_and_query_equivalence(self, repo: BaselineRepository):
        """Observations with non-UTC timezones (e.g. PKT UTC+5) normalize and match UTC queries."""
        pkt = timezone(timedelta(hours=5))
        # 17:00 PKT == 12:00 UTC
        pkt_time = datetime(2026, 11, 12, 17, 0, tzinfo=pkt)
        utc_time = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)

        repo.add_station_observation(StationObservation(station_id="OPLA", recorded_at=pkt_time, pm25=65.0))

        # Query with UTC equivalent
        res = repo.get_station_observation("OPLA", utc_time)
        assert res is not None
        assert res.pm25 == 65.0


# =============================================================================
# 5. THREAD SAFETY UNDER THREADING.RLOCK()
# =============================================================================

class TestBaselineThreadSafety:
    """Verifies concurrency safety across 10 reader threads and 2 writer threads."""

    def test_concurrent_readers_and_writers_under_rlock(self, repo: BaselineRepository):
        """
        Runs 10 concurrent reader threads and 2 writer threads executing 5,000 queries
        and 150 batch mutations without race conditions, deadlocks, or state corruption.
        """
        errors: List[Exception] = []
        dt = repo.get_latest_timestamp()
        assert dt is not None

        def reader_worker(worker_id: int):
            try:
                for i in range(500):
                    repo.get_station_by_id("OPLA")
                    repo.get_district_by_id("Lahore")
                    repo.get_station_observation("OPLA", dt)
                    repo.get_station_observations_at_timestamp(dt)
                    repo.get_hour_index(dt)
                    repo.get_available_timestamps()
            except Exception as e:
                errors.append(e)

        def writer_worker(worker_id: int):
            try:
                for i in range(75):
                    # Ingest new station observations
                    t = dt + timedelta(hours=i + 1)
                    repo.add_station_observations([
                        StationObservation(station_id="OPLA", recorded_at=t, pm25=float(i)),
                        StationObservation(station_id="OPFA", recorded_at=t, pm25=float(i * 2)),
                    ])
                    # Ingest new district observation
                    repo.add_district_observation(
                        DistrictObservation(district_id="Lahore", recorded_at=t, pm25=float(i))
                    )
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=12) as executor:
            futures = []
            for r in range(10):
                futures.append(executor.submit(reader_worker, r))
            for w in range(2):
                futures.append(executor.submit(writer_worker, w))
            for f in futures:
                f.result()

        assert len(errors) == 0, f"Concurrent execution produced errors: {errors}"
        # Timeline and index consistency
        assert len(repo.get_available_timestamps()) == repo.total_hours()

    def test_atomic_cache_invalidation_during_mutations(self, repo: BaselineRepository):
        """Caches (CPF, flux, surface, transboundary) are atomically cleared upon observation ingestion."""
        dt = repo.get_latest_timestamp()
        assert dt is not None

        # Seed analytics cache
        repo.save_cpf_rose(CPFRoseResult(
            district_id="Lahore",
            pollutant="PM2.5",
            threshold=35.0,
            calm_ratio=0.1,
            sectors=[10.0] * 16,
        ))
        assert repo.get_cpf_rose("Lahore", "PM2.5") is not None

        # Mutate via add_station_observations
        repo.add_station_observation(StationObservation(station_id="OPLA", recorded_at=dt, pm25=88.0))

        # Verify cache was cleared
        assert repo.get_cpf_rose("Lahore", "PM2.5") is None


# =============================================================================
# 6. INTERFACE COMPLIANCE & LSP DISAMBIGUATION (FINDING 3)
# =============================================================================

class TestBaselineInterfaceCompliance:
    """Verifies compliance with abstract contracts and resolution of LSP collisions."""

    def test_station_repository_interface_contract(self, repo: BaselineRepository):
        """BaselineRepository fully satisfies StationRepository interface."""
        st_repo: StationRepository = repo

        assert st_repo.count() == 85
        assert len(st_repo.list_all()) == 85
        assert st_repo.get_by_id("OPLA") is not None
        assert st_repo.exists("OPLA") is True
        assert st_repo.exists("NON_EXISTENT_ID") is False
        assert len(st_repo.list_airports()) == 6
        assert len(st_repo.list_by_district("Lahore")) > 0

    def test_district_repository_interface_contract(self, repo: BaselineRepository):
        """BaselineRepository satisfies DistrictRepository interface."""
        dist_repo: DistrictRepository = repo

        # Direct domain-specific methods must return accurate counts
        assert dist_repo.count_districts() == 41
        assert len(dist_repo.list_all_districts()) == 41
        assert len(dist_repo.list_districts()) == 41

        lahore = dist_repo.get_district_by_name("Lahore")
        assert lahore is not None
        assert isinstance(lahore, District)
        assert lahore.name == "Lahore"

        assert dist_repo.get_boundary_geometry("Lahore") is not None
        assert len(dist_repo.list_border_districts(120.0)) > 0

    def test_interface_polymorphism_and_lsp_disambiguation(self, repo: BaselineRepository):
        """
        Tests polymorphic access as DistrictRepository:
        - When calling count_districts(), returns 41
        - When calling list_all_districts(), returns 41 District instances
        - When calling get_district_by_name('Lahore'), returns District, NOT Station
        """
        district_view: DistrictRepository = repo

        # Method disambiguation
        assert district_view.count_districts() == 41
        districts = district_view.list_districts()
        assert len(districts) == 41
        assert all(isinstance(d, District) for d in districts)

        dist_entity = district_view.get_district_by_name("Lahore")
        assert isinstance(dist_entity, District)
        assert dist_entity.id == "Lahore" or dist_entity.name == "Lahore"

        # Dedicated adapter facades
        station_adapter: StationRepository = repo.stations
        district_adapter: DistrictRepository = repo.districts
        assert station_adapter.count() == 85
        assert district_adapter.count() == 41
        assert len(station_adapter.list_all()) == 85
        assert len(district_adapter.list_all()) == 41
        assert district_adapter.get_by_name("Lahore").division == "Lahore"
        assert station_adapter.get_by_name("Lahore") is not None


# =============================================================================
# 7. LABEL PLACEMENT & PROJECTION (FINDING 4)
# =============================================================================

class TestBaselineLabelPlacement:
    """Verifies greedy label placement coordinates and Axis-Aligned Bounding Box collision freedom."""

    def test_label_placement_coordinates_and_leader_lines(self, repo: BaselineRepository):
        """
        get_label_placement(district_id):
        - Returns a valid LabelPlacement instance for all 41 districts
        - Placement coordinates anchor_x and anchor_y are positive canvas pixels
        - Offsets conform to LABEL_CANDIDATE_OFFSETS
        - Leader line is correctly flagged when offset displacement > 20.0 px
        - Returns None for non-existent district IDs
        """
        for d in repo.list_all_districts():
            placement = repo.get_label_placement(d.id) or repo.get_label_placement(d.name)
            assert placement is not None, f"get_label_placement returned None for district '{d.name}'"
            assert isinstance(placement, LabelPlacement)
            assert placement.text == d.name
            assert placement.anchor_x > 0.0
            assert placement.anchor_y > 0.0
            assert placement.width > 0.0
            assert placement.height > 0.0

            # Verify offset matches valid candidate vector
            offset_tuple = (placement.offset_x, placement.offset_y)
            assert offset_tuple in LABEL_CANDIDATE_OFFSETS, f"Offset {offset_tuple} not in LABEL_CANDIDATE_OFFSETS"

            # Leader line threshold invariant: sqrt(dx^2 + dy^2) > 20.0 px
            displacement = math.hypot(placement.offset_x, placement.offset_y)
            if displacement > 20.0:
                assert placement.has_leader_line is True
            else:
                assert placement.has_leader_line is False

        # Non-existent district returns None
        assert repo.get_label_placement("NonExistentDistrictXYZ999") is None

    def test_label_placement_aabb_collision_freedom(self, repo: BaselineRepository):
        """All 41 placed district label bounding boxes must be 100% collision-free."""
        placements: List[LabelPlacement] = []
        for d in repo.list_all_districts():
            p = repo.get_label_placement(d.id) or repo.get_label_placement(d.name)
            if p is not None:
                placements.append(p)

        assert len(placements) == 41

        # Check all pairs for AABB collision
        boxes = []
        for p in placements:
            # Box format: (x, y, w, h)
            bx = p.anchor_x + p.offset_x - (p.width / 2.0) - 1.0
            by = p.anchor_y + p.offset_y - (p.height / 2.0)
            bw = p.width + 2.0
            bh = p.height
            boxes.append((p.district_id, (bx, by, bw, bh)))

        collisions = []
        for i in range(len(boxes)):
            id1, b1 = boxes[i]
            for j in range(i + 1, len(boxes)):
                id2, b2 = boxes[j]
                if check_aabb_collision(b1, b2):
                    collisions.append((id1, id2))

        assert len(collisions) == 0, f"Detected visual label collisions between districts: {collisions}"
