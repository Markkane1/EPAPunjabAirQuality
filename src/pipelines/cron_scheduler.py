"""
Standing Background Cron Scheduler Daemon for Punjab Air Quality.
Implements asynchronous cron scheduling using APScheduler (AsyncIOScheduler)
and coordinates with Celery beat tasks adhering to DATA_PIPELINES_ARCHITECTURE.md §2 & §3.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Callable, Dict, List, Optional, Union

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


# Standard cron schedules per DATA_PIPELINES_ARCHITECTURE.md §2
CRON_SCHEDULES: Dict[str, Dict[str, Any]] = {
    "epa_punjab": {
        "job_id": "cron_ingest_epa_punjab",
        "stream_id": "STR-01-EPAPUNJAB",
        "name": "EPA Punjab Ground Stations Ingestion",
        "trigger": CronTrigger(minute="5,15", timezone=timezone.utc),
        "cron_expression": "5,15 * * * *",
        "description": "Polls EPA Punjab current AQMS dashboard & fallback stations (cadence 5,15m)",
    },
    "metar": {
        "job_id": "cron_ingest_metar",
        "stream_id": "STR-02-METAR",
        "name": "NOAA AWC Aviation METAR Weather Ingestion",
        "trigger": CronTrigger(minute="10", timezone=timezone.utc),
        "cron_expression": "10 * * * *",
        "description": "Polls NOAA Aviation Weather Center for 12 aerodrome METAR observations",
    },
    "synop": {
        "job_id": "cron_ingest_synop",
        "stream_id": "STR-03-SYNOP",
        "name": "WMO SYNOP Surface Weather Ingestion",
        "trigger": CronTrigger(minute="15", timezone=timezone.utc),
        "cron_expression": "15 * * * *",
        "description": "Decodes WMO SYNOP FM-12 land surface observations across Punjab",
    },
    "open_meteo": {
        "job_id": "cron_ingest_open_meteo",
        "stream_id": "STR-04-ECMWF-IFS",
        "name": "ECMWF IFS NWP 10m Wind Ingestion",
        "trigger": CronTrigger(minute="0", timezone=timezone.utc),
        "cron_expression": "0 * * * *",
        "description": "Queries Open-Meteo ECMWF IFS 0.25° NWP forecast for 41 district centroids",
    },
    "firms": {
        "job_id": "cron_ingest_firms",
        "stream_id": "STR-05-FIRMS",
        "name": "NASA FIRMS VIIRS Active Fire Ingestion",
        "trigger": CronTrigger(hour="3,15", minute="0", timezone=timezone.utc),
        "cron_expression": "0 3,15 * * *",
        "description": "Queries NASA FIRMS VIIRS 375m active thermal anomalies twice daily",
    },
    "iqair": {
        "job_id": "cron_ingest_iqair",
        "stream_id": "STR-06-IQAIR",
        "name": "IQAir Transboundary Regional Ingestion",
        "trigger": CronTrigger(minute="20", timezone=timezone.utc),
        "cron_expression": "20 * * * *",
        "description": "Polls cross-border Indian upwind monitoring stations (Amritsar, Ludhiana, etc.)",
    },
    "cams": {
        "job_id": "cron_ingest_cams",
        "stream_id": "STR-07-CAMS",
        "name": "Copernicus CAMS EAC4 Boundary Aerosol Ingestion",
        "trigger": CronTrigger(hour="4", minute="0", timezone=timezone.utc),
        "cron_expression": "0 4 * * *",
        "description": "Retrieves regional CAMS global atmospheric composition border flux grid",
    },
    "harmonize": {
        "job_id": "cron_harmonize_hourly_commit",
        "stream_id": "STR-HARMONIZE-COMMIT",
        "name": "Hourly Multi-Stream Harmonization & Commit",
        "trigger": CronTrigger(minute="25", timezone=timezone.utc),
        "cron_expression": "25 * * * *",
        "description": "Reconciles staged multi-source observations, commits snapshot, and broadcasts SSE",
    },
}


class StandingCronScheduler:
    """
    Standing background cron scheduler daemon.
    Wraps APScheduler's AsyncIOScheduler to run on the primary FastAPI asyncio event loop.
    Provides execution tracking, job pausing/resuming, and dynamic trigger dispatch.
    """

    def __init__(self, orchestrator: Any = None) -> None:
        self.orchestrator = orchestrator
        self.scheduler: AsyncIOScheduler = AsyncIOScheduler(timezone=timezone.utc)
        self._is_running: bool = False

        # Job execution metrics telemetry
        self.job_stats: Dict[str, Dict[str, Any]] = {}
        for key, conf in CRON_SCHEDULES.items():
            jid = conf["job_id"]
            self.job_stats[jid] = {
                "job_id": jid,
                "stream_key": key,
                "stream_id": conf["stream_id"],
                "name": conf["name"],
                "cron_expression": conf["cron_expression"],
                "description": conf["description"],
                "run_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "last_run": None,
                "last_duration_ms": 0.0,
                "last_error": None,
                "is_paused": False,
            }

        # Simulation replay job tracker
        self.job_stats["simulation_tick"] = {
            "job_id": "simulation_tick",
            "stream_key": "simulation",
            "stream_id": "SIM-REPLAY",
            "name": "Simulation Historical Chronometric Replay",
            "cron_expression": "interval",
            "description": "Advances simulation timeline pump and broadcasts hourly frame",
            "run_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "last_run": None,
            "last_duration_ms": 0.0,
            "last_error": None,
            "is_paused": False,
        }

        # Auto-register all jobs if orchestrator is provided
        if self.orchestrator:
            self.register_live_cron_jobs()
            interval = getattr(self.orchestrator, "auto_tick_interval_seconds", None) or 60.0
            self.register_simulation_replay_job(interval_seconds=interval)

    @property
    def is_running(self) -> bool:
        return self._is_running and self.scheduler.running

    def register_live_cron_jobs(self) -> None:
        """Registers all 7 ingestion workers + harmonization tick cron jobs."""
        if not self.orchestrator:
            logger.warning("StandingCronScheduler: No orchestrator linked. Skipping live job registration.")
            return

        # 1. EPA Punjab
        self._add_or_replace_job(
            job_id="cron_ingest_epa_punjab",
            func=self._run_epa_punjab_job,
            trigger=CRON_SCHEDULES["epa_punjab"]["trigger"],
            name=CRON_SCHEDULES["epa_punjab"]["name"],
        )

        # 2. Aviation METAR
        self._add_or_replace_job(
            job_id="cron_ingest_metar",
            func=self._run_metar_job,
            trigger=CRON_SCHEDULES["metar"]["trigger"],
            name=CRON_SCHEDULES["metar"]["name"],
        )

        # 3. WMO SYNOP
        self._add_or_replace_job(
            job_id="cron_ingest_synop",
            func=self._run_synop_job,
            trigger=CRON_SCHEDULES["synop"]["trigger"],
            name=CRON_SCHEDULES["synop"]["name"],
        )

        # 4. Open-Meteo ECMWF IFS
        self._add_or_replace_job(
            job_id="cron_ingest_open_meteo",
            func=self._run_open_meteo_job,
            trigger=CRON_SCHEDULES["open_meteo"]["trigger"],
            name=CRON_SCHEDULES["open_meteo"]["name"],
        )

        # 5. NASA FIRMS VIIRS
        self._add_or_replace_job(
            job_id="cron_ingest_firms",
            func=self._run_firms_job,
            trigger=CRON_SCHEDULES["firms"]["trigger"],
            name=CRON_SCHEDULES["firms"]["name"],
        )

        # 6. IQAir Regional
        self._add_or_replace_job(
            job_id="cron_ingest_iqair",
            func=self._run_iqair_job,
            trigger=CRON_SCHEDULES["iqair"]["trigger"],
            name=CRON_SCHEDULES["iqair"]["name"],
        )

        # 7. CAMS Boundary
        self._add_or_replace_job(
            job_id="cron_ingest_cams",
            func=self._run_cams_job,
            trigger=CRON_SCHEDULES["cams"]["trigger"],
            name=CRON_SCHEDULES["cams"]["name"],
        )

        # 8. Master Harmonization & Commit
        self._add_or_replace_job(
            job_id="cron_harmonize_hourly_commit",
            func=self._run_harmonize_job,
            trigger=CRON_SCHEDULES["harmonize"]["trigger"],
            name=CRON_SCHEDULES["harmonize"]["name"],
        )

        logger.info("StandingCronScheduler: Registered 8 standard live pipeline cron jobs.")

    def register_simulation_replay_job(self, interval_seconds: float = 60.0) -> None:
        """Registers the periodic auto-tick simulation replay job."""
        if not self.orchestrator:
            return

        trigger = IntervalTrigger(seconds=interval_seconds, timezone=timezone.utc)
        self._add_or_replace_job(
            job_id="simulation_tick",
            func=self._run_simulation_tick_job,
            trigger=trigger,
            name="Simulation Chronometric Replay Tick",
        )
        self.job_stats["simulation_tick"]["cron_expression"] = f"interval:{interval_seconds}s"
        logger.info("StandingCronScheduler: Registered simulation replay job (interval=%.1fs)", interval_seconds)

    def _add_or_replace_job(self, job_id: str, func: Callable, trigger: Any, name: str) -> None:
        """Safely adds or updates an APScheduler job without raising conflicting ID errors."""
        existing = self.scheduler.get_job(job_id)
        if existing:
            self.scheduler.remove_job(job_id)
        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            name=name,
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

    def start(self) -> None:
        """Starts the standing background scheduler."""
        if not self._is_running:
            try:
                self.scheduler.start()
                self._is_running = True
                logger.info("StandingCronScheduler: Daemon started on AsyncIO event loop.")
            except Exception as e:
                logger.error("StandingCronScheduler failed to start: %s", e)

    def shutdown(self, wait: bool = False) -> None:
        """Gracefully shuts down the background scheduler."""
        if self._is_running:
            try:
                self.scheduler.shutdown(wait=wait)
                self._is_running = False
                logger.info("StandingCronScheduler: Daemon shutdown complete.")
            except Exception as e:
                logger.error("StandingCronScheduler shutdown error: %s", e)

    def pause_job(self, job_id: str) -> bool:
        """Pauses a specific cron job."""
        job = self.scheduler.get_job(job_id)
        if job:
            job.pause()
            if job_id in self.job_stats:
                self.job_stats[job_id]["is_paused"] = True
            logger.info("StandingCronScheduler: Paused job '%s'", job_id)
            return True
        return False

    def resume_job(self, job_id: str) -> bool:
        """Resumes a paused cron job."""
        job = self.scheduler.get_job(job_id)
        if job:
            job.resume()
            if job_id in self.job_stats:
                self.job_stats[job_id]["is_paused"] = False
            logger.info("StandingCronScheduler: Resumed job '%s'", job_id)
            return True
        return False

    async def trigger_job(self, job_id: str) -> Dict[str, Any]:
        """Manually triggers an immediate run of a scheduled job."""
        dispatchers = {
            "cron_ingest_epa_punjab": self._run_epa_punjab_job,
            "cron_ingest_metar": self._run_metar_job,
            "cron_ingest_synop": self._run_synop_job,
            "cron_ingest_open_meteo": self._run_open_meteo_job,
            "cron_ingest_firms": self._run_firms_job,
            "cron_ingest_iqair": self._run_iqair_job,
            "cron_ingest_cams": self._run_cams_job,
            "cron_harmonize_hourly_commit": self._run_harmonize_job,
            "simulation_tick": self._run_simulation_tick_job,
        }
        fn = dispatchers.get(job_id)
        if not fn:
            raise ValueError(f"Job ID '{job_id}' is not recognized.")

        start_time = datetime.now(timezone.utc)
        result = await fn()
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0

        return {
            "job_id": job_id,
            "triggered_at": start_time.isoformat(),
            "duration_ms": round(duration_ms, 2),
            "result": str(result),
            "status": "success",
        }

    # =========================================================================
    # Internal Job Handlers with Metrics Tracking
    # =========================================================================

    async def _track_job_execution(self, job_id: str, coro_fn: Callable) -> Any:
        stats = self.job_stats.get(job_id)
        start_t = datetime.now(timezone.utc)
        if stats:
            stats["run_count"] += 1
            stats["last_run"] = start_t.isoformat()

        try:
            res = await coro_fn()
            dur = (datetime.now(timezone.utc) - start_t).total_seconds() * 1000.0
            if stats:
                stats["success_count"] += 1
                stats["last_duration_ms"] = round(dur, 2)
                stats["last_error"] = None
            return res
        except Exception as e:
            dur = (datetime.now(timezone.utc) - start_t).total_seconds() * 1000.0
            err_msg = str(e)
            logger.error("Error in scheduled cron job '%s': %s", job_id, err_msg)
            if stats:
                stats["failure_count"] += 1
                stats["last_duration_ms"] = round(dur, 2)
                stats["last_error"] = err_msg
            return None

    async def _run_epa_punjab_job(self) -> Any:
        async def _exec():
            if not self.orchestrator:
                return None
            worker = self.orchestrator.workers.get("epa_punjab")
            if worker:
                return await worker.run()
            return None
        return await self._track_job_execution("cron_ingest_epa_punjab", _exec)

    async def _run_metar_job(self) -> Any:
        async def _exec():
            if not self.orchestrator:
                return None
            worker = self.orchestrator.workers.get("metar")
            if worker:
                reports = await worker.run()
                target_ts = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
                self.orchestrator.staging.stage_metar_data(target_ts, reports)
                return reports
            return None
        return await self._track_job_execution("cron_ingest_metar", _exec)

    async def _run_synop_job(self) -> Any:
        async def _exec():
            if not self.orchestrator:
                return None
            worker = self.orchestrator.workers.get("synop")
            if worker:
                return await worker.run()
            return None
        return await self._track_job_execution("cron_ingest_synop", _exec)

    async def _run_open_meteo_job(self) -> Any:
        async def _exec():
            if not self.orchestrator:
                return None
            worker = self.orchestrator.workers.get("open_meteo")
            if worker:
                reports = await worker.run()
                target_ts = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
                nwp_winds: Dict[str, tuple[float, float]] = {}
                for r in reports:
                    d_name = r.get("district")
                    if d_name and "u_calibrated" in r and "v_calibrated" in r:
                        nwp_winds[d_name] = (float(r["u_calibrated"]), float(r["v_calibrated"]))
                self.orchestrator.staging.stage_nwp_forecast(target_ts, nwp_winds)
                return reports
            return None
        return await self._track_job_execution("cron_ingest_open_meteo", _exec)

    async def _run_firms_job(self) -> Any:
        async def _exec():
            if not self.orchestrator:
                return None
            worker = self.orchestrator.workers.get("firms")
            if worker:
                fires = await worker.run()
                target_ts = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
                self.orchestrator.staging.stage_firms_fires(target_ts, fires)
                return fires
            return None
        return await self._track_job_execution("cron_ingest_firms", _exec)

    async def _run_iqair_job(self) -> Any:
        async def _exec():
            if not self.orchestrator:
                return None
            worker = self.orchestrator.workers.get("iqair")
            if worker:
                cb = worker.get_fallback()
                target_ts = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
                self.orchestrator.staging.stage_cross_border_data(target_ts, cb)
                return cb
            return None
        return await self._track_job_execution("cron_ingest_iqair", _exec)

    async def _run_cams_job(self) -> Any:
        async def _exec():
            if not self.orchestrator:
                return None
            worker = self.orchestrator.workers.get("cams")
            if worker:
                cams_list = worker.get_fallback()
                summary = cams_list[0] if cams_list else None
                if summary:
                    target_ts = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
                    self.orchestrator.staging.stage_cams_summary(target_ts, summary)
                return summary
            return None
        return await self._track_job_execution("cron_ingest_cams", _exec)

    async def _run_harmonize_job(self) -> Any:
        async def _exec():
            if not self.orchestrator:
                return None
            return await self.orchestrator.tick_async(mode="live")
        return await self._track_job_execution("cron_harmonize_hourly_commit", _exec)

    async def _run_simulation_tick_job(self) -> Any:
        async def _exec():
            if not self.orchestrator:
                return None
            return await self.orchestrator.tick_async(mode="simulation")
        return await self._track_job_execution("simulation_tick", _exec)

    # =========================================================================
    # Status & Telemetry API
    # =========================================================================

    def get_scheduler_status(self) -> Dict[str, Any]:
        """Returns high-level status of the standing cron daemon."""
        jobs = self.scheduler.get_jobs()
        total_runs = sum(s["run_count"] for s in self.job_stats.values())
        total_failures = sum(s["failure_count"] for s in self.job_stats.values())

        return {
            "engine": "APScheduler.AsyncIOScheduler",
            "is_running": self.is_running,
            "total_registered_jobs": len(jobs),
            "total_executions": total_runs,
            "total_failures": total_failures,
            "timezone": "UTC",
            "active_mode": getattr(self.orchestrator, "mode", "unknown") if self.orchestrator else "unknown",
        }

    def get_jobs_status(self) -> List[Dict[str, Any]]:
        """Returns detailed status and next fire times for each registered cron job."""
        res: List[Dict[str, Any]] = []
        now = datetime.now(timezone.utc)
        for jid, stats in self.job_stats.items():
            job = self.scheduler.get_job(jid)
            next_fire = None
            if job:
                next_run = getattr(job, "next_run_time", None)
                if next_run:
                    next_fire = next_run.isoformat()
                elif getattr(job, "trigger", None):
                    try:
                        computed = job.trigger.get_next_fire_time(None, now)
                        if computed:
                            next_fire = computed.isoformat()
                    except Exception:
                        next_fire = None

            is_active = job is not None
            item = dict(stats)
            item["is_registered"] = is_active
            item["next_run_time"] = next_fire
            res.append(item)
        return res
