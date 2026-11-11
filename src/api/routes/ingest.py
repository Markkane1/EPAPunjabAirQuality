"""API Route Module: Custom User CSV Ingestion (/api/v1/ingest)."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from src.api.dependencies import get_ingestion_service
from src.api.schemas.ingest import CSVIngestResponse
from src.services.ingestion_service import IngestionService

router = APIRouter(prefix="/api/v1/ingest", tags=["Ingestion"])


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
