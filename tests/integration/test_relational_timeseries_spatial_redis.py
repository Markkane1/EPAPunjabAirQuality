"""
Comprehensive End-to-End Integration Test Suite for the 5 Architectural Pillars:
1. Relational Core (PostgreSQL 16)
2. Time-Series Persistence (TimescaleDB 2.14 Hypertables)
3. Spatial Engine (PostGIS 3.4 Spatial Types & Geodesic Queries)
4. High-Speed Cache & SSE Fan-Out (Redis 7.2 & Pub/Sub)
5. Continuous Rollups (Automated Continuous Aggregates)
Plus full End-to-End FastAPI Gateway wiring.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
import httpx
from httpx import ASGITransport
from sqlalchemy import text

from src.api.main import create_application
from src.domain.entities.models import (
    AdvectionFluxLink,
    CPFRoseResult,
    District,
    DistrictObservation,
    Station,
    StationObservation,
    SurfaceGridPoint,
    TransboundaryResult,
)
from src.infrastructure.cache.redis_analytics_repository import RedisAnalyticsRepository
from src.infrastructure.cache.redis_manager import RedisCacheManager
from src.infrastructure.database.connection import DatabaseConfig, DatabaseManager
from src.infrastructure.database.continuous_aggregates import ContinuousRollupService
from src.infrastructure.repositories.persistent_repository import PersistentRepository
from src.infrastructure.spatial.postgis_engine import PostgisSpatialEngine


@pytest.fixture(scope="module")
def persistent_repo():
    """Initializes the unified PersistentRepository connected to PostgreSQL 16 & Redis."""
    repo = PersistentRepository()
    return repo


@pytest.fixture(scope="module")
def app():
    """Create and initialize the FastAPI application with persistent backend."""
    return create_application()


@pytest.fixture
def anyio_backend():
    return "asyncio"


# =============================================================================
# PILLAR 1: RELATIONAL CORE (PostgreSQL 16)
# =============================================================================

class TestRelationalCore:
    """Verifies PostgreSQL 16 schema, tables, foreign keys, and relational repositories."""

    def test_database_connection_and_version(self, persistent_repo):
        """Verifies database connectivity, ping, and PostgreSQL 16 server version."""
        db = persistent_repo.db
        assert db.ping() is True

        with db.session_scope() as session:
            version_str = session.execute(text("SELECT version();")).scalar()
            assert version_str is not None
            assert "PostgreSQL 16" in version_str

    def test_districts_relational_repository(self, persistent_repo):
        """Verifies all 41 Punjab districts are indexed in spatial_districts table."""
        districts = persistent_repo.districts.list_all()
        assert len(districts) == 41

        # Check Lahore district details
        lahore = persistent_repo.districts.get_by_name("Lahore")
        assert lahore is not None
        assert lahore.name == "Lahore"
        assert lahore.division == "Lahore"
        assert abs(lahore.latitude - 31.5497) < 0.1
        assert abs(lahore.longitude - 74.3436) < 0.1

        # Verify polygon boundary
        boundary = persistent_repo.districts.get_boundary_geometry(lahore.id)
        assert boundary is not None
        assert len(boundary) > 0

    def test_stations_relational_repository(self, persistent_repo):
        """Verifies stations/aerodromes are indexed in spatial_stations table."""
        stations = persistent_repo.stations.list_all()
        assert len(stations) >= 85

        # Check Allama Iqbal International Airport (OPLA)
        opla = persistent_repo.stations.get_by_id("OPLA")
        assert opla is not None
        assert opla.id == "OPLA"
        assert opla.station_type == "airport_metar"
        assert opla.district.lower() == "lahore"

        # Filter stations by district
        lahore_stations = persistent_repo.stations.list_by_district("Lahore")
        assert len(lahore_stations) >= 5
        assert any(s.id == "OPLA" for s in lahore_stations)

        # Filter stations by type
        aerodromes = persistent_repo.stations.list_all(station_type="airport_metar")
        assert len(aerodromes) >= 5


# =============================================================================
# PILLAR 2: TIME-SERIES PERSISTENCE (TimescaleDB 2.14 Hypertables)
# =============================================================================

class TestTimeSeriesPersistence:
    """Verifies station_hourly_observations table/hypertable with composite PK upsert."""

    def test_historical_timeline_and_observation_count(self, persistent_repo):
        """Verifies historical hours are queried from relational/hypertable storage."""
        timeline = persistent_repo.get_timeline_timestamps()
        assert len(timeline) >= 216
        latest_ts = persistent_repo.get_latest_timestamp()
        assert latest_ts is not None


        # Verify baseline observation count
        baseline_obs = persistent_repo.get_station_observations_at_timestamp(timeline[0])
        assert len(baseline_obs) >= 40

        # Verify latest observations query
        latest_obs = persistent_repo.get_latest_station_observations()
        assert len(latest_obs) >= 1

    def test_time_range_queries(self, persistent_repo):
        """Verifies range scans on recorded_at index."""
        timeline = persistent_repo.get_timeline_timestamps()
        start = timeline[0]
        end = timeline[10]

        range_obs = persistent_repo.get_station_hourly_series(
            station_id="1",
            start_time=start,
            end_time=end,
        )
        assert len(range_obs) == 11
        for obs in range_obs:
            assert obs.station_id == "1"
            assert start <= obs.recorded_at <= end

    def test_composite_pk_upsert_deduplication(self, persistent_repo):
        """
        Tests Challenge 2.1 Mitigation:
        PostgreSQL ON CONFLICT (recorded_at, station_id) DO UPDATE.
        Inserting an observation, then upserting with updated PM2.5 must update in place without duplicates.
        """
        test_ts = datetime(2030, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        test_station = "1"

        try:
            # 1. Insert initial observation
            initial_obs = StationObservation(
                station_id=test_station,
                recorded_at=test_ts,
                pm25=120.5,
                pm10=210.0,
                aqi=185,
            )
            persistent_repo.add_station_observations([initial_obs])

            # Verify initial insert
            fetched = persistent_repo.get_station_hourly_series(
                station_id=test_station,
                start_time=test_ts,
                end_time=test_ts,
            )
            assert len(fetched) == 1
            assert fetched[0].pm25 == 120.5

            # 2. Upsert updated observation for same composite key (recorded_at, station_id)
            updated_obs = StationObservation(
                station_id=test_station,
                recorded_at=test_ts,
                pm25=199.9,  # Changed value
                pm10=305.0,
                aqi=249,
            )
            persistent_repo.add_station_observations([updated_obs])

            # Verify that record was updated, NOT duplicated
            fetched_after = persistent_repo.get_station_hourly_series(
                station_id=test_station,
                start_time=test_ts,
                end_time=test_ts,
            )
            assert len(fetched_after) == 1
            assert fetched_after[0].pm25 == 199.9
            assert fetched_after[0].aqi == 249
        finally:
            # Cleanup test record & refresh timeline cache
            with persistent_repo.db.session_scope() as session:
                session.execute(
                    text("DELETE FROM station_hourly_observations WHERE station_id = :sid AND recorded_at = :ts"),
                    {"sid": test_station, "ts": test_ts},
                )
            persistent_repo.observations._refresh_timeline_cache()



# =============================================================================
# PILLAR 3: SPATIAL ENGINE (PostGIS 3.4 Spatial Types & Geodesic Queries)
# =============================================================================

class TestSpatialEngine:
    """Verifies PostGIS spatial queries casting to ::geography to prevent angular degree distortion."""

    def test_nearest_aerodrome_catchment(self, persistent_repo):
        """
        Tests Challenge 2.3 Mitigation:
        Finding nearest aerodrome using ::geography metric distance.
        Verifies Lahore centroid (31.5497, 74.3436) resolves to OPLA at ~6.5 km (< 10 km).
        """
        engine: PostgisSpatialEngine = persistent_repo.spatial_engine
        assert engine is not None

        nearest = engine.find_nearest_aerodrome(31.5497, 74.3436, max_distance_km=40.0)
        assert nearest is not None
        assert nearest["station_id"] == "OPLA"
        assert nearest["distance_km"] < 10.0
        assert nearest["distance_km"] > 1.0  # Approx 6.5 km

    def test_stations_within_metric_radius(self, persistent_repo):
        """Verifies ST_DWithin on ::geography identifies stations within metric radius in km."""
        engine: PostgisSpatialEngine = persistent_repo.spatial_engine
        stations_25km = engine.find_stations_within_radius(31.5497, 74.3436, radius_km=25.0)

        assert len(stations_25km) >= 5
        station_ids = [s["station_id"] for s in stations_25km]
        assert "OPLA" in station_ids
        # Must not contain distant Multan or Rawalpindi stations
        assert "OPMT" not in station_ids
        assert "OPRN" not in station_ids

    def test_point_in_polygon_containment(self, persistent_repo):
        """Verifies point-in-polygon containment with MultiPolygon nesting normalization."""
        engine: PostgisSpatialEngine = persistent_repo.spatial_engine
        # Coordinates inside Lahore district
        district = engine.find_district_for_point(31.5497, 74.3436)
        assert district is not None
        assert district["district_id"] == 18
        assert district["name"] == "Lahore"

        # Coordinates inside Rawalpindi (33.6007, 73.0679)
        rwp = engine.find_district_for_point(33.6007, 73.0679)
        assert rwp is not None
        assert rwp["name"] == "Rawalpindi"

    def test_border_corridor_filtering(self, persistent_repo):
        """Verifies 120km transboundary border corridor district identification."""
        engine: PostgisSpatialEngine = persistent_repo.spatial_engine
        border_districts = engine.get_border_districts(max_border_distance_km=120.0)
        assert len(border_districts) >= 5

        names = [d["name"] for d in border_districts]
        assert "Lahore" in names
        assert "Kasur" in names
        assert "Narowal" in names


# =============================================================================
# PILLAR 4: HIGH-SPEED CACHE & SSE FAN-OUT (Redis 7.2)
# =============================================================================

class TestHighSpeedCacheAndPubSub:
    """Verifies Redis caching for IDW grids, CPF roses, flux links, and SSE fan-out."""

    def test_redis_cache_operations(self, persistent_repo):
        """Verifies key setting, getting, and json serialization in RedisCacheManager."""
        mgr: RedisCacheManager = persistent_repo.cache_mgr
        assert mgr is not None

        test_key = "paq:test:integration_key"
        test_payload = {"status": "ok", "timestamp": "2026-11-13T12:00:00Z", "val": 42.5}
        mgr.set(test_key, test_payload, ttl_seconds=60)

        retrieved = mgr.get_json(test_key)
        assert retrieved is not None
        assert retrieved["status"] == "ok"
        assert retrieved["val"] == 42.5

        mgr.delete(test_key)
        assert mgr.get(test_key) is None

    def test_analytics_repository_caching(self, persistent_repo):
        """Verifies RedisAnalyticsRepository caching and clearing."""
        analytics: RedisAnalyticsRepository = persistent_repo.analytics
        now = datetime.now(timezone.utc)

        # 1. Surface grid caching
        test_grid = [
            SurfaceGridPoint(x=74.3, y=31.5, value=125.0, nearest_station_km=2.5, alpha=180)
        ]
        analytics.save_surface_grid(timestamp=now, pollutant="PM2.5", resolution=1, grid=test_grid)
        cached_grid = analytics.get_surface_grid(timestamp=now, pollutant="PM2.5", resolution=1)
        assert cached_grid is not None
        assert len(cached_grid) == 1
        assert cached_grid[0].value == 125.0

        # 2. CPF wind rose caching
        test_cpf = CPFRoseResult(
            district_id="Lahore",
            pollutant="PM2.5",
            threshold=75.0,
            calm_ratio=0.05,
            sectors=(0.82, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
            sector_counts=(10, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            sector_exceedances=(8, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        )
        analytics.save_cpf_rose(result=test_cpf)
        cached_cpf = analytics.get_cpf_rose(district_id="Lahore", pollutant="PM2.5")
        assert cached_cpf is not None
        assert cached_cpf.threshold == 75.0
        assert cached_cpf.sectors[0] == 0.82

        # 3. Advection flux caching
        test_flux = [
            AdvectionFluxLink(
                source_district="Amritsar",
                receptor_district="Lahore",
                distance_km=45.0,
                bearing_deg=78.0,
                divergence_deg=5.0,
                flux=340.2,
            )
        ]
        analytics.save_advection_flux(timestamp=now, pollutant="PM2.5", links=test_flux)
        cached_flux = analytics.get_advection_flux(timestamp=now, pollutant="PM2.5")
        assert cached_flux is not None
        assert len(cached_flux) == 1
        assert cached_flux[0].flux == 340.2

        # 4. Transboundary index caching
        test_tb = TransboundaryResult(
            timestamp=now,
            inflow_total=450.0,
            outflow_total=50.0,
            net_flux=400.0,
        )
        analytics.save_transboundary_result(result=test_tb)
        cached_tb = analytics.get_transboundary_result(timestamp=now)
        assert cached_tb is not None
        assert cached_tb.net_flux == 400.0

        # 5. Invalidate / clear cache
        analytics.clear_cache()
        assert analytics.get_surface_grid(timestamp=now, pollutant="PM2.5", resolution=1) is None
        assert analytics.get_cpf_rose(district_id="Lahore", pollutant="PM2.5") is None

    @pytest.mark.anyio
    async def test_redis_pubsub_fanout(self, persistent_repo):
        """Verifies publishing on telemetry channel fans out to subscribers."""
        mgr: RedisCacheManager = persistent_repo.cache_mgr
        import asyncio
        subscriber_queue = asyncio.Queue()
        mgr._local_subscribers.append(subscriber_queue)

        packet = {"event": "hourly_update", "mean_aqi": 185.2, "status": "published"}
        mgr.publish("channel:telemetry:hourly", packet)

        raw = await asyncio.wait_for(subscriber_queue.get(), timeout=2.0)
        data = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
        assert data["event"] == "hourly_update"
        assert data["mean_aqi"] == 185.2


# =============================================================================
# PILLAR 5: CONTINUOUS ROLLUPS (Automated Continuous Aggregates)
# =============================================================================

class TestContinuousRollups:
    """Verifies continuous aggregate rollup queries for hourly and daily rollups."""

    def test_continuous_hourly_district_rollups(self, persistent_repo):
        """Verifies hourly rollup query computes reporting count, mean PM2.5, and vector wind."""
        service: ContinuousRollupService = persistent_repo.continuous_rollups
        assert service is not None

        rollups = service.get_hourly_rollups(district="Lahore", limit=24)
        assert len(rollups) > 0
        assert len(rollups) <= 24

        first = rollups[0]
        assert "timestamp" in first
        assert "pm25" in first
        assert "u" in first
        assert "v" in first
        assert "reporting_count" in first
        assert first["reporting_count"] >= 1

    def test_continuous_daily_district_rollups(self, persistent_repo):
        """Verifies daily rollup query computes daily min, max, mean PM2.5 and peak AQI."""
        service: ContinuousRollupService = persistent_repo.continuous_rollups
        daily = service.get_daily_rollups(district="Lahore", limit=7)

        assert len(daily) > 0
        first = daily[0]
        assert "date" in first
        assert "avg_pm25" in first
        assert "max_aqi" in first
        assert "min_pm25" in first
        assert "max_pm25" in first
        assert first["max_pm25"] >= first["min_pm25"]
        assert first["max_aqi"] > 0


# =============================================================================
# PILLAR 6: END-TO-END FASTAPI GATEWAY INTEGRATION
# =============================================================================

class TestFastApiEndToEndGateway:
    """Verifies all endpoints served through FastAPI with persistent repository backend."""

    @pytest.mark.anyio
    async def test_health_check_endpoint(self, app):
        """GET /health returns healthy status."""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"
            assert data["service"] == "punjab-air-quality-api"

    @pytest.mark.anyio
    async def test_districts_metadata_endpoint(self, app):
        """GET /api/v1/meta/districts returns 41 districts."""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/api/v1/meta/districts")
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert len(data) == 41

    @pytest.mark.anyio
    async def test_continuous_hourly_rollup_endpoint(self, app):
        """GET /api/v1/analytics/rollups/hourly returns hourly rollups."""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/api/v1/analytics/rollups/hourly?district=Lahore")
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert len(data) > 0
            assert "timestamp" in data[0]
            assert "pm25" in data[0]
            assert "reporting_count" in data[0]

    @pytest.mark.anyio
    async def test_continuous_daily_rollup_endpoint(self, app):
        """GET /api/v1/analytics/rollups/daily returns daily continuous aggregate rollups."""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/api/v1/analytics/rollups/daily?district=Lahore")
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert len(data) > 0
            assert "date" in data[0]
            assert "avg_pm25" in data[0]
            assert "max_aqi" in data[0]

    @pytest.mark.anyio
    async def test_sse_live_stream_endpoint(self, app):
        """GET /api/v1/stream/live?max_events=1 returns Server-Sent Events stream frame."""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/api/v1/stream/live?max_events=1")
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            text_data = resp.text
            assert "event: hourly_update" in text_data
            assert "data:" in text_data
