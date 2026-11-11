"""Pydantic v2 schemas for current and hourly air quality observations."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ProvincialSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    mean_aqi: float = Field(..., description="Provincial arithmetic mean AQI across reporting districts")
    exceedance_peqs_count: int = Field(..., description="Number of districts exceeding PEQS statutory ceiling")
    peak_district: str = Field(..., description="District exhibiting highest AQI")
    peak_aqi: float = Field(..., description="Maximum AQI value recorded in peak district")
    reporting_stations_count: int = Field(default=0, description="Count of stations reporting valid observations")
    reporting_districts_count: int = Field(default=0, description="Count of districts reporting valid observations")
    total_districts: int = Field(default=41, description="Total districts count")


class DistrictReadingSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    district: str = Field(...)
    district_id: Optional[str] = None
    name: Optional[str] = None
    aqi: Optional[int] = Field(None, description="Composite PEPC AQI")
    value: Optional[float] = Field(None, description="Target pollutant concentration or AQI")
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    no2: Optional[float] = None
    so2: Optional[float] = None
    co: Optional[float] = None
    o3: Optional[float] = None
    u: Optional[float] = Field(None, description="Zonal wind vector in m/s")
    v: Optional[float] = Field(None, description="Meridional wind vector in m/s")
    wind_speed: Optional[float] = Field(None, description="Wind speed in m/s")
    wind_direction: Optional[float] = Field(None, description="Wind azimuth in degrees")
    is_estimated: bool = Field(default=False, description="True if imputed via spatial IDW")


class AirportReadingSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    icao: str = Field(..., description="4-letter ICAO code (e.g. OPLA)")
    name: str = Field(..., description="Aerodrome name")
    latitude: float = Field(...)
    longitude: float = Field(...)
    wind_speed_ms: Optional[float] = Field(None)
    wind_direction_deg: Optional[float] = Field(None)
    u: Optional[float] = None
    v: Optional[float] = None


class CurrentObservationsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    timestamp: str = Field(..., description="ISO-8601 UTC timestamp of observation snapshot")
    hour_index: int = Field(..., description="Historical hour index (0 to 215, or latest)")
    pollutant: str = Field(default="AQI")
    provincial_summary: ProvincialSummarySchema
    districts: Dict[str, DistrictReadingSchema]
    airports: List[AirportReadingSchema] = Field(default_factory=list)


class DistrictHourlySeriesSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    concentrations: List[Optional[float]] = Field(..., description="Hourly concentration or AQI values")
    wind_u: List[Optional[float]] = Field(default_factory=list, description="Hourly U-wind components")
    wind_v: List[Optional[float]] = Field(default_factory=list, description="Hourly V-wind components")
    is_estimated: bool = Field(default=False)


class HourlyObservationsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    pollutant: str = Field(...)
    hours: List[str] = Field(..., description="Array of ISO-8601 hourly timestamps")
    total_hours: int = Field(...)
    districts: Dict[str, DistrictHourlySeriesSchema] = Field(...)
    provincial_mean: Optional[List[Optional[float]]] = Field(default=None)
