"""API Route Module: Continuous Geospatial Interpolation Surface & Labels (/api/v1/spatial)."""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import get_spatial_service
from src.api.schemas.spatial import LabelPlacementResponse, SpatialSurfaceResponse
from src.services.spatial_service import SpatialService

router = APIRouter(prefix="/api/v1/spatial", tags=["Spatial"])


@router.get(
    "/surface",
    response_model=SpatialSurfaceResponse,
    summary="Retrieve 2D continuous interpolated raster field",
)
async def get_spatial_surface(
    timestamp: Optional[datetime] = Query(None, description="Observation timestamp; defaults to latest"),
    pollutant: str = Query("PM2.5", description="Pollutant species to interpolate (e.g. PM2.5, PM10, AQI)"),
    resolution: int = Query(5, ge=1, le=50, description="Spatial resolution step in pixels (lower = finer, default = 5)"),
    width_px: int = Query(600, ge=100, le=2400, description="Raster field width in screen pixels"),
    height_px: int = Query(450, ge=100, le=1800, description="Raster field height in screen pixels"),
    anisotropic: bool = Query(False, description="Whether to apply wind-steered anisotropic plume weighting"),
    spatial_service: SpatialService = Depends(get_spatial_service),
) -> SpatialSurfaceResponse:
    """Computes dynamic 2D IDW geostatistical surface grid matrix with distance confidence opacity."""
    try:
        dto = spatial_service.get_surface_matrix(
            timestamp=timestamp,
            pollutant=pollutant,
            resolution=resolution,
            width_px=width_px,
            height_px=height_px,
            use_anisotropic=anisotropic,
        )
        return SpatialSurfaceResponse.model_validate(dto)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spatial surface calculation failed: {str(e)}")


@router.get(
    "/labels",
    response_model=List[LabelPlacementResponse],
    summary="Retrieve greedy collision-free district label placements",
)
async def get_district_labels(
    width_px: float = Query(1200.0, ge=300.0, le=3840.0, description="Viewport canvas width in pixels"),
    height_px: float = Query(900.0, ge=200.0, le=2160.0, description="Viewport canvas height in pixels"),
    spatial_service: SpatialService = Depends(get_spatial_service),
) -> List[LabelPlacementResponse]:
    """Computes collision-free district text labels with leader line displacement vectors."""
    try:
        placements = spatial_service.get_district_label_placements(
            width_px=width_px,
            height_px=height_px,
        )
        return [LabelPlacementResponse.model_validate(p) for p in placements]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Label placement calculation failed: {str(e)}")
