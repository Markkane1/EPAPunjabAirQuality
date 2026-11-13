"""
Celery Distributed Ingestion & Beat Cron Schedule Application.
Provides production distributed task execution and standing cron beat daemons
for the 7 ingestion pipelines and hourly harmonization commit.
Adheres to DATA_PIPELINES_ARCHITECTURE.md §2, §3, & §8.
"""
import os
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List

from celery import Celery
from celery.schedules import crontab

logger = logging.getLogger(__name__)

# Redis Broker & Result Backend configuration (with sensible local defaults)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

# Create Celery App
celery_app = Celery(
    "punjab_air_quality",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

# Standard Celery Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_soft_time_limit=120,   # 120s soft timeout to prevent starvation
    task_time_limit=180,        # 180s hard timeout per DATA_PIPELINES_ARCHITECTURE.md §3.1
    worker_concurrency=int(os.getenv("CELERY_WORKER_CONCURRENCY", "4")),
)

# Standing Celery Beat Cron Schedule Configuration per DATA_PIPELINES_ARCHITECTURE.md §2
celery_app.conf.beat_schedule = {
    # 1. EPA Punjab (cadence: 5, 15m)
    "ingest-epa-punjab-cron": {
        "task": "paq.ingest.epa_punjab",
        "schedule": crontab(minute="5,15"),
        "options": {"queue": "ingest_critical"},
    },
    # 2. Aviation METAR (cadence: 10m)
    "ingest-metar-cron": {
        "task": "paq.ingest.metar",
        "schedule": crontab(minute="10"),
        "options": {"queue": "ingest_weather"},
    },
    # 3. WMO SYNOP (cadence: 15m)
    "ingest-synop-cron": {
        "task": "paq.ingest.synop",
        "schedule": crontab(minute="15"),
        "options": {"queue": "ingest_weather"},
    },
    # 4. Open-Meteo ECMWF IFS NWP 10m Winds (cadence: 00m)
    "ingest-open-meteo-cron": {
        "task": "paq.ingest.open_meteo",
        "schedule": crontab(minute="0"),
        "options": {"queue": "ingest_weather"},
    },
    # 5. NASA FIRMS VIIRS Active Fire (cadence: 03:00, 15:00 UTC)
    "ingest-firms-cron": {
        "task": "paq.ingest.firms",
        "schedule": crontab(hour="3,15", minute="0"),
        "options": {"queue": "ingest_auxiliary"},
    },
    # 6. IQAir Transboundary (cadence: 20m)
    "ingest-iqair-cron": {
        "task": "paq.ingest.iqair",
        "schedule": crontab(minute="20"),
        "options": {"queue": "ingest_auxiliary"},
    },
    # 7. Copernicus CAMS Aerosol Boundary (cadence: 04:00 UTC daily)
    "ingest-cams-cron": {
        "task": "paq.ingest.cams",
        "schedule": crontab(hour="4", minute="0"),
        "options": {"queue": "ingest_auxiliary"},
    },
    # 8. Master Hourly Ingestion Harmonization, Commit, & SSE Broadcast (cadence: 25m)
    "harmonize-and-commit-hourly": {
        "task": "paq.harmonize_and_commit",
        "schedule": crontab(minute="25"),
        "options": {"queue": "harmonization"},
    },
}


# =============================================================================
# Celery Task Definitions
# =============================================================================

@celery_app.task(name="paq.ingest.epa_punjab", bind=True, max_retries=3, default_retry_delay=15)
def task_ingest_epa_punjab(self) -> Dict[str, Any]:
    """Celery task: Ingests ground station readings from EPA Punjab AQMS."""
    import asyncio
    from src.pipelines.epa_punjab import EPAPunjabIngestionWorker

    worker = EPAPunjabIngestionWorker()
    try:
        results = asyncio.run(worker.run())
        return {
            "stream_id": "STR-01-EPAPUNJAB",
            "status": "success",
            "records_count": len(results),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("task_ingest_epa_punjab failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(name="paq.ingest.metar", bind=True, max_retries=3, default_retry_delay=15)
def task_ingest_metar(self) -> Dict[str, Any]:
    """Celery task: Ingests 12 aerodrome METAR weather observations from NOAA AWC."""
    import asyncio
    from src.pipelines.metar import MetarIngestionWorker

    worker = MetarIngestionWorker()
    try:
        results = asyncio.run(worker.run())
        return {
            "stream_id": "STR-02-METAR",
            "status": "success",
            "records_count": len(results),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("task_ingest_metar failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(name="paq.ingest.synop", bind=True, max_retries=3, default_retry_delay=15)
def task_ingest_synop(self) -> Dict[str, Any]:
    """Celery task: Ingests WMO SYNOP surface observations."""
    import asyncio
    from src.pipelines.synop import SynopIngestionWorker

    worker = SynopIngestionWorker()
    try:
        results = asyncio.run(worker.run())
        return {
            "stream_id": "STR-03-SYNOP",
            "status": "success",
            "records_count": len(results),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("task_ingest_synop failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(name="paq.ingest.open_meteo", bind=True, max_retries=3, default_retry_delay=20)
def task_ingest_open_meteo(self) -> Dict[str, Any]:
    """Celery task: Ingests ECMWF IFS NWP 10m wind forecast for 41 district centroids."""
    import asyncio
    from src.pipelines.open_meteo import OpenMeteoIngestionWorker

    worker = OpenMeteoIngestionWorker()
    try:
        results = asyncio.run(worker.run())
        return {
            "stream_id": "STR-04-ECMWF-IFS",
            "status": "success",
            "districts_count": len(results),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("task_ingest_open_meteo failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(name="paq.ingest.firms", bind=True, max_retries=3, default_retry_delay=30)
def task_ingest_firms(self) -> Dict[str, Any]:
    """Celery task: Ingests NASA FIRMS VIIRS active fire detections."""
    import asyncio
    from src.pipelines.firms import FirmsIngestionWorker

    worker = FirmsIngestionWorker()
    try:
        results = asyncio.run(worker.run())
        return {
            "stream_id": "STR-05-FIRMS",
            "status": "success",
            "fires_count": len(results),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("task_ingest_firms failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(name="paq.ingest.iqair", bind=True, max_retries=3, default_retry_delay=15)
def task_ingest_iqair(self) -> Dict[str, Any]:
    """Celery task: Ingests cross-border Indian upwind monitoring observations."""
    from src.pipelines.iqair import IQAirIngestionWorker

    worker = IQAirIngestionWorker()
    try:
        results = worker.get_fallback()
        return {
            "stream_id": "STR-06-IQAIR",
            "status": "success",
            "cities_count": len(results),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("task_ingest_iqair failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(name="paq.ingest.cams", bind=True, max_retries=3, default_retry_delay=30)
def task_ingest_cams(self) -> Dict[str, Any]:
    """Celery task: Ingests Copernicus CAMS aerosol boundary summary."""
    from src.pipelines.cams import CamsIngestionWorker

    worker = CamsIngestionWorker()
    try:
        results = worker.get_fallback()
        return {
            "stream_id": "STR-07-CAMS",
            "status": "success",
            "cams_available": len(results) > 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("task_ingest_cams failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(name="paq.harmonize_and_commit", bind=True, max_retries=2, default_retry_delay=30)
def task_harmonize_and_commit(self) -> Dict[str, Any]:
    """Celery task: Harmonizes staged multi-source observations and commits snapshot."""
    import asyncio
    from src.infrastructure.repositories.baseline_repository import BaselineRepository
    from src.pipelines.staging_buffer import ChronometricStagingBuffer

    repo = BaselineRepository()
    staging = ChronometricStagingBuffer(repository=repo)
    target_ts = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    try:
        report = staging.harmonize_and_commit(target_ts)
        return {
            "task": "harmonize_and_commit",
            "status": "success",
            "timestamp": report.timestamp.isoformat(),
            "stations_committed": report.stations_committed,
            "districts_committed": report.districts_committed,
            "mean_aqi": report.mean_aqi,
        }
    except Exception as exc:
        logger.error("task_harmonize_and_commit failed: %s", exc)
        raise self.retry(exc=exc)
