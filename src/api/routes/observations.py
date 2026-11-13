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


@router.get(
    "/cross-border",
    summary="Query regional cross-border reference cities",
)
async def get_cross_border_cities(
    obs_service: ObservationService = Depends(get_observation_service),
):
    """Returns air quality measurements for cross-border upwind reference cities."""
    try:
        cities = obs_service.get_cross_border_observations()
        return {"status": "success", "count": len(cities), "cities": cities}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve cross-border cities: {str(e)}")


@router.get(
    "/rolling-mean",
    summary="Query true 24-hour moving average",
)
async def get_rolling_mean(
    entity_type: str = Query("district", description="'district' or 'station'"),
    entity_id: str = Query("Lahore", description="District or station identifier"),
    pollutant: str = Query("PM2.5", description="Target pollutant species"),
    timestamp: Optional[datetime] = Query(None, description="Anchor timestamp (UTC)"),
    obs_service: ObservationService = Depends(get_observation_service),
):
    """Computes arithmetic mean over the preceding 24-hour rolling window."""
    try:
        mean_val = obs_service.get_24h_rolling_mean(
            entity_type=entity_type,
            entity_id=entity_id,
            pollutant=pollutant,
            timestamp=timestamp,
        )
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "pollutant": pollutant,
            "rolling_24h_mean": mean_val,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate rolling mean: {str(e)}")


@router.get(
    "/fires",
    summary="Query active satellite thermal anomaly fire detections",
)
async def get_active_fires(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    region: Optional[str] = Query(None, description="Optional region filter"),
    min_frp: Optional[float] = Query(None, ge=0.0, description="Minimum FRP in MW"),
    obs_service: ObservationService = Depends(get_observation_service),
):
    """Returns spaceborne VIIRS active fire anomalies across the Punjab airshed."""
    try:
        fires = obs_service.get_active_fire_observations(hours=hours, region=region, min_frp=min_frp)
        summary = obs_service.get_fire_summary().get("summary", {})
        return {
            "status": "success",
            "count": len(fires),
            "live_fires": summary.get("live_fires_count", len(fires)),
            "fires_24h": summary.get("fires_24h_count", len(fires)),
            "fires": fires,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve active fires: {str(e)}")


@router.get(
    "/fires/summary",
    summary="Query fire anomalies summary and 12-month monthly trends",
)
async def get_fire_summary(
    obs_service: ObservationService = Depends(get_observation_service),
):
    """Returns comprehensive 24h, live, and 12-month historical monthly trend statistics."""
    try:
        return obs_service.get_fire_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve fire summary: {str(e)}")


@router.get(
    "/fires/history",
    summary="Query historic fire anomalies by date duration, month, or range",
)
async def get_historic_fires(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    duration: Optional[str] = Query(None, description="Preset: '24h', '7d', '30d', '1y', 'live', 'custom'"),
    month: Optional[str] = Query(None, description="Specific month filter, e.g. '2026-10'"),
    region: Optional[str] = Query(None, description="Filter by region (e.g. 'Punjab (India)', 'Punjab (Pakistan)')"),
    min_frp: Optional[float] = Query(None, ge=0.0, description="Minimum Fire Radiative Power (MW)"),
    limit: int = Query(2000, ge=1, le=10000, description="Max detections to return"),
    obs_service: ObservationService = Depends(get_observation_service),
):
    """Returns filtered historical VIIRS fire anomalies across requested date duration or month."""
    try:
        return obs_service.get_historic_fire_observations(
            start_date=start_date,
            end_date=end_date,
            duration=duration,
            month=month,
            region=region,
            min_frp=min_frp,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query historic fires: {str(e)}")
