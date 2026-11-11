"""
Pydantic v2 schema for validating user-supplied CSV observation rows.
Adheres to DATA_PIPELINES_ARCHITECTURE.md §2 and PROJECT.md §Interface Contracts.
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class UserCSVRow(BaseModel):
    """
    Validation schema for individual rows from custom user CSV datasets.
    Enforces geographic bounds (lat [27.0, 35.0], lon [69.0, 76.0]), physical value caps (0.0 - 5000.0),
    and recognized pollutants.
    """
    timestamp: str = Field(..., description="Observation timestamp (ISO-8601 or YYYY-MM-DD HH:MM)")
    station_id: str = Field(..., min_length=1, description="Unique station identifier")
    station_name: str = Field(..., min_length=1, description="Station display name")
    district: str = Field(..., min_length=1, description="District in Punjab")
    latitude: float = Field(..., ge=27.0, le=35.0, description="WGS84 Latitude within Punjab bounds [27.0, 35.0]")
    longitude: float = Field(..., ge=69.0, le=76.0, description="WGS84 Longitude within Punjab bounds [69.0, 76.0]")
    pollutant: str = Field(..., description="Pollutant name (aqi, pm25, pm10, no2, so2, co, o3, no, nox)")
    value: float = Field(..., ge=0.0, le=5000.0, description="Pollutant concentration or index within [0.0, 5000.0]")
    wind_speed: Optional[float] = Field(None, ge=0.0, le=30.0, description="Surface wind speed in m/s [0.0, 30.0]")
    wind_direction: Optional[float] = Field(None, ge=0.0, le=360.0, description="Wind azimuth in degrees [0.0, 360.0]")
    pollutant_flags: Optional[str] = Field(None, description="Optional diagnostic or QC flags")

    @field_validator("pollutant")
    @classmethod
    def validate_pollutant_name(cls, v: str) -> str:
        """
        Normalize and validate pollutant identifier against the 9 recognized pollutants.
        Permits variations like 'PM2.5', 'pm-2.5', 'pm25', 'AQI', 'O3', etc.
        """
        valid_pollutants = {
            "aqi", "pm25", "pm10", "no2", "so2", "co", "o3", "no", "nox"
        }
        clean = v.strip().lower().replace(".", "").replace("-", "").replace("_", "")
        if clean not in valid_pollutants:
            raise ValueError(
                f"Invalid pollutant: '{v}'. Must be one of: {sorted(list(valid_pollutants))}"
            )
        return clean
