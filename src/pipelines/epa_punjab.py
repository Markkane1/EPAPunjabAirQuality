"""
EPA Punjab Live Feed Ingestion Worker.
Queries provincial AQMS dashboard API with custom User-Agent, exponential retry/backoff,
district fallback fan-out, and graceful baseline failover.
Adheres to DATA_SOURCES_AND_STREAMS.md §3.1 and DATA_PIPELINES_ARCHITECTURE.md §3.1.
"""
import asyncio
import logging
import random
from typing import Any, Dict, List, Optional, Union
import httpx

from src.domain.schemas.measurement import RawStationMeasurement
from src.pipelines.base import BaseIngestionWorker
from src.pipelines.fallback_engine import FallbackTemplateEngine, EXCLUDED_STATIONS

logger = logging.getLogger(__name__)


class EPAPunjabIngestionWorker(BaseIngestionWorker):
    """
    Client for Environmental Protection Agency, Government of the Punjab.
    Base URL: https://aqi.punjab.gov.pk
    """

    DEFAULT_BASE_URL: str = "https://aqi.punjab.gov.pk"
    DEFAULT_USER_AGENT: str = "EMC-EPA-Punjab-AQ-dashboard/1.0"

    def __init__(
        self,
        base_url: Optional[str] = None,
        user_agent: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        fallback_engine: Optional[FallbackTemplateEngine] = None,
        timeout: float = 30.0,
    ) -> None:
        super().__init__(
            stream_id="STR-01-EPAPUNJAB",
            name="EPA Punjab AQMS Live Feed Worker",
            polling_cadence="5,15 * * * *",
            fallback_engine=fallback_engine,
        )
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.client = client
        self.timeout = timeout
        self.retry_delays = [2.0, 8.0, 20.0]

    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }

    async def fetch_data(self, endpoint: str = "/api/dashboard/current", **kwargs: Any) -> Any:
        """
        Executes HTTP GET against EPA Punjab portal with 3 retries (2s, 8s, 20s +/- 20% jitter).
        """
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
                    response = await client.get(url)
                    response.raise_for_status()
                    return response.json()
                except (httpx.HTTPStatusError, httpx.RequestError, ValueError) as exc:
                    last_exception = exc
                    if attempt < len(self.retry_delays):
                        jitter = delay * (0.8 + 0.4 * random.random())
                        logger.warning(
                            "EPA Punjab request failed (attempt %d/%d): %s. Retrying in %.2fs...",
                            attempt,
                            len(self.retry_delays),
                            exc,
                            jitter,
                        )
                        await asyncio.sleep(jitter)
                    else:
                        logger.error("EPA Punjab all %d retry attempts exhausted.", len(self.retry_delays))
            if last_exception:
                raise last_exception
            raise RuntimeError("Unknown error during EPA Punjab data fetch")
        finally:
            if owns_client:
                await client.aclose()

    async def fan_out_missing_districts(
        self, missing_districts: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Asynchronously queries /api/district-stations/{name} for omitted tehsils or districts.
        Uses Semaphore(10) concurrency with 3s per-district timeout. Aborts on 3 consecutive timeouts.
        """
        if not missing_districts:
            return []

        semaphore = asyncio.Semaphore(10)
        timeout_budget = 3.0
        consecutive_timeouts = 0
        supplementary_stations: List[Dict[str, Any]] = []

        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_budget, connect=2.0),
            headers=self._get_headers(),
            follow_redirects=True,
        )

        async def _query_single_district(district_name: str) -> Optional[List[Dict[str, Any]]]:
            nonlocal consecutive_timeouts
            if consecutive_timeouts >= 3:
                return None
            async with semaphore:
                try:
                    url = f"{self.base_url}/api/district-stations/{district_name}"
                    resp = await client.get(url)
                    resp.raise_for_status()
                    data = resp.json()
                    consecutive_timeouts = 0
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict) and "data" in data:
                        return data["data"]
                    return None
                except asyncio.TimeoutError:
                    consecutive_timeouts += 1
                    logger.warning("District fan-out timed out for %s (streak=%d)", district_name, consecutive_timeouts)
                    return None
                except Exception as exc:
                    logger.debug("District fan-out skipped for %s: %s", district_name, exc)
                    return None

        try:
            tasks = [_query_single_district(d) for d in missing_districts]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, list):
                    supplementary_stations.extend(res)
            return supplementary_stations
        finally:
            if owns_client:
                await client.aclose()

    def parse_and_validate(self, raw_data: Any) -> List[RawStationMeasurement]:
        """
        Parses JSON response into RawStationMeasurement models.
        Excludes unlocatable stations (OneNetwork Station 25) and enforces Pydantic contracts.
        """
        station_list: List[Dict[str, Any]] = []
        if isinstance(raw_data, list):
            station_list = raw_data
        elif isinstance(raw_data, dict):
            station_list = raw_data.get("data", [])
            if not station_list and "stations" in raw_data:
                station_list = raw_data.get("stations", [])
        else:
            raise ValueError(f"Unexpected EPA Punjab payload type: {type(raw_data)}")

        validated: List[RawStationMeasurement] = []
        for item in station_list:
            if not isinstance(item, dict):
                continue

            s_name = str(item.get("station_name") or item.get("name") or "").strip()
            s_id = str(item.get("station_id") or item.get("id") or "").strip()

            # Exclusion rule: OneNetwork Station 25 lacks verifiable coordinates
            lower_name = s_name.lower()
            lower_id = s_id.lower()
            if any(exc in lower_name or exc in lower_id for exc in EXCLUDED_STATIONS):
                logger.debug("Excluding station from EPA payload: %s (id: %s)", s_name, s_id)
                continue

            # Standardize payload keys
            payload = dict(item)
            if "name" in payload and "station_name" not in payload:
                payload["station_name"] = payload["name"]
            if "id" in payload and "station_id" not in payload:
                payload["station_id"] = payload["id"]

            try:
                meas = RawStationMeasurement(**payload)
                validated.append(meas)
            except Exception as e:
                logger.warning("Dropped invalid station record %s: %s", s_name, e)

        return validated

    def get_fallback(self, hour_idx: int = -1, **kwargs: Any) -> List[RawStationMeasurement]:
        """Generates fallback baseline measurements for all stations."""
        return self.fallback_engine.get_all_station_measurements_fallback(hour_idx=hour_idx)
