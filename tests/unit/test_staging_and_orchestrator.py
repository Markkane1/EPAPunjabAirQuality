"""
Unit test suite for ChronometricStagingBuffer, PipelineOrchestrator, SimulationPump,
and structural stream workers (FIRMS, IQAir, CAMS).
Verifies:
1. FirmsIngestionWorker VIIRS active fires parsing and gas flaring suppression (<27°N).
2. IQAirIngestionWorker cross-border city parsing and PEPC AQI normalization.
3. CamsIngestionWorker boundary mass flux summary and net balance calculations.
4. ChronometricStagingBuffer multi-source staging, wind reconciliation, and atomic commits.
5. BaselineRepository dynamic 24-h rolling average calculations.
6. PipelineOrchestrator subscription, broadcast, and simulation ticks.
"""
import asyncio
from datetime import datetime, timezone
import pytest

from src.infrastructure.repositories.baseline_repository import BaselineRepository
from src.pipelines.cams import CamsIngestionWorker, CamsBoundarySummary
from src.pipelines.firms import FirmsIngestionWorker, ActiveFireDetection
from src.pipelines.iqair import IQAirIngestionWorker, CrossBorderCityObservation
from src.pipelines.scheduler import PipelineOrchestrator
from src.pipelines.simulation_pump import SimulationPump
from src.pipelines.staging_buffer import ChronometricStagingBuffer
from src.services.analytics_service import AnalyticsService
from src.services.precomputation_service import PrecomputationService
from src.services.spatial_service import SpatialService


class TestStructuralWorkers:
    """Tests structural worker classes prepared for live feeds."""

    def test_firms_worker_parsing_and_gas_flaring_filter(self):
        worker = FirmsIngestionWorker(worker_mode="fixture")
        raw_fires = [
            # Legitimate agricultural stubble fire
            {"latitude": 31.55, "longitude": 74.35, "brightness": 340.0, "frp": 30.0, "acq_date": "2026-11-13", "acq_time": "1200"},
            # Industrial gas flaring candidate in Rajasthan (< 27.0°N) -> MUST BE FILTERED
            {"latitude": 26.50, "longitude": 71.10, "brightness": 360.0, "frp": 75.0, "acq_date": "2026-11-13", "acq_time": "1200"},
        ]
        parsed = worker.parse_and_validate(raw_fires)
        assert len(parsed) == 1
        assert parsed[0].latitude == 31.55
        assert parsed[0].region == "Punjab (Pakistan)"

    def test_iqair_worker_parsing_and_pepc_conversion(self):
        worker = IQAirIngestionWorker(worker_mode="fixture")
        raw_cities = [
            {"city": "Amritsar", "state": "Punjab", "country": "India", "distance_km": 28.0, "latitude": 31.63, "longitude": 74.87, "pm25_val": 160.0, "us_aqi": 210},
        ]
        parsed = worker.parse_and_validate(raw_cities)
        assert len(parsed) == 1
        c = parsed[0]
        assert c.city == "Amritsar"
        assert c.pm25 == 160.0
        # For PM2.5 = 160.0 in Punjab PEPC (140-250 range), PEPC AQI is in 201-300 range (Unhealthy)
        assert 200 <= c.pepc_aqi <= 300
        assert c.pepc_tier == "Unhealthy"

    def test_cams_worker_parsing_and_status(self):
        worker = CamsIngestionWorker(worker_mode="fixture")
        raw_cams = {
            "inflow_kg_per_s": 500.0,
            "outflow_kg_per_s": 100.0,
            "border_belt_index": 310.0,
        }
        summaries = worker.parse_and_validate(raw_cams)
        assert len(summaries) == 1
        s = summaries[0]
        assert s.inflow_kg_per_s == 500.0
        assert s.outflow_kg_per_s == 100.0
        assert s.net_flux_kg_per_s == 400.0
        assert s.status == "NET_INFLOW_ALERT"


class TestChronometricStagingBuffer:
    """Tests staging, harmonization, and atomic repository commits."""

    @pytest.fixture
    def staging_setup(self):
        repo = BaselineRepository()
        staging = ChronometricStagingBuffer(repository=repo)
        return repo, staging

    def test_staging_and_harmonization_commit(self, staging_setup):
        repo, staging = staging_setup
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

        # Stage synthetic station records
        station_records = [
            {
                "station_id": "10",
                "station_name": "DHQ Sheikhupura",
                "district": "Sheikhupura",
                "pm25": 150.0,
                "pm10": 260.0,
                "wind_speed": 2.0,
                "wind_direction": 180.0,
            },
            {
                "station_id": "23",
                "station_name": "Punjab University-LHR",
                "district": "Lahore",
                "pm25": 220.0,
                "pm10": 340.0,
                "wind_speed": 1.5,
                "wind_direction": 90.0,
            },
        ]
        metar_records = [
            {"icao": "OPLA", "wind_speed_ms": 2.5, "wind_direction_deg": 180.0},
        ]
        nwp_winds = {
            "Rawalpindi": (-1.5, 2.0),
            "Faisalabad": (0.5, -1.0),
        }

        staging.stage_station_data(now, station_records)
        staging.stage_metar_data(now, metar_records)
        staging.stage_nwp_forecast(now, nwp_winds)

        report = staging.harmonize_and_commit(now)
        assert report.stations_committed == 2
        # All 41 districts must be committed (either aggregated or IDW imputed)
        assert report.districts_committed == 41
        assert report.unmonitored_imputed > 0
        assert report.peak_aqi > 0

        # Verify repository updated latest timestamp
        assert repo.get_latest_timestamp() == now
        assert repo.get_district_observation("Lahore", now) is not None
        assert repo.get_station_observation("10", now) is not None


class TestRollingMeanAndOrchestrator:
    """Tests rolling 24h mean and orchestrator execution."""

    def test_rolling_24h_mean_calculation(self):
        repo = BaselineRepository()
        latest = repo.get_latest_timestamp()
        assert latest is not None

        # Calculate true rolling 24-h mean for Lahore
        mean_lahore = repo.calculate_district_24h_rolling_mean("Lahore", timestamp=latest, pollutant="PM2.5")
        assert mean_lahore is not None
        assert mean_lahore > 0

    @pytest.mark.anyio
    async def test_orchestrator_tick_and_subscription(self):
        repo = BaselineRepository()
        spatial_svc = SpatialService(repo=repo)
        analytics_svc = AnalyticsService(repo=repo)
        precomp_svc = PrecomputationService(repo, spatial_svc, analytics_svc)
        orchestrator = PipelineOrchestrator(
            repository=repo,
            precomputation_service=precomp_svc,
            mode="simulation",
        )

        queue = orchestrator.subscribe()
        assert queue in orchestrator._listeners

        # Trigger tick
        report = await orchestrator.tick_async()
        assert report is not None
        assert report.districts_committed == 41

        # Verify broadcast arrived in queue
        event = await asyncio.wait_for(queue.get(), timeout=2.0)
        assert "timestamp" in event
        assert "provincial_summary" in event
        assert event["provincial_summary"]["reporting_districts"] == 41

        orchestrator.unsubscribe(queue)
        assert queue not in orchestrator._listeners

    @pytest.mark.anyio
    async def test_orchestrator_mode_switch_and_live_tick(self):
        repo = BaselineRepository()
        spatial_svc = SpatialService(repo=repo)
        analytics_svc = AnalyticsService(repo=repo)
        precomp_svc = PrecomputationService(repo, spatial_svc, analytics_svc)
        orchestrator = PipelineOrchestrator(
            repository=repo,
            precomputation_service=precomp_svc,
            mode="simulation",
        )

        # 1. Mode switch validation
        orchestrator.set_mode("live")
        assert orchestrator.mode == "live"
        with pytest.raises(ValueError):
            orchestrator.set_mode("unsupported_mode")

        # 2. Live tick execution with active NOAA METAR and Open-Meteo feeds
        queue = orchestrator.subscribe()
        report = await orchestrator.tick_async(mode="live")
        assert report is not None
        assert report.districts_committed == 41
        assert report.stations_committed > 0

        # 3. Verify SSE broadcast event carries live metadata
        event = await asyncio.wait_for(queue.get(), timeout=5.0)
        assert event["mode"] == "live"
        assert "live_streams" in event
        assert "metar" in event["live_streams"]
        assert "open_meteo" in event["live_streams"]

        # 4. Status reflects live enabled streams
        status = orchestrator.get_status()
        assert status["mode"] == "live"
        assert "STR-02-METAR" in status["live_enabled_streams"]
        assert "STR-04-ECMWF-IFS" in status["live_enabled_streams"]
        assert status["live_stream_status"]["metar"]["status"] in ("connected", "degraded")
        assert status["live_stream_status"]["open_meteo"]["status"] in ("connected", "degraded")

        orchestrator.unsubscribe(queue)
