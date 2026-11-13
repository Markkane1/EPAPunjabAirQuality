"""API Route Module: Custom User CSV Ingestion & Background Scheduler (/api/v1/ingest)."""
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from src.api.dependencies import get_ingestion_service
from src.api.schemas.ingest import CSVIngestResponse
from src.services.ingestion_service import IngestionService

router = APIRouter(prefix="/api/v1/ingest", tags=["Ingestion"])


# =============================================================================
# Standing Background Cron Scheduler Daemon Endpoints
# =============================================================================

@router.get(
    "/scheduler/status",
    summary="Get background cron scheduler daemon status and operational telemetry",
)
async def get_scheduler_status(request: Request) -> Dict[str, Any]:
    """Returns standing cron daemon status, APScheduler engine health, and active execution metrics."""
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if not orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pipeline orchestrator is not initialized.",
        )
    return orchestrator.get_status()


@router.get(
    "/scheduler/jobs",
    summary="List all registered standing cron jobs and next run times",
)
async def list_scheduler_jobs(request: Request) -> List[Dict[str, Any]]:
    """Returns details, cron expressions, next fire times, and execution counts for all pipeline jobs."""
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if not orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pipeline orchestrator is not initialized.",
        )
    return orchestrator.get_cron_jobs()


@router.post(
    "/scheduler/jobs/{job_id}/trigger",
    summary="Manually trigger immediate execution of a scheduled cron job",
)
async def trigger_scheduler_job(job_id: str, request: Request) -> Dict[str, Any]:
    """Dispatches an immediate manual execution of a registered ingestion or harmonization job."""
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if not orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pipeline orchestrator is not initialized.",
        )
    try:
        return await orchestrator.trigger_cron_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute job '{job_id}': {str(e)}",
        )


@router.post(
    "/scheduler/jobs/{job_id}/pause",
    summary="Pause a scheduled cron job",
)
async def pause_scheduler_job(job_id: str, request: Request) -> Dict[str, Any]:
    """Pauses future cron triggers for the specified job ID."""
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if not orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pipeline orchestrator is not initialized.",
        )
    success = orchestrator.pause_cron_job(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found or could not be paused.",
        )
    return {"status": "paused", "job_id": job_id}


@router.post(
    "/scheduler/jobs/{job_id}/resume",
    summary="Resume a paused cron job",
)
async def resume_scheduler_job(job_id: str, request: Request) -> Dict[str, Any]:
    """Resumes cron triggers for a previously paused job ID."""
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if not orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pipeline orchestrator is not initialized.",
        )
    success = orchestrator.resume_cron_job(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found or could not be resumed.",
        )
    return {"status": "resumed", "job_id": job_id}


# =============================================================================
# Custom User CSV Ingestion
# =============================================================================


@router.post(
    "/csv",
    response_model=CSVIngestResponse,
    summary="Upload and validate custom air quality CSV dataset",
)
async def upload_csv_dataset(
    file: UploadFile = File(..., description="Multipart CSV dataset file"),
    allow_missing_coords: bool = Form(False, description="Allow stations to resolve coordinates via canonical catalog"),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
) -> CSVIngestResponse:
    """
    Accepts user-supplied CSV files, validates required headers, executes row-level quarantine,
    applies GPS coordinate corrections, performs QC filtering, and registers valid observations.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only standard comma-separated values (.csv) files are supported.",
        )

    try:
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded CSV file is empty.",
            )

        report = ingestion_service.process_csv_upload(
            file_bytes=content,
            filename=file.filename,
            allow_missing_coords=allow_missing_coords,
        )

        return CSVIngestResponse.model_validate(report)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the CSV dataset: {str(e)}",
        )
