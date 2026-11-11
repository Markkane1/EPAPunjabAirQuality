"""
Pydantic v2 domain schemas for raw station measurements and normalized observations.
Adheres to DATA_PIPELINES_ARCHITECTURE.md §4 and ARCHITECTURE_OVERVIEW.md §3.1.
"""
import math
from datetime import datetime, timezone, timedelta
from typing import Any, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator

# Define PKT (Pakistan Standard Time is UTC+5)
PKT = timezone(timedelta(hours=5))
UTC = timezone.utc


class RawStationMeasurement(BaseModel):
    """
    Pydantic v2 data contract for raw telemetry readings from AQMS stations.
    Enforces upper bounds (le=5000.0) while tagging extreme exceedances (>1000 PM2.5, >1500 PM10).
    """
    station_id: Union[int, str] = Field(..., description="EPA Punjab internal portal ID or station code")
    station_name: str = Field(..., min_length=2, max_length=100)
    district: str = Field(..., min_length=2, max_length=50)
    timestamp: datetime = Field(..., description="Observation timestamp UTC")
    aqi: Optional[float] = Field(None, ge=0.0, le=2000.0, description="Composite AQI; operational cap 500 when PM2.5 > 350")
    pm25: Optional[float] = Field(None, ge=0.0, le=5000.0, description="Fine particulate matter (<= 2.5 um); >1000 tagged QC_EXCEEDANCE_EXTREME")
    pm10: Optional[float] = Field(None, ge=0.0, le=5000.0, description="Coarse particulate matter (<= 10 um); >1500 tagged QC_EXCEEDANCE_EXTREME")
    no2: Optional[float] = Field(None, ge=0.0, le=500.0)
    so2: Optional[float] = Field(None, ge=0.0, le=500.0)
    co: Optional[float] = Field(None, ge=0.0, le=50.0)
    o3: Optional[float] = Field(None, ge=0.0, le=400.0)
    no: Optional[float] = Field(None, ge=0.0, le=5000.0)
    nox: Optional[float] = Field(None, ge=0.0, le=5000.0)
    wind_speed: Optional[float] = Field(None, ge=0.0, le=30.0)
    wind_direction: Optional[float] = Field(None, ge=0.0, le=360.0)
    pollutant_flags: Optional[Any] = Field(None, description="Diagnostic sensor flags (str, list, dict)")
    qc_flags: List[str] = Field(default_factory=list)
    is_estimated: bool = Field(default=False, description="Flag indicating fallback or imputed estimation")

    @field_validator("timestamp", mode="after")
    def ensure_utc(cls, v: datetime) -> datetime:
        """Ensure naive datetimes are interpreted as PKT and converted to UTC."""
        if v.tzinfo is None:
            v = v.replace(tzinfo=PKT)
        return v.astimezone(UTC)

    @field_validator("pm25", "pm10", "no2", "so2", "co", "o3", "no", "nox", mode="before")
    @classmethod
    def zero_and_negative_to_none(cls, v: Any) -> Optional[float]:
        """Step 0 QC: convert zero, negative, or invalid sensor readings to None."""
        if v is None:
            return None
        try:
            val = float(v)
            if math.isnan(val) or val <= 0.0 or math.isinf(val):
                return None
            return val
        except (ValueError, TypeError):
            return None

    @field_validator("wind_speed", mode="before")
    @classmethod
    def sanitize_wind_speed(cls, v: Any) -> Optional[float]:
        """Sanitize wind speed within physical bounds [0.0, 30.0] m/s."""
        if v is None:
            return None
        try:
            val = float(v)
            if math.isnan(val) or math.isinf(val) or val < 0.0 or val > 30.0:
                return None
            return val
        except (ValueError, TypeError):
            return None

    @field_validator("wind_direction", mode="before")
    @classmethod
    def sanitize_wind_direction(cls, v: Any) -> Optional[float]:
        """Sanitize wind direction within physical bounds [0.0, 360.0] deg."""
        if v is None:
            return None
        try:
            val = float(v)
            if math.isnan(val) or math.isinf(val) or val < 0.0 or val > 360.0:
                return None
            return val
        except (ValueError, TypeError):
            return None

    @model_validator(mode="after")
    def tag_extreme_exceedances(self) -> "RawStationMeasurement":
        """
        Preserve extreme crisis smog peaks while appending QC_EXCEEDANCE_EXTREME tag:
        - PM2.5 > 1000.0 ug/m3
        - PM10 > 1500.0 ug/m3
        """
        if self.pm25 is not None and self.pm25 > 1000.0:
            if "QC_EXCEEDANCE_EXTREME" not in self.qc_flags:
                self.qc_flags.append("QC_EXCEEDANCE_EXTREME")
        if self.pm10 is not None and self.pm10 > 1500.0:
            if "QC_EXCEEDANCE_EXTREME" not in self.qc_flags:
                self.qc_flags.append("QC_EXCEEDANCE_EXTREME")
        return self


class NormalizedObservation(BaseModel):
    """
    Cleaned, QC-validated, and georeferenced domain observation model.
    """
    timestamp: datetime = Field(..., description="Observation timestamp UTC")
    station_id: str = Field(..., description="Canonical station identifier")
    station_name: str = Field(..., description="Canonical station display name")
    district: str = Field(..., description="Administrative district in Punjab")
    latitude: float = Field(..., ge=27.0, le=35.0, description="WGS84 latitude")
    longitude: float = Field(..., ge=69.0, le=76.0, description="WGS84 longitude")
    pm25_qc: Optional[float] = None
    pm10_qc: Optional[float] = None
    no2_qc: Optional[float] = None
    so2_qc: Optional[float] = None
    co_qc: Optional[float] = None
    o3_qc: Optional[float] = None
    no_qc: Optional[float] = None
    nox_qc: Optional[float] = None
    pepc_aqi: Optional[int] = None
    wind_speed_ms: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    u_vector_ms: Optional[float] = None
    v_vector_ms: Optional[float] = None
    meteorology_source: str = Field(default="aqms", description="aqms, metar, ecmwf, idw, baseline, user_csv")
    qc_flags: List[str] = Field(default_factory=list)
    is_estimated: bool = Field(default=False)

    @field_validator("timestamp", mode="after")
    def ensure_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            v = v.replace(tzinfo=PKT)
        return v.astimezone(UTC)
