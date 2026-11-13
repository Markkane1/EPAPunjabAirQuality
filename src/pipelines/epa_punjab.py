"""
EPA Punjab Live AQMS Ingestion Worker.
Connects directly to the provincial Environmental Protection Department (EPD) AQMS API:
Base URL: https://api.epd-aqms-pk.com
Static API Key: 7b2f49c1e0e447c6a2bde74b81f51a87

Implements:
1. Complete 38-station monitoring network telemetry ingestion (GET /latest_hour)
2. Daily hourly profiles (GET /daily/{stationId} and GET /daily)
3. Monthly daily aggregates (GET /monthly/{stationId} and GET /monthly)
4. Arbitrary periodic time-series windows (GET /periodic/{stationId})
5. Operational telemetry alerts ingestion (GET /alerts/last_two_days and GET /alerts/range)
6. Status_* quality flag enforcement (Incomplete, N/A, Invalid -> None)
7. Extreme crisis smog exceedance tagging (>1000 PM2.5, >1500 PM10)
8. Circuit breaker with jittered exponential retry and fallback to FallbackTemplateEngine
"""
import asyncio
from datetime import datetime, timezone, timedelta
import logging
import os
import random
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote

import httpx

from src.domain.constants.epa_stations import (
    EPA_STATIONS_CATALOG,
    get_epa_station_info,
    resolve_district_for_station,
)
from src.domain.schemas.measurement import RawStationMeasurement, PKT, UTC
from src.pipelines.base import BaseIngestionWorker
from src.pipelines.fallback_engine import FallbackTemplateEngine, EXCLUDED_STATIONS

logger = logging.getLogger(__name__)

INVALID_STATUS_STRINGS = {"incomplete", "n/a", "invalid", "null", "none"}


class EPAPunjabIngestionWorker(BaseIngestionWorker):
    """
    Client and Ingestion Worker for Environmental Protection Department (EPD) Punjab.
    Connects to the official live AQMS API at https://api.epd-aqms-pk.com.
    """

    DEFAULT_BASE_URL: str = "https://api.epd-aqms-pk.com"
    DEFAULT_API_KEY: str = "7b2f49c1e0e447c6a2bde74b81f51a87"
    DEFAULT_USER_AGENT: str = "EMC-EPA-Punjab-AQ-dashboard/1.0"

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        user_agent: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        fallback_engine: Optional[FallbackTemplateEngine] = None,
        timeout: float = 30.0,
    ) -> None:
        super().__init__(
            stream_id="STR-01-EPAPUNJAB",
            name="EPA Punjab AQMS Live Feed Worker",
            polling_cadence="3 * * * *",  # Poll at HH:03 per API docs
            fallback_engine=fallback_engine,
        )
        self.base_url = (base_url or os.getenv("EPA_PUNJAB_BASE_URL", self.DEFAULT_BASE_URL)).rstrip("/")
        self.api_key = api_key or os.getenv("EPA_PUNJAB_API_KEY", self.DEFAULT_API_KEY)
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.client = client
        self.timeout = timeout
        self.retry_delays = [2.0, 8.0, 20.0]

    def _get_headers(self) -> Dict[str, str]:
        """Builds mandatory request headers including static X-API-Key."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def fetch_data(
        self,
        endpoint: str = "/latest_hour",
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Executes HTTP GET against EPA Punjab API with 3 retries and exponential backoff.
        Handles URL path parameter formatting and query parameters.
        """
        # Ensure endpoint begins with /
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"

        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        last_exception: Optional[Exception] = None

        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout, connect=10.0),
            headers=headers,
            follow_redirects=True,
        )

        try:
            for attempt, delay in enumerate(self.retry_delays, start=1):
                try:
                    response = await client.get(url, params=params, headers=headers)
                    response.raise_for_status()
                    return response.json()
                except (httpx.HTTPStatusError, httpx.RequestError, ValueError) as exc:
                    last_exception = exc
                    if attempt < len(self.retry_delays):
                        jitter = delay * (0.8 + 0.4 * random.random())
                        logger.warning(
                            "EPA Punjab request to %s failed (attempt %d/%d): %s. Retrying in %.2fs...",
                            url,
                            attempt,
                            len(self.retry_delays),
                            exc,
                            jitter,
                        )
                        await asyncio.sleep(jitter)
                    else:
                        logger.error("EPA Punjab all %d retry attempts exhausted for %s.", len(self.retry_delays), url)
            if last_exception:
                raise last_exception
            raise RuntimeError(f"Unknown error during EPA Punjab data fetch from {url}")
        finally:
            if owns_client:
                await client.aclose()

    async def fetch_latest_hour(self) -> Dict[str, Any]:
        """
        GET /latest_hour
        Retrieves the last stored hour for all 38 AQMS stations.
        """
        return await self.fetch_data("/latest_hour")

    async def fetch_daily(self, station_id: Optional[str] = None) -> Union[Dict[str, Any], List[Any]]:
        """
        GET /daily/{stationId} or GET /daily
        Retrieves hourly rows for the current calendar day (00:00 through latest hour).
        """
        if station_id:
            encoded_id = quote(station_id, safe="")
            return await self.fetch_data(f"/daily/{encoded_id}")
        return await self.fetch_data("/daily")

    async def fetch_monthly(self, station_id: Optional[str] = None) -> Union[Dict[str, Any], List[Any]]:
        """
        GET /monthly/{stationId} or GET /monthly
        Retrieves one daily aggregate row per day of the current month.
        """
        if station_id:
            encoded_id = quote(station_id, safe="")
            return await self.fetch_data(f"/monthly/{encoded_id}")
        return await self.fetch_data("/monthly")

    async def fetch_periodic(
        self,
        station_id: str,
        start_datetime: str,
        end_datetime: str,
        interval: str = "60",
    ) -> Dict[str, Any]:
        """
        GET /periodic/{stationId}?start_datetime=...&end_datetime=...&interval=...
        Retrieves custom time-series window.
        Intervals allowed by server: '05', '15', '30', '60', '1440'.
        """
        valid_intervals = {"05", "15", "30", "60", "1440"}
        if str(interval) not in valid_intervals:
            raise ValueError(f"Invalid interval '{interval}'. Must be one of {valid_intervals}")

        encoded_id = quote(station_id, safe="")
        params = {
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "interval": str(interval),
        }
        return await self.fetch_data(f"/periodic/{encoded_id}", params=params)

    async def fetch_alerts_last_two_days(self) -> List[Dict[str, Any]]:
        """
        GET /alerts/last_two_days
        Retrieves operational alerts for approximately the last 48 hours.
        """
        res = await self.fetch_data("/alerts/last_two_days")
        if isinstance(res, list):
            return res
        return []

    async def fetch_alerts_range(
        self,
        start_datetime: str,
        end_datetime: str,
    ) -> List[Dict[str, Any]]:
        """
        GET /alerts/range?start_datetime=...&end_datetime=...
        Retrieves operational alerts for a bounded timestamp window.
        """
        params = {
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
        }
        res = await self.fetch_data("/alerts/range", params=params)
        if isinstance(res, list):
            return res
        return []

    async def fan_out_missing_districts(
        self, missing_districts: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Asynchronously queries fallback district feeds for omitted districts if available.
        Maintained for legacy compatibility with multi-source collectors.
        """
        if not missing_districts:
            return []

        supplementary: List[Dict[str, Any]] = []
        for d in missing_districts:
            try:
                data = await self.fetch_data(f"/api/district-stations/{d}")
                if isinstance(data, list):
                    supplementary.extend(data)
                elif isinstance(data, dict) and "data" in data:
                    supplementary.extend(data["data"])
            except Exception as e:
                logger.debug("District fan-out skipped for %s: %s", d, e)
        return supplementary

    def parse_and_validate(self, raw_data: Any) -> List[RawStationMeasurement]:
        """
        Parses live EPA AQMS responses into validated RawStationMeasurement models.
        Supports:
        1. /latest_hour dictionary format: { "Station-ID": { "Date_Time": "...", "PM25": 46.39, ... } }
        2. /daily or /periodic format: { "Station-ID": [ { ... }, { ... } ] }
        3. Legacy envelope format: { "data": [ ... ] } or [ ... ]
        Filters unlocatable stations (OneNetwork Station 25) and enforces Status_* checks.
        """
        items_to_process: List[Dict[str, Any]] = []

        if isinstance(raw_data, list):
            items_to_process = [i for i in raw_data if isinstance(i, dict)]
        elif isinstance(raw_data, dict):
            if "data" in raw_data and isinstance(raw_data["data"], list):
                items_to_process = [i for i in raw_data["data"] if isinstance(i, dict)]
            elif "stations" in raw_data and isinstance(raw_data["stations"], list):
                items_to_process = [i for i in raw_data["stations"] if isinstance(i, dict)]
            else:
                # Keyed by station identifier (e.g. /latest_hour or /daily or /periodic)
                for station_key, val in raw_data.items():
                    if isinstance(val, dict):
                        # Skip error dictionaries like {"error": "Station not found"}
                        if "error" in val:
                            continue
                        record = dict(val)
                        if "station_id" not in record and "id" not in record:
                            record["station_id"] = station_key
                        if "station_name" not in record and "name" not in record:
                            record["station_name"] = station_key
                        items_to_process.append(record)
                    elif isinstance(val, list):
                        for row in val:
                            if isinstance(row, dict) and "error" not in row:
                                record = dict(row)
                                if "station_id" not in record and "id" not in record:
                                    record["station_id"] = station_key
                                if "station_name" not in record and "name" not in record:
                                    record["station_name"] = station_key
                                items_to_process.append(record)
        else:
            raise ValueError(f"Unexpected EPA Punjab payload type: {type(raw_data)}")

        validated: List[RawStationMeasurement] = []

        for item in items_to_process:
            s_name = str(item.get("station_name") or item.get("name") or "").strip()
            s_id = str(item.get("station_id") or item.get("id") or s_name).strip()

            if not s_name and not s_id:
                continue

            # Exclusion rule: OneNetwork Station 25 lacks verifiable ground coordinates
            lower_name = s_name.lower()
            lower_id = s_id.lower()
            if any(exc in lower_name or exc in lower_id for exc in EXCLUDED_STATIONS):
                logger.debug("Excluding station from EPA payload: %s (id: %s)", s_name, s_id)
                continue

            # Canonical station directory lookup
            info = get_epa_station_info(s_id) or get_epa_station_info(s_name)
            canonical_name = info["display_name"] if info else (s_name or s_id)
            canonical_district = info["district"] if info else item.get("district") or resolve_district_for_station(canonical_name)

            # Datetime extraction and conversion to UTC
            dt_raw = item.get("Date_Time") or item.get("timestamp") or item.get("date_time")
            if dt_raw:
                if isinstance(dt_raw, datetime):
                    dt_val = dt_raw
                else:
                    dt_str = str(dt_raw).strip()
                    try:
                        # Space format: YYYY-MM-DD HH:MM:SS (naive PKT)
                        if "T" not in dt_str and len(dt_str) >= 19:
                            dt_val = datetime.strptime(dt_str[:19], "%Y-%m-%d %H:%M:%S")
                            dt_val = dt_val.replace(tzinfo=PKT).astimezone(UTC)
                        else:
                            # ISO format
                            dt_val = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                    except Exception:
                        dt_val = datetime.now(timezone.utc)
            else:
                dt_val = datetime.now(timezone.utc)

            # Extract measurement attributes with Status_* checks
            def _extract_val(primary_key: str, fallback_key: str, status_field: Optional[str] = None) -> Optional[float]:
                if status_field and status_field in item:
                    status_val = str(item[status_field]).strip().lower()
                    if status_val in INVALID_STATUS_STRINGS:
                        return None
                val = item.get(primary_key)
                if val is None:
                    val = item.get(fallback_key)
                if val is None:
                    return None
                try:
                    num = float(val)
                    return num
                except (ValueError, TypeError):
                    return None

            pm25 = _extract_val("PM25", "pm25", "Status_PM25")
            pm10 = _extract_val("PM10", "pm10", "Status_PM10")
            o3 = _extract_val("O3", "o3", "Status_O3")
            co = _extract_val("CO", "co", "Status_CO")
            so2 = _extract_val("SO2", "so2", "Status_SO2")
            no = _extract_val("NO", "no", "Status_NO")
            no2 = _extract_val("NO2", "no2", "Status_NO2")
            nox = _extract_val("NOX", "nox", "Status_NOX")
            ws = _extract_val("WS", "wind_speed")
            wd = _extract_val("WD", "wind_direction")

            aqi_val = item.get("AQI")
            if aqi_val is None:
                aqi_val = item.get("aqi")
            try:
                aqi_num = float(aqi_val) if aqi_val is not None else None
            except (ValueError, TypeError):
                aqi_num = None

            # Build standardized measurement payload
            payload: Dict[str, Any] = {
                "station_id": s_id,
                "station_name": canonical_name,
                "district": canonical_district,
                "timestamp": dt_val,
                "aqi": aqi_num,
                "pm25": pm25,
                "pm10": pm10,
                "no2": no2,
                "so2": so2,
                "co": co,
                "o3": o3,
                "no": no,
                "nox": nox,
                "wind_speed": ws,
                "wind_direction": wd,
                "is_estimated": False,
                "qc_flags": list(item.get("qc_flags", [])),
            }

            # Preserve extreme crisis smog exceedance tags
            if pm25 is not None and pm25 > 1000.0:
                if "QC_EXCEEDANCE_EXTREME" not in payload["qc_flags"]:
                    payload["qc_flags"].append("QC_EXCEEDANCE_EXTREME")
            if pm10 is not None and pm10 > 1500.0:
                if "QC_EXCEEDANCE_EXTREME" not in payload["qc_flags"]:
                    payload["qc_flags"].append("QC_EXCEEDANCE_EXTREME")

            try:
                meas = RawStationMeasurement(**payload)
                validated.append(meas)
            except Exception as e:
                logger.warning("Dropped invalid station record %s: %s", s_name, e)

        return validated

    def get_fallback(self, hour_idx: int = -1, **kwargs: Any) -> List[RawStationMeasurement]:
        """Generates fallback baseline measurements for all stations."""
        return self.fallback_engine.get_all_station_measurements_fallback(hour_idx=hour_idx)
