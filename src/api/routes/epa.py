"""
API Route Module: EPA Punjab Live AQMS Gateway (/api/v1/epa).
Direct live integration with the official Environmental Protection Department AQMS network:
Base URL: https://api.epd-aqms-pk.com
"""
import asyncio
from datetime import datetime, timezone, timedelta
import logging
import re
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from src.api.schemas.epa import (
    EPAAlertItem,
    EPAAlertsResponse,
    EPAHealthStatus,
    EPALatestObservation,
    EPALatestResponse,
    EPAStationMeta,
)
from src.domain.constants.epa_stations import (
    EPA_STATIONS_CATALOG,
    get_all_epa_stations,
    get_epa_station_info,
)
from src.domain.schemas.measurement import PKT, UTC
from src.pipelines.epa_punjab import EPAPunjabIngestionWorker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/epa", tags=["EPA Punjab Live AQMS"])

# Singleton worker instance for route queries
_worker: Optional[EPAPunjabIngestionWorker] = None
_latest_cache: Optional[Dict[str, Any]] = None
_latest_cache_time: float = 0.0
CACHE_TTL_SECONDS: float = 60.0  # Cache live snapshot for 60 seconds


def get_epa_worker() -> EPAPunjabIngestionWorker:
    """Returns singleton EPAPunjabIngestionWorker."""
    global _worker
    if _worker is None:
        _worker = EPAPunjabIngestionWorker()
    return _worker


@router.get(
    "/stations",
    response_model=List[EPAStationMeta],
    summary="List all 38 official EPA Punjab AQMS stations",
)
async def list_epa_stations() -> List[EPAStationMeta]:
    """Returns the official 38-station monitoring directory with coordinates and district mappings."""
    stations = get_all_epa_stations()
    return [
        EPAStationMeta(
            api_id=s["api_id"],
            display_name=s["display_name"],
            city=s["city"],
            district=s["district"],
            latitude=s["latitude"],
            longitude=s["longitude"],
            station_type=s["station_type"],
        )
        for s in stations
    ]


@router.get(
    "/latest",
    response_model=EPALatestResponse,
    summary="Retrieve live latest hour telemetry across all 38 EPA stations",
)
async def get_epa_latest(
    force_refresh: bool = Query(False, description="Bypass in-memory cache and fetch live from upstream"),
) -> EPALatestResponse:
    """
    Directly queries GET /latest_hour from https://api.epd-aqms-pk.com.
    Enriches raw station measurements with coordinates, district mappings,
    quality status checks, and data staleness metrics.
    """
    global _latest_cache, _latest_cache_time
    worker = get_epa_worker()
    now_ts = time.time()

    if not force_refresh and _latest_cache and (now_ts - _latest_cache_time < CACHE_TTL_SECONDS):
        raw_dict = _latest_cache
    else:
        try:
            raw_dict = await worker.fetch_latest_hour()
            _latest_cache = raw_dict
            _latest_cache_time = now_ts
        except Exception as e:
            logger.error("Failed to fetch live latest_hour from EPA API: %s", e)
            if _latest_cache:
                logger.warning("Serving stale cached latest_hour data due to upstream error.")
                raw_dict = _latest_cache
            else:
                raise HTTPException(status_code=502, detail=f"Failed to query live EPA Punjab API: {str(e)}")

    observations: List[EPALatestObservation] = []
    active_count = 0
    stale_count = 0
    now_utc = datetime.now(timezone.utc)

    for api_id, s_info in EPA_STATIONS_CATALOG.items():
        # Match data by api_id or display name
        raw_record = raw_dict.get(api_id) or raw_dict.get(s_info["display_name"]) or {}

        dt_str = raw_record.get("Date_Time") or "2026-01-01 00:00:00"
        try:
            if "T" in dt_str:
                dt_val = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            else:
                dt_val = datetime.strptime(dt_str[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=PKT).astimezone(UTC)
        except Exception:
            dt_val = datetime(2026, 1, 1, tzinfo=timezone.utc)

        # Staleness computation: > 6 hours old tagged as stale
        delta_hours = max(0.0, (now_utc - dt_val).total_seconds() / 3600.0)
        is_stale = delta_hours > 6.0
        if is_stale:
            stale_count += 1
        else:
            active_count += 1

        # Check Status_* flags
        def _get_val(key: str, status_key: Optional[str] = None) -> Optional[float]:
            if status_key and status_key in raw_record:
                status_str = str(raw_record[status_key]).strip().lower()
                if status_str in {"incomplete", "n/a", "invalid", "null"}:
                    return None
            val = raw_record.get(key)
            if val is None:
                return None
            try:
                f_val = float(val)
                return None if f_val <= 0.0 else f_val
            except (ValueError, TypeError):
                return None

        pm25 = _get_val("PM25", "Status_PM25")
        pm10 = _get_val("PM10", "Status_PM10")
        o3 = _get_val("O3", "Status_O3")
        no2 = _get_val("NO2", "Status_NO2")
        so2 = _get_val("SO2", "Status_SO2")
        co = _get_val("CO", "Status_CO")
        no = _get_val("NO", "Status_NO")
        nox = _get_val("NOX", "Status_NOX")
        ws = _get_val("WS")
        wd = _get_val("WD")
        temp = _get_val("Temp")
        rh = _get_val("RH")
        bp = _get_val("BP")
        rain = _get_val("Rain")
        sr = _get_val("SR")

        aqi_raw = raw_record.get("AQI")
        try:
            aqi_val = float(aqi_raw) if aqi_raw is not None else None
        except (ValueError, TypeError):
            aqi_val = None

        qc_flags = []
        if pm25 and pm25 > 1000.0:
            qc_flags.append("QC_EXCEEDANCE_EXTREME")
        if pm10 and pm10 > 1500.0:
            qc_flags.append("QC_EXCEEDANCE_EXTREME")
        if is_stale:
            qc_flags.append("STALE_SENSOR_CLOCK")

        observations.append(
            EPALatestObservation(
                station_id=api_id,
                station_name=s_info["display_name"],
                district=s_info["district"],
                city=s_info["city"],
                latitude=s_info["latitude"],
                longitude=s_info["longitude"],
                station_type=s_info["station_type"],
                observed_at_pkt=dt_str,
                observed_at_utc=dt_val,
                is_stale=is_stale,
                stale_hours=round(delta_hours, 1),
                aqi=aqi_val,
                aqi_category=raw_record.get("AQI_category"),
                dominant_pollutant=raw_record.get("Dominant_Pollutant"),
                pm25=pm25,
                pm10=pm10,
                o3=o3,
                no2=no2,
                so2=so2,
                co=co,
                no=no,
                nox=nox,
                wind_speed=ws,
                wind_direction=wd,
                temp_c=temp,
                relative_humidity=rh,
                barometric_pressure_hpa=bp,
                rain_mm=rain,
                solar_radiation=sr,
                qc_flags=qc_flags,
            )
        )

    return EPALatestResponse(
        status="success",
        source="epd-aqms-pk.com",
        upstream_url=worker.base_url,
        timestamp_fetched_utc=datetime.now(timezone.utc),
        total_stations=len(observations),
        active_reporting_stations=active_count,
        stale_reporting_stations=stale_count,
        stations=observations,
    )


@router.get(
    "/daily",
    summary="Retrieve current day hourly series for a station or all stations",
)
async def get_epa_daily(
    station_id: Optional[str] = Query(None, description="Optional station API ID (e.g. UET-LHR, Safari Park-LHR)"),
) -> Dict[str, Any]:
    """Queries GET /daily/{stationId} or GET /daily from live EPA AQMS API."""
    worker = get_epa_worker()
    try:
        data = await worker.fetch_daily(station_id=station_id)
        return {"status": "success", "data": data}
    except Exception as e:
        logger.error("Failed to query /daily from EPA: %s", e)
        raise HTTPException(status_code=502, detail=f"Failed to fetch daily data: {str(e)}")


@router.get(
    "/monthly",
    summary="Retrieve current month daily aggregates for a station or all stations",
)
async def get_epa_monthly(
    station_id: Optional[str] = Query(None, description="Optional station API ID"),
) -> Dict[str, Any]:
    """Queries GET /monthly/{stationId} or GET /monthly from live EPA AQMS API."""
    worker = get_epa_worker()
    try:
        data = await worker.fetch_monthly(station_id=station_id)
        return {"status": "success", "data": data}
    except Exception as e:
        logger.error("Failed to query /monthly from EPA: %s", e)
        raise HTTPException(status_code=502, detail=f"Failed to fetch monthly data: {str(e)}")


@router.get(
    "/periodic",
    summary="Query custom periodic time-series window for an EPA station",
)
async def get_epa_periodic(
    station_id: str = Query(..., description="Target station API ID (e.g. UET-LHR)"),
    start_datetime: str = Query(..., description="Start datetime: 'YYYY-MM-DD HH:mm:ss'"),
    end_datetime: str = Query(..., description="End datetime: 'YYYY-MM-DD HH:mm:ss'"),
    interval: str = Query("60", description="Aggregation interval in minutes: '05', '15', '30', '60', '1440'"),
) -> Dict[str, Any]:
    """Queries GET /periodic/{stationId} with custom range and interval."""
    worker = get_epa_worker()
    try:
        data = await worker.fetch_periodic(
            station_id=station_id,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            interval=interval,
        )
        return {"status": "success", "data": data}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error("Failed to query /periodic from EPA: %s", e)
        raise HTTPException(status_code=502, detail=f"Failed to fetch periodic data: {str(e)}")


@router.get(
    "/alerts",
    response_model=EPAAlertsResponse,
    summary="Retrieve operational telemetry alerts from EPA AQMS network",
)
async def get_epa_alerts(
    limit: int = Query(100, ge=1, le=1000, description="Max alerts to return"),
    code: Optional[str] = Query(None, description="Optional filter by alert code (e.g. E04.3, E04.2, E08, E07)"),
) -> EPAAlertsResponse:
    """
    Queries GET /alerts/last_two_days.
    Extracts structured alert code (E04.3 no data from station, E04.2 dust analyzer, etc.)
    and provides sorted telemetry logs.
    """
    worker = get_epa_worker()
    try:
        raw_alerts = await worker.fetch_alerts_last_two_days()
    except Exception as e:
        logger.error("Failed to query /alerts from EPA: %s", e)
        raise HTTPException(status_code=502, detail=f"Failed to fetch alerts: {str(e)}")

    parsed_alerts: List[EPAAlertItem] = []
    code_pattern = re.compile(r"^(E\d+(?:\.\d+)?):")

    for a in raw_alerts:
        msg = a.get("Alert", "")
        dt_str = a.get("Date_Time", "")

        match = code_pattern.search(msg.strip())
        alert_code = match.group(1) if match else None

        if code and alert_code != code:
            continue

        ts_utc = None
        if dt_str:
            try:
                ts_utc = datetime.strptime(dt_str[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=PKT).astimezone(UTC)
            except Exception:
                pass

        parsed_alerts.append(
            EPAAlertItem(
                code=alert_code,
                alert=msg,
                date_time=dt_str,
                timestamp_utc=ts_utc,
            )
        )

        if len(parsed_alerts) >= limit:
            break

    return EPAAlertsResponse(
        status="success",
        count=len(parsed_alerts),
        alerts=parsed_alerts,
    )


@router.get(
    "/status",
    response_model=EPAHealthStatus,
    summary="Check connectivity health and latency to EPA Punjab API host",
)
async def get_epa_health() -> EPAHealthStatus:
    """Performs active ping against https://api.epd-aqms-pk.com/latest_hour to assess network latency and health."""
    worker = get_epa_worker()
    start_t = time.perf_counter()
    try:
        await worker.fetch_latest_hour()
        latency = (time.perf_counter() - start_t) * 1000.0
        return EPAHealthStatus(
            status="healthy",
            upstream_url=worker.base_url,
            latency_ms=round(latency, 2),
            circuit_breaker_open=worker.circuit_breaker_open,
            is_healthy=worker.is_healthy,
            last_checked=datetime.now(timezone.utc),
        )
    except Exception as e:
        latency = (time.perf_counter() - start_t) * 1000.0
        return EPAHealthStatus(
            status=f"degraded: {str(e)}",
            upstream_url=worker.base_url,
            latency_ms=round(latency, 2),
            circuit_breaker_open=worker.circuit_breaker_open,
            is_healthy=False,
            last_checked=datetime.now(timezone.utc),
        )
