"""
Domain entities and value objects for Punjab Air Quality system.
Clean architecture: pure Python dataclasses with zero framework dependencies.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Station:
    """Air Quality Monitoring Station (AQMS), Airport METAR, or WMO SYNOP node."""
    id: str
    name: str
    district: str
    latitude: float
    longitude: float
    station_type: str = "fixed"  # 'fixed', 'mobile', 'airport_metar', 'wmo_synop'
    has_anemometer: bool = False
    anemometer_blacklisted: bool = False
    altitude_m: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class District:
    """Administrative District in Punjab province."""
    id: str
    name: str
    division: str
    latitude: float
    longitude: float
    is_monitored: bool = False
    border_distance_km: float = 999.0
    india_inflow_sectors: Tuple[int, ...] = field(default_factory=tuple)


@dataclass
class StationObservation:
    """Hourly observation measurement from a station."""
    station_id: str
    recorded_at: datetime
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    no2: Optional[float] = None
    so2: Optional[float] = None
    co: Optional[float] = None
    o3: Optional[float] = None
    no: Optional[float] = None
    nox: Optional[float] = None
    aqi: Optional[int] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    u: Optional[float] = None
    v: Optional[float] = None
    temperature_c: Optional[float] = None
    relative_humidity_pct: Optional[float] = None
    qc_flags: int = 0


@dataclass
class DistrictObservation:
    """Hourly aggregated or imputed observation for a district."""
    district_id: str
    recorded_at: datetime
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    no2: Optional[float] = None
    so2: Optional[float] = None
    co: Optional[float] = None
    o3: Optional[float] = None
    aqi: Optional[int] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    u: Optional[float] = None
    v: Optional[float] = None
    is_estimated: bool = False


@dataclass(frozen=True)
class CPFRoseResult:
    """16-sector Conditional Probability Function polar rose result."""
    district_id: str
    pollutant: str
    threshold: float
    calm_ratio: float
    sectors: Tuple[Optional[float], ...]
    sector_counts: Tuple[int, ...] = field(default_factory=tuple)
    sector_exceedances: Tuple[int, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AdvectionFluxLink:
    """Physical mass transport link between source and receptor districts."""
    source_district: str
    receptor_district: str
    distance_km: float
    bearing_deg: float
    divergence_deg: float
    flux: float
    omega: float = 0.25
    score: float = 0.0


@dataclass(frozen=True)
class TransboundaryResult:
    """Cross-border transboundary atmospheric transport assessment."""
    timestamp: datetime
    inflow_total: float
    outflow_total: float
    net_flux: float
    district_values: Dict[str, float] = field(default_factory=dict)
    normal_fluxes: List[float] = field(default_factory=list)


@dataclass(frozen=True)
class SurfaceGridPoint:
    """Interpolated 2D continuous surface grid point."""
    x: float
    y: float
    value: float
    nearest_station_km: float
    alpha: int  # [95, 235]


@dataclass(frozen=True)
class LabelPlacement:
    """Collision-free district label coordinates and leader line status."""
    district_id: str
    text: str
    anchor_x: float
    anchor_y: float
    offset_x: float
    offset_y: float
    width: float
    height: float
    has_leader_line: bool
