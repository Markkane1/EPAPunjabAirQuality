"""
Comprehensive Unit Test Suite for Background Scheduler Standing Cron Daemons (APScheduler & Celery).
Validates:
1. APScheduler AsyncIOScheduler initialization and registration of all 7 streams.
2. Exact cron trigger expressions per DATA_PIPELINES_ARCHITECTURE.md §2.
3. Job execution tracking, run counts, error handling, and manual triggering.
4. Job pausing and resuming capabilities.
5. Celery application beat_schedule configuration and tasks.
6. PipelineOrchestrator lifecycle integration.
7. FastAPI REST API endpoints under /api/v1/ingest/scheduler/.
"""
import asyncio
from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import create_application
from src.infrastructure.repositories.baseline_repository import BaselineRepository
from src.pipelines.celery_app import celery_app
from src.pipelines.cron_scheduler import CRON_SCHEDULES, StandingCronScheduler
from src.pipelines.scheduler import PipelineOrchestrator
from src.services.analytics_service import AnalyticsService
from src.services.precomputation_service import PrecomputationService
from src.services.spatial_service import SpatialService


class TestStandingCronScheduler:
    """Tests the StandingCronScheduler APScheduler daemon."""

    def test_cron_schedules_specification(self):
        """Verifies all 7 streams + harmonization have standard cron specifications."""
        expected_keys = [
            "epa_punjab",
            "metar",
            "synop",
            "open_meteo",
            "firms",
            "iqair",
            "cams",
            "harmonize",
        ]
        for key in expected_keys:
            assert key in CRON_SCHEDULES
            conf = CRON_SCHEDULES[key]
            assert "job_id" in conf
            assert "stream_id" in conf
            assert "trigger" in conf
            assert "cron_expression" in conf

        # Verify exact crons per DATA_PIPELINES_ARCHITECTURE.md §2
        assert CRON_SCHEDULES["epa_punjab"]["cron_expression"] == "5,15 * * * *"
        assert CRON_SCHEDULES["metar"]["cron_expression"] == "10 * * * *"
        assert CRON_SCHEDULES["synop"]["cron_expression"] == "15 * * * *"
        assert CRON_SCHEDULES["open_meteo"]["cron_expression"] == "0 * * * *"
        assert CRON_SCHEDULES["firms"]["cron_expression"] == "0 3,15 * * *"
        assert CRON_SCHEDULES["iqair"]["cron_expression"] == "20 * * * *"
        assert CRON_SCHEDULES["cams"]["cron_expression"] == "0 4 * * *"
        assert CRON_SCHEDULES["harmonize"]["cron_expression"] == "25 * * * *"

    @pytest.mark.anyio
    async def test_scheduler_lifecycle_and_live_registration(self):
        """Tests daemon start, live cron job registration, and graceful shutdown."""
        repo = BaselineRepository()
        spatial_svc = SpatialService(repo=repo)
        analytics_svc = AnalyticsService(repo=repo)
        precomp_svc = PrecomputationService(repo, spatial_svc, analytics_svc)
        orchestrator = PipelineOrchestrator(
            repository=repo,
            precomputation_service=precomp_svc,
            mode="live",
        )

        cron = orchestrator.cron_scheduler
        assert not cron.is_running

        # Start scheduler
        cron.start()
        assert cron.is_running

        # Register live jobs
        cron.register_live_cron_jobs()
        status = cron.get_scheduler_status()
        assert status["is_running"] is True
        assert status["total_registered_jobs"] >= 8

        jobs = cron.get_jobs_status()
        assert len(jobs) >= 8
        job_ids = [j["job_id"] for j in jobs]
        assert "cron_ingest_epa_punjab" in job_ids
        assert "cron_ingest_metar" in job_ids
        assert "cron_ingest_synop" in job_ids
        assert "cron_ingest_open_meteo" in job_ids
        assert "cron_ingest_firms" in job_ids
        assert "cron_ingest_iqair" in job_ids
        assert "cron_ingest_cams" in job_ids
        assert "cron_harmonize_hourly_commit" in job_ids

        # Next fire time should be computed for all active jobs
        for j in jobs:
            if j["job_id"] in job_ids:
                assert j["is_registered"] is True
                assert j["next_run_time"] is not None

        # Shutdown
        cron.shutdown(wait=False)
        assert not cron.is_running

    @pytest.mark.anyio
    async def test_job_pause_resume_and_manual_trigger(self):
        """Tests pausing, resuming, and manually triggering a cron job."""
        repo = BaselineRepository()
        orchestrator = PipelineOrchestrator(repository=repo, mode="live")
        cron = orchestrator.cron_scheduler
        cron.start()
        cron.register_live_cron_jobs()

        # 1. Pause job
        assert cron.pause_job("cron_ingest_metar") is True
        metar_job = next(j for j in cron.get_jobs_status() if j["job_id"] == "cron_ingest_metar")
        assert metar_job["is_paused"] is True

        # 2. Resume job
        assert cron.resume_job("cron_ingest_metar") is True
        metar_job = next(j for j in cron.get_jobs_status() if j["job_id"] == "cron_ingest_metar")
        assert metar_job["is_paused"] is False

        # 3. Manual trigger
        res = await cron.trigger_job("cron_ingest_metar")
        assert res["status"] == "success"
        assert res["job_id"] == "cron_ingest_metar"
        assert res["duration_ms"] >= 0

        # Stats should reflect the execution
        metar_job = next(j for j in cron.get_jobs_status() if j["job_id"] == "cron_ingest_metar")
        assert metar_job["run_count"] == 1
        assert metar_job["success_count"] == 1
        assert metar_job["last_run"] is not None

        cron.shutdown(wait=False)


class TestCeleryAppConfiguration:
    """Tests the Celery distributed application and beat_schedule."""

    def test_celery_beat_schedule_contract(self):
        """Verifies Celery beat_schedule matches the architecture specifications."""
        beat = celery_app.conf.beat_schedule
        assert len(beat) == 8

        assert "ingest-epa-punjab-cron" in beat
        assert "ingest-metar-cron" in beat
        assert "ingest-synop-cron" in beat
        assert "ingest-open-meteo-cron" in beat
        assert "ingest-firms-cron" in beat
        assert "ingest-iqair-cron" in beat
        assert "ingest-cams-cron" in beat
        assert "harmonize-and-commit-hourly" in beat

        # Check soft timeout to prevent starvation
        assert celery_app.conf.task_soft_time_limit == 120
        assert celery_app.conf.task_time_limit == 180

    def test_celery_tasks_registered(self):
        """Verifies all celery ingestion tasks exist in registry."""
        registered_tasks = celery_app.tasks
        assert "paq.ingest.epa_punjab" in registered_tasks
        assert "paq.ingest.metar" in registered_tasks
        assert "paq.ingest.synop" in registered_tasks
        assert "paq.ingest.open_meteo" in registered_tasks
        assert "paq.ingest.firms" in registered_tasks
        assert "paq.ingest.iqair" in registered_tasks
        assert "paq.ingest.cams" in registered_tasks
        assert "paq.harmonize_and_commit" in registered_tasks


class TestSchedulerApiEndpoints:
    """Tests the FastAPI REST API endpoints for scheduler monitoring and management."""

    @pytest.mark.anyio
    async def test_api_scheduler_endpoints(self):
        app = create_application()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. GET /api/v1/ingest/scheduler/status
            resp = await client.get("/api/v1/ingest/scheduler/status")
            assert resp.status_code == 200
            data = resp.json()
            assert "cron_scheduler" in data
            assert data["cron_scheduler"]["engine"] == "APScheduler.AsyncIOScheduler"
            assert "scheduled_cron_jobs" in data

            # 2. GET /api/v1/ingest/scheduler/jobs
            resp = await client.get("/api/v1/ingest/scheduler/jobs")
            assert resp.status_code == 200
            jobs = resp.json()
            assert isinstance(jobs, list)
            assert len(jobs) >= 8

            # 3. POST /api/v1/ingest/scheduler/jobs/{id}/pause
            resp = await client.post("/api/v1/ingest/scheduler/jobs/cron_ingest_synop/pause")
            assert resp.status_code == 200
            assert resp.json()["status"] == "paused"

            # 4. POST /api/v1/ingest/scheduler/jobs/{id}/resume
            resp = await client.post("/api/v1/ingest/scheduler/jobs/cron_ingest_synop/resume")
            assert resp.status_code == 200
            assert resp.json()["status"] == "resumed"

            # 5. POST /api/v1/ingest/scheduler/jobs/{id}/trigger
            resp = await client.post("/api/v1/ingest/scheduler/jobs/cron_ingest_synop/trigger")
            assert resp.status_code == 200
            res_data = resp.json()
            assert res_data["status"] == "success"
            assert res_data["job_id"] == "cron_ingest_synop"
