"""
Simulation and Historical Replay Data Pump.
Sequentially feeds hourly observation batches into the ChronometricStagingBuffer,
simulating live streaming data arrival without requiring external network connectivity.
Enables full-system demonstration, end-to-end integration testing, and UI live push verification.
"""
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional

from src.infrastructure.repositories.baseline_repository import BaselineRepository
from src.pipelines.cams import CamsIngestionWorker
from src.pipelines.fallback_engine import FallbackTemplateEngine
from src.pipelines.firms import FirmsIngestionWorker
from src.pipelines.iqair import IQAirIngestionWorker
from src.pipelines.staging_buffer import ChronometricStagingBuffer, HarmonizationCommitReport
from src.services.precomputation_service import PrecomputationService

logger = logging.getLogger(__name__)


class SimulationPump:
    """
    Replays baseline observation frames or synthesizes advancing real-time hours.
    """

    def __init__(
        self,
        repository: BaselineRepository,
        staging_buffer: ChronometricStagingBuffer,
        precomputation_service: Optional[PrecomputationService] = None,
        fallback_engine: Optional[FallbackTemplateEngine] = None,
    ) -> None:
        self.repo = repository
        self.staging = staging_buffer
        self.precomp = precomputation_service
        self.fallback = fallback_engine or FallbackTemplateEngine()

        self.firms_worker = FirmsIngestionWorker(worker_mode="fixture")
        self.iqair_worker = IQAirIngestionWorker(worker_mode="fixture")
        self.cams_worker = CamsIngestionWorker(worker_mode="fixture")

        # Current playback cursor
        self.current_hour_idx = 0
        self.total_baseline_hours = len(self.fallback.hours)

    def tick(self, timestamp: Optional[datetime] = None) -> HarmonizationCommitReport:
        """
        Advances simulation by one hour:
        1. Gathers multi-source observations for the current hour index.
        2. Stages observations in ChronometricStagingBuffer.
        3. Harmonizes, reconciles wind, imputes unmonitored districts, and commits to repository.
        4. Runs precomputation of IDW grids and flux links.
        5. Advances cursor.
        """
        h_idx = self.current_hour_idx % self.total_baseline_hours
        target_ts = timestamp
        if target_ts is None:
            # If repo has a latest timestamp, advance by 1 hour past it, else use baseline hour
            latest = self.repo.get_latest_timestamp()
            if latest:
                target_ts = latest + timedelta(hours=1)
            else:
                target_ts = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

        # 1. Fetch Station Measurements from Fallback Baseline
        station_measurements = self.fallback.get_all_station_measurements_fallback(hour_idx=h_idx)
        station_dicts = [m.model_dump() for m in station_measurements]

        # 2. Fetch Aerodrome METAR reports
        airports_data = []
        for icao in ["OPLA", "OPFA", "OPMT", "OPST", "OPIS", "VIAR"]:
            rep = self.fallback.get_airport_metar_fallback(icao, hour_idx=h_idx)
            if rep:
                airports_data.append(rep)

        # 3. Fetch NWP Wind Forecast
        open_meteo_reports = self.fallback.get_open_meteo_fallback(hour_idx=h_idx)
        nwp_winds: Dict[str, tuple[float, float]] = {}
        for r in open_meteo_reports:
            d_name = r.get("district")
            if d_name and "u_calibrated" in r and "v_calibrated" in r:
                nwp_winds[d_name] = (float(r["u_calibrated"]), float(r["v_calibrated"]))

        # 4. Fetch Auxiliary Feeds (FIRMS, IQAir, CAMS)
        fires = self.firms_worker.get_fallback()
        cross_border = self.iqair_worker.get_fallback()
        cams_list = self.cams_worker.get_fallback()
        cams_summary = cams_list[0] if cams_list else None

        # 5. Stage all feeds
        self.staging.stage_station_data(target_ts, station_dicts)
        self.staging.stage_metar_data(target_ts, airports_data)
        self.staging.stage_nwp_forecast(target_ts, nwp_winds)
        self.staging.stage_firms_fires(target_ts, fires)
        self.staging.stage_cross_border_data(target_ts, cross_border)
        if cams_summary:
            self.staging.stage_cams_summary(target_ts, cams_summary)

        # 6. Harmonize and Commit
        report = self.staging.harmonize_and_commit(target_ts)

        # 7. Asynchronous Precomputation
        if self.precomp:
            try:
                self.precomp.precompute_hourly_artifacts(target_ts)
            except Exception as e:
                logger.warning("Precomputation error during tick: %s", e)

        self.current_hour_idx += 1
        logger.info(
            "SimulationPump tick completed for %s: %d stations, %d districts, mean AQI %.1f, peak AQI %d (%s)",
            target_ts,
            report.stations_committed,
            report.districts_committed,
            report.mean_aqi,
            report.peak_aqi,
            report.peak_district,
        )
        return report
