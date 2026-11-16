"""
Pydantic v2 domain schemas for Planetary Boundary Layer (PBL) mixing height observations.
Stream 8 (STR-08-PBL) and Transformation 11 (Atmospheric Ventilation Index).
"""
from datetime import datetime, timezone
from typing import Any, List, Optional
from pydantic import BaseModel, Field, field_validator


class PBLObservation(BaseModel):
    """
    Pydantic v2 contract for planetary boundary layer mixing height and ventilation index.
    """
    district: str = Field(..., min_length=2, max_length=50, description="Punjab administrative district name")
    timestamp: datetime = Field(..., description="Observation or forecast timestamp (UTC)")
    boundary_layer_height: float = Field(..., ge=0.0, le=10000.0, description="PBL mixing height in meters")
    surface_wind_speed: Optional[float] = Field(None, ge=0.0, le=50.0, description="Surface 10m wind speed in m/s")
    ventilation_index: Optional[float] = Field(None, ge=0.0, description="Ventilation index h_PBL * w_sfc (m^2/s)")
    dispersion_category: Optional[str] = Field(None, description="Statutory dispersion risk band")
    is_estimated: bool = Field(default=False, description="Flag indicating fallback or imputed estimation")
    source: str = Field(default="ecmwf_open_meteo", description="Data provider or model source")

    @field_validator("timestamp", mode="after")
    def ensure_utc(cls, v: datetime) -> datetime:
        """Ensure naive datetimes are treated as UTC."""
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)


class DistrictPBLSummary(BaseModel):
    """
    District-level summary of boundary layer height and dispersion risk.
    """
    district: str
    latest_pbl_height_m: float
    surface_wind_speed_ms: float
    ventilation_index: float
    dispersion_category: str
    dispersion_color: str
    is_critical_trap: bool
