"""
Pydantic v2 schemas for EPA Punjab Live AQMS API routes (/api/v1/epa/*).
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EPAStationMeta(BaseModel):
    api_id: str
    display_name: str
    city: str
    district: str
    latitude: float
    longitude: float
    station_type: str


class EPALatestObservation(BaseModel):
    station_id: str
    station_name: str
    district: str
    city: str
    latitude: float
    longitude: float
    station_type: str
    observed_at_pkt: str
    observed_at_utc: datetime
    is_stale: bool
    stale_hours: float
    aqi: Optional[float] = None
    aqi_category: Optional[str] = None
    dominant_pollutant: Optional[str] = None
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    o3: Optional[float] = None
    no2: Optional[float] = None
    so2: Optional[float] = None
    co: Optional[float] = None
    no: Optional[float] = None
    nox: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    temp_c: Optional[float] = None
    relative_humidity: Optional[float] = None
    barometric_pressure_hpa: Optional[float] = None
    rain_mm: Optional[float] = None
    solar_radiation: Optional[float] = None
    qc_flags: List[str] = Field(default_factory=list)


class EPALatestResponse(BaseModel):
    status: str
    source: str
    upstream_url: str
    timestamp_fetched_utc: datetime
    total_stations: int
    active_reporting_stations: int
    stale_reporting_stations: int
    stations: List[EPALatestObservation]


class EPAAlertItem(BaseModel):
    code: Optional[str] = None
    alert: str
    date_time: str
    timestamp_utc: Optional[datetime] = None


class EPAAlertsResponse(BaseModel):
    status: str
    count: int
    alerts: List[EPAAlertItem]


class EPAHealthStatus(BaseModel):
    status: str
    upstream_url: str
    latency_ms: float
    circuit_breaker_open: bool
    is_healthy: bool
    last_checked: datetime
