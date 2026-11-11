"""Pydantic v2 schemas for geographic and station metadata."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DistrictMetaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str = Field(..., description="Unique district identifier")
    name: str = Field(..., description="Official district name")
    division: str = Field(default="", description="Administrative division")
    latitude: float = Field(..., description="Centroid latitude (WGS84)")
    longitude: float = Field(..., description="Centroid longitude (WGS84)")
    is_monitored: bool = Field(..., description="True if district has active ground AQMS")
    border_distance_km: float = Field(..., description="Distance from centroid to international border in km")
    india_inflow_sectors: List[int] = Field(default_factory=list, description="Wind compass sectors blowing from India (0-15)")
    stations: List[str] = Field(default_factory=list, description="List of station names in this district")
    boundary: Optional[Any] = Field(default=None, description="Boundary polygon coordinate array or GeoJSON geometry")


class StationMetaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str = Field(..., description="Unique station code or EPA ID")
    name: str = Field(..., description="Station display name")
    district: str = Field(..., description="District name")
    latitude: float = Field(..., description="Latitude (WGS84)")
    longitude: float = Field(..., description="Longitude (WGS84)")
    station_type: str = Field(default="fixed", description="fixed, mobile, airport_metar, wmo_synop")
    has_anemometer: bool = Field(default=False, description="True if site has functional anemometer")
    anemometer_blacklisted: bool = Field(default=False, description="True if vane is uncalibrated/blacklisted (e.g. Wazirabad)")
    altitude_m: Optional[float] = Field(default=None, description="Station elevation above sea level in meters")
    network_type: Optional[str] = Field(default=None, description="Network category (fixed, mobile, metar)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Supplementary sensor hardware metadata")
