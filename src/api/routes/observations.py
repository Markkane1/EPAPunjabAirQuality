"""API Route Module: Current & Historical Observations (/api/v1/observations)."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import get_observation_service
from src.api.schemas.observations import CurrentObservationsResponse, HourlyObservationsResponse
from src.services.observation_service import ObservationService

router = APIRouter(prefix="/api/v1/observations", tags=["Observations"])


@router.get(
    "/current",
    response_model=CurrentObservationsResponse,
    summary="Retrieve current air quality telemetry snapshot",
)
async def get_current_observations(
    pollutant: str = Query("AQI", description="Target pollutant species or composite index"),
    district: Optional[str] = Query(None, description="Optional district filter"),
    obs_service: ObservationService = Depends(get_observation_service),
) -> CurrentObservationsResponse:
    """Returns the latest available hourly observation snapshot across all districts and stations."""
    try:
        dto = obs_service.get_current_snapshot(pollutant=pollutant, district=district)
        return CurrentObservationsResponse.model_validate(dto)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve current observations: {str(e)}")


@router.get(
    "/hourly",
    response_model=HourlyObservationsResponse,
    summary="Query historical hourly observation series",
)
async def get_hourly_observations(
    district: Optional[str] = Query(None, description="Optional district name filter"),
    pollutant: str = Query("AQI", description="Pollutant species: AQI, PM2.5, PM10, NO2, SO2, CO, O3, NO, NOx"),
    start_time: Optional[datetime] = Query(None, description="Start timestamp (UTC)"),
    end_time: Optional[datetime] = Query(None, description="End timestamp (UTC)"),
    obs_service: ObservationService = Depends(get_observation_service),
) -> HourlyObservationsResponse:
    """Returns continuous time-series arrays for temporal scrubbing and trend charting."""
    try:
        dto = obs_service.get_hourly_series(
            pollutant=pollutant,
            district=district,
            start_time=start_time,
            end_time=end_time,
        )
        return HourlyObservationsResponse.model_validate(dto)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query hourly observations: {str(e)}")
