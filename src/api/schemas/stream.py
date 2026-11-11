"""Pydantic v2 schemas for SSE streaming payloads."""
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


class SSEHourlyUpdatePayload(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    event: str = Field(default="hourly_update")
    timestamp: str = Field(...)
    hour_index: int = Field(...)
    total_hours: int = Field(...)
    provincial_summary: Dict[str, Any] = Field(...)
    district_readings: Dict[str, Any] = Field(...)
    airports: List[Dict[str, Any]] = Field(default_factory=list)
