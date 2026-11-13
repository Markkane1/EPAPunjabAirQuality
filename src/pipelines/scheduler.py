"""
Asynchronous Ingestion Pipeline Orchestrator and Background Scheduler.
Coordinates periodic external worker execution or simulation replay ticks,
broadcasts real-time events to connected client streams, and maintains
operational health and circuit-breaker telemetry.
Adheres to DATA_PIPELINES_ARCHITECTURE.md §1 & §8.
"""
import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Callable, Dict, List, Optional, Set

from src.infrastructure.repositories.baseline_repository import BaselineRepository
from src.pipelines.cams import CamsIngestionWorker
from src.pipelines.epa_punjab import EPAPunjabIngestionWorker
from src.pipelines.fallback_engine import FallbackTemplateEngine
from src.pipelines.firms import FirmsIngestionWorker
from src.pipelines.iqair import IQAirIngestionWorker
from src.pipelines.metar import MetarIngestionWorker
from src.pipelines.open_meteo import OpenMeteoIngestionWorker
from src.pipelines.simulation_pump import SimulationPump
from src.pipelines.staging_buffer import ChronometricStagingBuffer, HarmonizationCommitReport
from src.pipelines.synop import SynopIngestionWorker
from src.pipelines.cron_scheduler import StandingCronScheduler
from src.services.precomputation_service import PrecomputationService

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Master pipeline scheduler and stream orchestrator.
    Manages background tasks, cron execution, simulation replay, and SSE broadcast dispatch.
    """

    def __init__(
        self,
        repository: BaselineRepository,
        staging_buffer: Optional[ChronometricStagingBuffer] = None,
        precomputation_service: Optional[PrecomputationService] = None,
        mode: str = "simulation",  # 'simulation' or 'live'
        auto_tick_interval_seconds: Optional[float] = None,  # e.g. 60.0 for periodic auto-replay
    ) -> None:
        self.repo = repository
        self.staging = staging_buffer or ChronometricStagingBuffer(repository=repository)
        self.precomp = precomputation_service
        self.mode = mode
        self.auto_tick_interval_seconds = auto_tick_interval_seconds

        # Simulation pump
        self.pump = SimulationPump(
            repository=repository,
            staging_buffer=self.staging,
            precomputation_service=self.precomp,
        )

        # Worker Registry (prepared for live activation)
        self.workers: Dict[str, Any] = {
            "epa_punjab": EPAPunjabIngestionWorker(),
            "metar": MetarIngestionWorker(),
            "synop": SynopIngestionWorker(),
            "open_meteo": OpenMeteoIngestionWorker(),
            "firms": FirmsIngestionWorker(),
            "iqair": IQAirIngestionWorker(),
            "cams": CamsIngestionWorker(),
        }

        # Background runner state
        self._running: bool = False
        self._background_task: Optional[asyncio.Task] = None
        self._listeners: Set[asyncio.Queue] = set()
        self.total_ticks: int = 0
        self.last_tick_time: Optional[datetime] = None
        self.last_report: Optional[HarmonizationCommitReport] = None

        # Standing background cron scheduler daemon (APScheduler)
        self.cron_scheduler = StandingCronScheduler(orchestrator=self)

    def subscribe(self) -> asyncio.Queue:
        """Subscribes an SSE streaming client to receive new hourly update frames."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._listeners.add(queue)
        logger.debug("New SSE client subscribed to orchestrator (total listeners: %d)", len(self._listeners))
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Removes a disconnected client queue."""
        self._listeners.discard(queue)
        logger.debug("SSE client unsubscribed (remaining listeners: %d)", len(self._listeners))

    def _broadcast(self, payload: Dict[str, Any]) -> None:
        """Pushes hourly frame payload to all active listener queues and Redis Pub/Sub cluster."""
        for q in list(self._listeners):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning("Listener queue full, dropping frame.")
            except Exception as e:
                logger.debug("Error broadcasting to queue: %s", e)

        # Fan-out to Redis Pub/Sub cluster for multi-worker SSE broadcast
        if hasattr(self.repo, "cache_mgr") and self.repo.cache_mgr:
            try:
                self.repo.cache_mgr.publish("channel:telemetry:hourly", payload)
            except Exception as e:
                logger.debug("Redis pub/sub publish notice: %s", e)

    async def start(self) -> None:
        """Starts background orchestration loop and standing cron daemons."""
        if self._running:
            return
        self._running = True
        logger.info("Starting PipelineOrchestrator in %s mode...", self.mode.upper())

        # Start standing background cron scheduler daemon
        self.cron_scheduler.start()
        if self.mode == "live":
            self.cron_scheduler.register_live_cron_jobs()
        elif self.auto_tick_interval_seconds and self.auto_tick_interval_seconds > 0:
            self.cron_scheduler.register_simulation_replay_job(interval_seconds=self.auto_tick_interval_seconds)

        if self.auto_tick_interval_seconds and self.auto_tick_interval_seconds > 0:
            self._background_task = asyncio.create_task(self._auto_tick_loop())

    async def stop(self) -> None:
        """Gracefully stops background orchestration loop and standing cron daemons."""
        self._running = False
        self.cron_scheduler.shutdown(wait=False)
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None
        logger.info("PipelineOrchestrator stopped.")

    async def _auto_tick_loop(self) -> None:
        """Periodic background auto-tick loop for simulation replay."""
        interval = self.auto_tick_interval_seconds or 60.0
        try:
            while self._running:
                await asyncio.sleep(interval)
                if not self._running:
                    break
                await self.tick_async()
        except asyncio.CancelledError:
            pass

    async def tick_async(self, timestamp: Optional[datetime] = None) -> HarmonizationCommitReport:
        """Asynchronously executes a tick and broadcasts the resulting snapshot."""
        loop = asyncio.get_running_loop()
        report = await loop.run_in_executor(None, self.pump.tick, timestamp)
        self.total_ticks += 1
        self.last_tick_time = report.timestamp
        self.last_report = report

        # Format update packet for SSE clients
        latest_ts_iso = report.timestamp.isoformat()
        broadcast_payload = {
            "timestamp": latest_ts_iso,
            "total_hours": self.repo.total_hours(),
            "provincial_summary": {
                "mean_aqi": report.mean_aqi,
                "peak_district": report.peak_district,
                "peak_aqi": report.peak_aqi,
                "reporting_stations": report.stations_committed,
                "reporting_districts": report.districts_committed,
            },
            "auxiliary": {
                "active_fires_count": report.active_fires_count,
                "cross_border_cities_count": report.cross_border_cities_count,
                "net_transboundary_flux": report.net_transboundary_flux,
            },
        }
        self._broadcast(broadcast_payload)
        return report

    def set_mode(self, mode: str) -> None:
        """Sets the orchestrator execution mode ('simulation' or 'live')."""
        normalized = mode.strip().lower()
        if normalized not in ("simulation", "live"):
            raise ValueError(f"Invalid mode '{mode}'. Expected 'simulation' or 'live'.")
        self.mode = normalized
        logger.info("PipelineOrchestrator switched operating mode to: %s", self.mode.upper())

        # Update registered standing cron jobs according to mode
        if self._running:
            if self.mode == "live":
                self.cron_scheduler.register_live_cron_jobs()
            elif self.auto_tick_interval_seconds and self.auto_tick_interval_seconds > 0:
                self.cron_scheduler.register_simulation_replay_job(interval_seconds=self.auto_tick_interval_seconds)

    async def tick_live_async(self, timestamp: Optional[datetime] = None) -> HarmonizationCommitReport:
        """
        Executes an asynchronous live ingestion cycle utilizing active external live APIs:
        1. STR-02-METAR: Queries NOAA Aviation Weather Center for 12 aerodromes.
        2. STR-04-ECMWF-IFS: Queries Open-Meteo ECMWF IFS 10m wind across all 41 district centroids.
        3. Ground AQMS: Combines current hour's station measurements from fallback/replay.
        4. Auxiliary feeds: Staged via workers.
        5. Chronometric Staging: Reconciles live winds, runs discrete geodesic IDW, commits to repo.
        6. Precomputes real-time spatial surfaces and broadcasts SSE update packet.
        """
        target_ts = timestamp or datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

        # 1. Fetch Live METAR from NOAA AWC
        metar_reports = await self.workers["metar"].run(target_timestamp=target_ts)
        self.staging.stage_metar_data(target_ts, metar_reports)

        # 2. Fetch Live Open-Meteo ECMWF IFS winds across 41 district centroids
        om_reports = await self.workers["open_meteo"].run()
        nwp_winds: Dict[str, tuple[float, float]] = {}
        for r in om_reports:
            d_name = r.get("district")
            if d_name and "u_calibrated" in r and "v_calibrated" in r:
                nwp_winds[d_name] = (float(r["u_calibrated"]), float(r["v_calibrated"]))
        self.staging.stage_nwp_forecast(target_ts, nwp_winds)

        # 3. Ground Stations: Live EPA Punjab AQMS Feed with automatic fallback
        h_idx = self.pump.current_hour_idx % self.pump.total_baseline_hours
        try:
            epa_measurements = await self.workers["epa_punjab"].run(hour_idx=h_idx)
            station_dicts = [m.model_dump() for m in epa_measurements]
        except Exception as e:
            logger.warning("EPA Punjab live fetch failed, using fallback: %s", e)
            fallback_meas = self.pump.fallback.get_all_station_measurements_fallback(hour_idx=h_idx)
            station_dicts = [m.model_dump() for m in fallback_meas]
        self.staging.stage_station_data(target_ts, station_dicts)

        # 4. Auxiliary Feeds (FIRMS live, IQAir, CAMS)
        fires = await self.workers["firms"].run()
        cross_border = self.workers["iqair"].get_fallback()
        cams_list = self.workers["cams"].get_fallback()
        cams_summary = cams_list[0] if cams_list else None
        self.staging.stage_firms_fires(target_ts, fires)
        self.staging.stage_cross_border_data(target_ts, cross_border)
        if cams_summary:
            self.staging.stage_cams_summary(target_ts, cams_summary)

        # 5. Harmonize and commit atomically
        loop = asyncio.get_running_loop()
        report = await loop.run_in_executor(None, self.staging.harmonize_and_commit, target_ts)

        # 6. Precompute hourly spatial/analytics artifacts
        if self.precomp:
            try:
                await loop.run_in_executor(None, self.precomp.precompute_hourly_artifacts, target_ts)
            except Exception as e:
                logger.warning("Live precomputations warning: %s", e)

        # 7. Advance pump cursor and update state
        self.pump.current_hour_idx += 1
        self.total_ticks += 1
        self.last_tick_time = report.timestamp
        self.last_report = report

        # 8. Broadcast to connected SSE subscribers
        broadcast_payload = {
            "timestamp": report.timestamp.isoformat(),
            "total_hours": self.repo.total_hours(),
            "mode": "live",
            "provincial_summary": {
                "mean_aqi": report.mean_aqi,
                "peak_district": report.peak_district,
                "peak_aqi": report.peak_aqi,
                "reporting_stations": report.stations_committed,
                "reporting_districts": report.districts_committed,
            },
            "auxiliary": {
                "active_fires_count": report.active_fires_count,
                "cross_border_cities_count": report.cross_border_cities_count,
                "net_transboundary_flux": report.net_transboundary_flux,
            },
            "live_streams": {
                "metar": {
                    "healthy": self.workers["metar"].is_healthy,
                    "records": len(metar_reports),
                },
                "open_meteo": {
                    "healthy": self.workers["open_meteo"].is_healthy,
                    "records": len(om_reports),
                },
                "firms": {
                    "healthy": self.workers["firms"].is_healthy,
                    "records": len(fires),
                },
            },
        }
        self._broadcast(broadcast_payload)
        return report

    async def tick_async(
        self,
        timestamp: Optional[datetime] = None,
        mode: Optional[str] = None,
    ) -> HarmonizationCommitReport:
        """Asynchronously executes a tick in simulation or live mode and broadcasts the resulting snapshot."""
        effective_mode = mode.lower() if mode else self.mode
        if effective_mode == "live":
            return await self.tick_live_async(timestamp=timestamp)

        loop = asyncio.get_running_loop()
        report = await loop.run_in_executor(None, self.pump.tick, timestamp)
        self.total_ticks += 1
        self.last_tick_time = report.timestamp
        self.last_report = report

        # Format update packet for SSE clients
        latest_ts_iso = report.timestamp.isoformat()
        broadcast_payload = {
            "timestamp": latest_ts_iso,
            "total_hours": self.repo.total_hours(),
            "mode": "simulation",
            "provincial_summary": {
                "mean_aqi": report.mean_aqi,
                "peak_district": report.peak_district,
                "peak_aqi": report.peak_aqi,
                "reporting_stations": report.stations_committed,
                "reporting_districts": report.districts_committed,
            },
            "auxiliary": {
                "active_fires_count": report.active_fires_count,
                "cross_border_cities_count": report.cross_border_cities_count,
                "net_transboundary_flux": report.net_transboundary_flux,
            },
        }
        self._broadcast(broadcast_payload)
        return report

    def tick_sync(self, timestamp: Optional[datetime] = None) -> HarmonizationCommitReport:
        """Synchronously executes a tick."""
        report = self.pump.tick(timestamp)
        self.total_ticks += 1
        self.last_tick_time = report.timestamp
        self.last_report = report
        return report

    def get_status(self) -> Dict[str, Any]:
        """Returns comprehensive operational health metrics."""
        return {
            "status": "running" if self._running else "stopped",
            "mode": self.mode,
            "total_ticks": self.total_ticks,
            "last_tick_time": self.last_tick_time.isoformat() if self.last_tick_time else None,
            "connected_sse_clients": len(self._listeners),
            "auto_tick_interval_seconds": self.auto_tick_interval_seconds,
            "cron_scheduler": self.cron_scheduler.get_scheduler_status(),
            "scheduled_cron_jobs": self.cron_scheduler.get_jobs_status(),
            "live_enabled_streams": ["STR-02-METAR", "STR-04-ECMWF-IFS", "STR-05-FIRMS"],
            "live_stream_status": {
                "metar": {
                    "stream_id": "STR-02-METAR",
                    "name": "NOAA Aviation Weather Center METAR",
                    "status": "connected" if self.workers["metar"].is_healthy else "degraded",
                    "last_run": self.workers["metar"].last_run.isoformat() if self.workers["metar"].last_run else None,
                    "circuit_open": self.workers["metar"].circuit_breaker_open,
                },
                "open_meteo": {
                    "stream_id": "STR-04-ECMWF-IFS",
                    "name": "ECMWF IFS Open-Meteo 10m Wind",
                    "status": "connected" if self.workers["open_meteo"].is_healthy else "degraded",
                    "last_run": self.workers["open_meteo"].last_run.isoformat() if self.workers["open_meteo"].last_run else None,
                    "circuit_open": self.workers["open_meteo"].circuit_breaker_open,
                },
                "firms": {
                    "stream_id": "STR-05-FIRMS",
                    "name": "NASA FIRMS VIIRS Active Fire",
                    "status": "connected" if self.workers["firms"].is_healthy else "degraded",
                    "last_run": self.workers["firms"].last_run.isoformat() if self.workers["firms"].last_run else None,
                    "circuit_open": self.workers["firms"].circuit_breaker_open,
                },
            },
            "workers": {
                wid: {
                    "stream_id": w.stream_id,
                    "name": w.name,
                    "is_healthy": w.is_healthy,
                    "cadence": w.polling_cadence,
                    "circuit_open": w.circuit_breaker_open,
                }
                for wid, w in self.workers.items()
            },
        }

    def get_cron_jobs(self) -> List[Dict[str, Any]]:
        """Returns status and next fire times for all registered standing cron jobs."""
        return self.cron_scheduler.get_jobs_status()

    async def trigger_cron_job(self, job_id: str) -> Dict[str, Any]:
        """Manually triggers an immediate run of a standing cron job."""
        return await self.cron_scheduler.trigger_job(job_id)

    def pause_cron_job(self, job_id: str) -> bool:
        """Pauses a specific standing cron job."""
        return self.cron_scheduler.pause_job(job_id)

    def resume_cron_job(self, job_id: str) -> bool:
        """Resumes a paused standing cron job."""
        return self.cron_scheduler.resume_job(job_id)
