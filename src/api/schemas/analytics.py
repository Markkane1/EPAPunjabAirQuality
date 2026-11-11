"""Pydantic v2 schemas for CPF wind roses, advection transport flux, and transboundary balance."""
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CPFSectorDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    sector_index: int = Field(..., ge=0, le=15, description="Compass sector index 0-15")
    azimuth_deg: float = Field(..., description="Central sector azimuth (0.0 to 337.5 deg)")
    direction_label: str = Field(..., description="Compass label (N, NNE, NE, ...)")
    total_hours: int = Field(..., description="Total non-calm hours recorded in this sector (Nk)")
    exceedance_hours: int = Field(..., description="Hours exceeding P75 threshold in this sector (mk)")
    cpf_probability: Optional[float] = Field(
        None, description="Conditional probability (mk / Nk), or None if Nk < 6 (suppressed)"
    )


class CPFRoseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    district: str = Field(...)
    pollutant: str = Field(...)
    threshold_p75: float = Field(..., description="Pooled 75th percentile exceedance threshold")
    calm_fraction: float = Field(..., description="Fraction of hours where wind speed < 0.5 m/s")
    null_hypothesis_baseline: float = Field(default=0.25, description="Isotropic baseline probability")
    sectors: List[CPFSectorDetail] = Field(...)


class AdvectionPathwayLink(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    source_district: str = Field(...)
    receptor_district: str = Field(...)
    distance_km: float = Field(..., description="Geodesic distance between centroids in km")
    bearing_deg: float = Field(..., description="Bearing from source to receptor")
    divergence_deg: float = Field(..., description="Angular deviation from advective wind vector")
    flux: float = Field(..., description="Physical advective mass flux")
    omega: float = Field(default=0.25, description="Receptor CPF feedback coupling coefficient")
    score: float = Field(default=0.0, description="Ranked transport score (flux * omega)")


class FluxTransportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    pollutant: str = Field(...)
    timestamp: Optional[str] = Field(None)
    total_links: int = Field(default=0)
    top_pathways: List[AdvectionPathwayLink] = Field(default_factory=list, description="Top ranked transport corridors")
    links: Optional[List[AdvectionPathwayLink]] = Field(default=None)
    net_balance: Dict[str, float] = Field(default_factory=dict, description="Net transport flux per district")


class BorderDistrictTransboundaryDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    district: str = Field(...)
    border_distance_km: float = Field(...)
    inflow_sectors: List[int] = Field(default_factory=list)
    transboundary_flux: float = Field(...)
    direction_mode: str = Field(..., description="inflow, outflow, neutral, or calm")


class BorderSampleNode(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    node_index: int = Field(...)
    latitude: float = Field(...)
    longitude: float = Field(...)
    normal_x: float = Field(..., description="Inward normal vector X component")
    normal_y: float = Field(..., description="Inward normal vector Y component")
    normal_flux: float = Field(..., description="Normal flux (+inflow, -outflow)")


class TransboundaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    timestamp: str = Field(...)
    pollutant: str = Field(...)
    inflow_total: float = Field(...)
    outflow_total: float = Field(...)
    net_transboundary_flux: float = Field(...)
    net_flux: Optional[float] = None
    status: str = Field(..., description="net_inflow, net_outflow, or neutral")
    border_districts: Dict[str, BorderDistrictTransboundaryDetail] = Field(default_factory=dict)
    border_samples: List[BorderSampleNode] = Field(default_factory=list)
