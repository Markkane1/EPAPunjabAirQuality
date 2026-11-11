"""API Route Module: Deep-Dive Analytics (/api/v1/analytics)."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import get_analytics_service
from src.api.schemas.analytics import CPFRoseResponse, FluxTransportResponse, TransboundaryResponse
from src.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get(
    "/cpf",
    response_model=CPFRoseResponse,
    summary="16-Sector Conditional Probability Function (CPF) Wind Rose",
)
async def get_cpf_rose(
    district: Optional[str] = Query(None, description="District name (e.g. Lahore, Faisalabad)"),
    district_name: Optional[str] = Query(None, description="District name alias"),
    pollutant: str = Query("PM2.5", description="Pollutant to analyze"),
    threshold: Optional[float] = Query(None, description="Optional custom exceedance threshold; defaults to P75"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> CPFRoseResponse:
    """Evaluates 16 compass sectors for localized directional emission source apportionment."""
    target_district = district or district_name
    if not target_district:
        raise HTTPException(status_code=422, detail="Field 'district' is required")
    try:
        dto = analytics_service.calculate_cpf(
            district_name=target_district,
            pollutant=pollutant,
            custom_threshold=threshold,
        )
        return CPFRoseResponse.model_validate(dto)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CPF analysis failed: {str(e)}")


@router.get(
    "/flux",
    response_model=FluxTransportResponse,
    summary="Inter-District Advection Transport Flux Ranking",
)
async def get_advection_flux(
    pollutant: str = Query("PM2.5", description="Mass pollutant species (AQI is strictly prohibited)"),
    timestamp: Optional[datetime] = Query(None, description="Observation timestamp; defaults to latest"),
    limit: int = Query(60, ge=1, le=200, description="Maximum pathway corridors to return"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> FluxTransportResponse:
    """
    Computes inter-district advective mass transport flux vectors and net mass balance.
    Enforces domain invariant: AQI is dimensionless and strictly prohibited from mass advection.
    """
    # CRITICAL PHYSICAL DOMAIN GUARD
    if pollutant.strip().upper() == "AQI":
        raise HTTPException(
            status_code=400,
            detail=(
                "Advection transport mass flux is physically undefined for dimensionless ordinal index 'AQI'. "
                "Mass conservation requires conserved physical concentrations. "
                "Query a mass pollutant species such as PM2.5, PM10, NO2, SO2, CO, or O3."
            ),
        )

    try:
        dto = analytics_service.calculate_flux(
            pollutant=pollutant,
            timestamp=timestamp,
            top_k=limit,
        )
        return FluxTransportResponse.model_validate(dto)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Advection flux calculation failed: {str(e)}")


@router.get(
    "/transboundary",
    response_model=TransboundaryResponse,
    summary="Cross-Border Transboundary Transport Index",
)
async def get_transboundary_analysis(
    timestamp: Optional[datetime] = Query(None, description="Observation timestamp; defaults to latest"),
    pollutant: str = Query("PM2.5", description="Target pollutant species"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> TransboundaryResponse:
    """Computes transboundary cross-border mass flux across 120km border districts and 39 border normal vector nodes."""
    try:
        dto = analytics_service.calculate_transboundary(
            timestamp=timestamp,
            pollutant=pollutant,
        )
        return TransboundaryResponse.model_validate(dto)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transboundary analysis failed: {str(e)}")
