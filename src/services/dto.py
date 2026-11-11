"""
Data Transfer Objects (DTOs) for Application Services Layer.
Pure dataclasses decoupling domain entities from HTTP presentation schemas.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# --- Observation Service DTOs ---

@dataclass(frozen=True)
class ProvincialSummaryDTO:
    timestamp: datetime
    mean_aqi: float
    exceedance_peqs_count: int
    peak_district: str
    peak_station: str
    peak_aqi: float
    reporting_districts_count: int = 0
    reporting_stations_count: int = 0
    total_districts: int = 41


@dataclass(frozen=True)
class DistrictReadingDTO:
    district_id: str
    name: str
    district: str = ""
    aqi: Optional[int] = None
    value: Optional[float] = None
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    no2: Optional[float] = None
    so2: Optional[float] = None
    co: Optional[float] = None
    o3: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    u: Optional[float] = None
    v: Optional[float] = None
    is_estimated: bool = False

    def __post_init__(self):
        if not self.district:
            object.__setattr__(self, "district", self.name)
        if self.value is None and self.aqi is not None:
            object.__setattr__(self, "value", float(self.aqi))


@dataclass(frozen=True)
class StationReadingDTO:
    station_id: str
    name: str
    district: str
    latitude: float
    longitude: float
    aqi: Optional[int] = None
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    no2: Optional[float] = None
    so2: Optional[float] = None
    co: Optional[float] = None
    o3: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    qc_flags: List[str] = field(default_factory=list)
    is_estimated: bool = False


@dataclass(frozen=True)
class AirportReadingDTO:
    icao: str
    name: str
    latitude: float
    longitude: float
    wind_speed_ms: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    u: Optional[float] = None
    v: Optional[float] = None


@dataclass(frozen=True)
class CurrentObservationsDTO:
    timestamp: str
    hour_index: int
    pollutant: str
    provincial_summary: ProvincialSummaryDTO
    districts: Dict[str, DistrictReadingDTO]
    stations: List[StationReadingDTO] = field(default_factory=list)
    airports: List[AirportReadingDTO] = field(default_factory=list)


@dataclass(frozen=True)
class DistrictSeriesDTO:
    district_id: str
    concentrations: List[Optional[float]]
    wind_u: List[Optional[float]] = field(default_factory=list)
    wind_v: List[Optional[float]] = field(default_factory=list)
    is_estimated: bool = False


@dataclass(frozen=True)
class HourlyTimeSeriesDTO:
    pollutant: str
    hours: List[str]
    total_hours: int
    districts: Dict[str, DistrictSeriesDTO]
    provincial_mean: Optional[List[Optional[float]]] = None


# --- Spatial Service DTOs ---

@dataclass(frozen=True)
class SurfaceFieldDTO:
    timestamp: str
    pollutant: str
    resolution: int
    grid_width: int
    grid_height: int
    min_val: float
    max_val: float
    grid_matrix: List[List[float]]
    opacity_matrix: Optional[List[List[int]]] = None


@dataclass(frozen=True)
class LabelPlacementDTO:
    district_id: str
    text: str
    anchor_x: float
    anchor_y: float
    placed_x: float
    placed_y: float
    offset_x: float
    offset_y: float
    has_leader_line: bool
    bounding_box: Tuple[float, float, float, float]


# --- Analytics Service DTOs ---

@dataclass(frozen=True)
class CPFSectorDTO:
    sector_index: int
    azimuth_deg: float
    direction_label: str = ""
    total_hours: int = 0
    exceedance_hours: int = 0
    cpf_probability: Optional[float] = None


@dataclass(frozen=True)
class CPFRoseResponseDTO:
    district: str
    pollutant: str
    threshold_p75: float
    calm_fraction: float
    null_hypothesis_baseline: float = 0.25
    sectors: List[CPFSectorDTO] = field(default_factory=list)


@dataclass(frozen=True)
class FluxLinkDTO:
    source_district: str
    receptor_district: str
    distance_km: float
    bearing_deg: float
    divergence_deg: float
    flux: float
    omega: float = 0.25
    score: float = 0.0


@dataclass(frozen=True)
class FluxResponseDTO:
    pollutant: str
    timestamp: Optional[str] = None
    total_links: int = 0
    top_pathways: List[FluxLinkDTO] = field(default_factory=list)
    links: List[FluxLinkDTO] = field(default_factory=list)
    net_balance: Dict[str, float] = field(default_factory=dict)
    net_balances: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if not self.top_pathways and self.links:
            object.__setattr__(self, "top_pathways", self.links)
        if not self.links and self.top_pathways:
            object.__setattr__(self, "links", self.top_pathways)
        if not self.net_balance and self.net_balances:
            object.__setattr__(self, "net_balance", self.net_balances)
        if not self.net_balances and self.net_balance:
            object.__setattr__(self, "net_balances", self.net_balance)


@dataclass(frozen=True)
class BorderDistrictTransboundaryDTO:
    district: str
    border_distance_km: float
    inflow_sectors: List[int]
    transboundary_flux: float
    direction_mode: str


@dataclass(frozen=True)
class BorderSampleNodeDTO:
    node_index: int
    latitude: float
    longitude: float
    normal_x: float
    normal_y: float
    normal_flux: float


@dataclass(frozen=True)
class TransboundaryResponseDTO:
    timestamp: str
    pollutant: str
    inflow_total: float
    outflow_total: float
    net_transboundary_flux: float
    net_flux: float
    status: str
    border_districts: Dict[str, BorderDistrictTransboundaryDTO] = field(default_factory=dict)
    border_samples: List[BorderSampleNodeDTO] = field(default_factory=list)
    district_values: Dict[str, float] = field(default_factory=dict)
    normal_fluxes: List[float] = field(default_factory=list)


# --- Ingestion Service DTOs ---

@dataclass(frozen=True)
class QuarantinedRowDTO:
    row_number: int
    station_id: Optional[str]
    error_type: str
    error_message: str
    raw_record: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IngestionReportDTO:
    status: str  # "success", "partial_quarantine", "failed"
    filename: str = ""
    total_rows: int = 0
    valid_rows: int = 0
    valid_count: int = 0
    quarantine_count: int = 0
    quarantined_rows: int = 0
    merged_observations_count: int = 0
    quarantined_records: List[QuarantinedRowDTO] = field(default_factory=list)
    quarantine_records: List[QuarantinedRowDTO] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    affected_stations: List[str] = field(default_factory=list)
    affected_districts: List[str] = field(default_factory=list)
    timestamps_ingested: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.valid_rows and self.valid_count:
            object.__setattr__(self, "valid_rows", self.valid_count)
        if not self.valid_count and self.valid_rows:
            object.__setattr__(self, "valid_count", self.valid_rows)
        if not self.quarantined_rows and self.quarantine_count:
            object.__setattr__(self, "quarantined_rows", self.quarantine_count)
        if not self.quarantine_count and self.quarantined_rows:
            object.__setattr__(self, "quarantine_count", self.quarantined_rows)
        if not self.quarantined_records and self.quarantine_records:
            object.__setattr__(self, "quarantined_records", self.quarantine_records)
        if not self.quarantine_records and self.quarantined_records:
            object.__setattr__(self, "quarantine_records", self.quarantined_records)
