"""API Route Module: Geographic & Station Metadata (/api/v1/meta)."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_district_repository, get_station_repository
from src.api.schemas.meta import DistrictMetaResponse, StationMetaResponse
from src.domain.interfaces.repositories import DistrictRepository, StationRepository

router = APIRouter(prefix="/api/v1/meta", tags=["Metadata"])


@router.get(
    "/districts",
    response_model=List[DistrictMetaResponse],
    summary="Retrieve administrative district metadata",
)
async def get_districts(
    monitored_only: bool = Query(False, description="Filter for districts with active ground monitoring stations"),
    district_repo: DistrictRepository = Depends(get_district_repository),
    station_repo: StationRepository = Depends(get_station_repository),
) -> List[DistrictMetaResponse]:
    """Returns all 41 administrative districts of Punjab with boundaries, centroids, and transboundary sectors."""
    districts = district_repo.list_all_districts(monitored_only=monitored_only)
    results: List[DistrictMetaResponse] = []
    for d in districts:
        boundary_geom = district_repo.get_boundary(d.id)
        station_names = [s.name for s in station_repo.list_by_district(d.name)]
        results.append(
            DistrictMetaResponse(
                id=str(d.id),
                name=d.name,
                division=d.division,
                latitude=d.latitude,
                longitude=d.longitude,
                is_monitored=d.is_monitored,
                border_distance_km=d.border_distance_km,
                india_inflow_sectors=list(d.india_inflow_sectors),
                stations=station_names,
                boundary=boundary_geom,
            )
        )
    return results


@router.get(
    "/stations",
    response_model=List[StationMetaResponse],
    summary="Retrieve monitoring station directory",
)
async def get_stations(
    district: Optional[str] = Query(None, description="Filter by district name (case-insensitive)"),
    station_type: Optional[str] = Query(None, description="Filter by type: fixed, mobile, airport_metar, wmo_synop"),
    station_repo: StationRepository = Depends(get_station_repository),
) -> List[StationMetaResponse]:
    """Returns all 79 active environmental monitoring stations and regional aerodromes."""
    if district:
        stations = station_repo.list_by_district(district)
    else:
        stations = station_repo.list_stations(station_type=station_type)

    return [
        StationMetaResponse(
            id=str(s.id),
            name=s.name,
            district=s.district,
            latitude=s.latitude,
            longitude=s.longitude,
            station_type=s.station_type,
            has_anemometer=s.has_anemometer,
            anemometer_blacklisted=s.anemometer_blacklisted,
            altitude_m=s.altitude_m,
            network_type=s.metadata.get("network_type", s.station_type),
            metadata=s.metadata,
        )
        for s in stations
    ]
