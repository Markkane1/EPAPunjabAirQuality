"""API Route Module: Continuous Geospatial Interpolation Surface (/api/v1/spatial)."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import get_spatial_service
from src.api.schemas.spatial import SpatialSurfaceResponse
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
    spatial_service: SpatialService = Depends(get_spatial_service),
) -> SpatialSurfaceResponse:
    """Computes or retrieves precomputed 2D IDW surface grid matrix with distance confidence opacity."""
    try:
        dto = spatial_service.get_surface_matrix(
            timestamp=timestamp,
            pollutant=pollutant,
            resolution=resolution,
        )
        return SpatialSurfaceResponse.model_validate(dto)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spatial surface calculation failed: {str(e)}")
