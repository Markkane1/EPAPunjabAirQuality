"""Pydantic v2 schemas for continuous 2D spatial surface raster fields."""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SpatialSurfaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    timestamp: str = Field(..., description="Snapshot timestamp")
    pollutant: str = Field(...)
    grid_width: int = Field(..., description="Horizontal cell count")
    grid_height: int = Field(..., description="Vertical cell count")
    resolution: int = Field(default=5, description="Pixel cell step size")
    min_val: float = Field(..., description="Minimum interpolated concentration in domain")
    max_val: float = Field(..., description="Maximum interpolated concentration in domain")
    grid_matrix: List[List[float]] = Field(..., description="2D array of continuous field values [y][x]")
    opacity_matrix: Optional[List[List[int]]] = Field(
        default=None, description="Optional 2D array of geostatistical distance confidence alpha channels [95, 235]"
    )
