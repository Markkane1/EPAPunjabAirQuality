"""
Punjab Air Quality Ingestion Pipelines & Fallback Services.
"""
from src.pipelines.base import BaseIngestionWorker
from src.pipelines.fallback_engine import FallbackTemplateEngine
from src.pipelines.epa_punjab import EPAPunjabIngestionWorker
from src.pipelines.metar import MetarIngestionWorker
from src.pipelines.synop import SynopIngestionWorker
from src.pipelines.open_meteo import OpenMeteoIngestionWorker
from src.pipelines.firms import FirmsIngestionWorker
from src.pipelines.iqair import IQAirIngestionWorker
from src.pipelines.cams import CamsIngestionWorker
from src.pipelines.cron_scheduler import StandingCronScheduler, CRON_SCHEDULES
from src.pipelines.celery_app import celery_app
from src.pipelines.scheduler import PipelineOrchestrator

__all__ = [
    "BaseIngestionWorker",
    "FallbackTemplateEngine",
    "EPAPunjabIngestionWorker",
    "MetarIngestionWorker",
    "SynopIngestionWorker",
    "OpenMeteoIngestionWorker",
    "FirmsIngestionWorker",
    "IQAirIngestionWorker",
    "CamsIngestionWorker",
    "StandingCronScheduler",
    "CRON_SCHEDULES",
    "celery_app",
    "PipelineOrchestrator",
]
