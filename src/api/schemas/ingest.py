"""Pydantic v2 schemas for CSV ingestion reports."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class QuarantineDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    row_number: int = Field(...)
    station_id: Optional[str] = Field(None)
    error_type: str = Field(...)
    error_message: str = Field(...)
    raw_record: Dict[str, Any] = Field(default_factory=dict)


class CSVIngestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    status: str = Field(..., description="success, partial_quarantine, or failed")
    filename: str = Field(...)
    total_rows: int = Field(...)
    valid_rows: int = Field(...)
    quarantined_rows: int = Field(...)
    merged_observations_count: int = Field(default=0)
    errors: List[str] = Field(default_factory=list)
    quarantine_records: Optional[List[QuarantineDetail]] = Field(default=None)
    quarantined_records: Optional[List[QuarantineDetail]] = Field(default=None)
