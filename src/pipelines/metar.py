"""
NOAA Aviation Weather Center METAR Ingestion Worker.
Parses aerodrome surface meteorology for 12 airports in Punjab and transboundary corridors,
applying knots-to-m/s, statute-to-meters, metric visibility overrides, and weather tokens.
Adheres to DATA_SOURCES_AND_STREAMS.md §3.2 and DATA_PIPELINES_ARCHITECTURE.md §3.2.
"""
from datetime import datetime, timezone, timedelta
import logging
import math
import re
from typing import Any, Dict, List, Optional, Union
import httpx

from src.pipelines.base import BaseIngestionWorker
from src.pipelines.fallback_engine import FallbackTemplateEngine

logger = logging.getLogger(__name__)

# 12 Target Aerodromes
TARGET_ICAO_CODES: List[str] = [
    "OPLA",  # Allama Iqbal Intl, Lahore
    "OPFA",  # Faisalabad Intl
    "OPMT",  # Multan Intl
    "OPST",  # Sialkot Intl
    "OPIS",  # Islamabad Intl
    "OPRN",  # Benazir Bhutto (PAF Chaklala), Rawalpindi
    "OPRK",  # Shaikh Zayed Intl, Rahim Yar Khan
    "OPBW",  # Bahawalpur
    "OPDG",  # Dera Ghazi Khan
    "OPSR",  # PAF Base Mushaf, Sargodha
    "OPMI",  # PAF Base Mianwali
    "VIAR",  # Sri Guru Ram Dass Jee Intl, Amritsar (Key transboundary anchor)
]

KNOTS_TO_MS: float = 0.514444
STATUTE_MILES_TO_METERS: float = 1609.344

WEATHER_TOKEN_MAP: Dict[str, str] = {
    "FU": "Smoke",
    "HZ": "Haze",
    "BR": "Mist",
    "FG": "Fog",
    "DU": "Dust",
    "RA": "Rain",
    "TS": "Thunderstorm",
}


class MetarIngestionWorker(BaseIngestionWorker):
    """
    Ingestion client for NOAA Aviation Weather Center METAR feed.
    Base URL: https://aviationweather.gov/api/data/metar
    """

    DEFAULT_BASE_URL: str = "https://aviationweather.gov/api/data/metar"
    DEFAULT_USER_AGENT: str = "EMC-EPA-Punjab-AQ-dashboard/1.0"

    def __init__(
        self,
        base_url: Optional[str] = None,
        user_agent: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        fallback_engine: Optional[FallbackTemplateEngine] = None,
        target_airports: Optional[List[str]] = None,
        timeout: float = 20.0,
    ) -> None:
        super().__init__(
            stream_id="STR-02-METAR",
            name="NOAA AWC METAR Ingestion Worker",
            polling_cadence="10 * * * *",
            fallback_engine=fallback_engine,
        )
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.client = client
        self.target_airports = target_airports or TARGET_ICAO_CODES
        self.timeout = timeout

    async def fetch_data(
        self,
        ids: Optional[List[str]] = None,
        hours: int = 6,
        **kwargs: Any,
    ) -> Any:
        """
        Executes HTTP GET to aviationweather.gov/api/data/metar.
        """
        airport_ids = ids or self.target_airports
        params = {
            "ids": ",".join(airport_ids),
            "format": "json",
            "hours": str(hours),
        }
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }

        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout, connect=10.0),
            headers=headers,
            follow_redirects=True,
        )

        try:
            resp = await client.get(self.base_url, params=params)
            resp.raise_for_status()
            return resp.json()
        finally:
            if owns_client:
                await client.aclose()

    def parse_and_validate(
        self,
        raw_data: Any,
        target_timestamp: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Parses array of METAR reports.
        Selects reports closest to top of hour within [-35 min, +25 min] window.
        Converts knots to m/s, statute miles to meters, applies metric visibility regex,
        and decodes present weather tokens.
        """
        if not isinstance(raw_data, list):
            if isinstance(raw_data, dict) and "data" in raw_data:
                raw_data = raw_data["data"]
            else:
                raw_data = [raw_data] if isinstance(raw_data, dict) else []

        ref_time = target_timestamp or datetime.now(timezone.utc)
        if ref_time.tzinfo is None:
            ref_time = ref_time.replace(tzinfo=timezone.utc)

        # Group reports by ICAO
        reports_by_icao: Dict[str, List[Dict[str, Any]]] = {}
        for item in raw_data:
            if not isinstance(item, dict):
                continue
            icao = str(item.get("icaoId") or item.get("station_id") or "").upper()
            if not icao:
                continue
            reports_by_icao.setdefault(icao, []).append(item)

        results: List[Dict[str, Any]] = []
        for icao, reports in reports_by_icao.items():
            best_report = self._select_temporally_aligned_report(reports, ref_time)
            if best_report:
                parsed = self._parse_single_metar(best_report)
                if parsed:
                    results.append(parsed)

        return results

    def _select_temporally_aligned_report(
        self, reports: List[Dict[str, Any]], ref_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Selects report closest in time to ref_time within window [-35 min, +25 min].
        """
        min_window = ref_time - timedelta(minutes=35)
        max_window = ref_time + timedelta(minutes=25)

        valid_candidates: List[Tuple[float, Dict[str, Any]]] = []
        for r in reports:
            raw_ts = r.get("obsTime") or r.get("reportTime")
            if not raw_ts:
                continue
            try:
                if isinstance(raw_ts, (int, float)):
                    dt = datetime.fromtimestamp(raw_ts, tz=timezone.utc)
                else:
                    # Clean ISO format
                    clean_ts = str(raw_ts).replace("Z", "+00:00")
                    dt = datetime.fromisoformat(clean_ts)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                continue

            if min_window <= dt <= max_window:
                delta_sec = abs((dt - ref_time).total_seconds())
                valid_candidates.append((delta_sec, r))

        if not valid_candidates:
            # If no report strictly in window, pick the chronologically nearest available
            all_with_dt: List[Tuple[float, Dict[str, Any]]] = []
            for r in reports:
                raw_ts = r.get("obsTime") or r.get("reportTime")
                if not raw_ts:
                    continue
                try:
                    if isinstance(raw_ts, (int, float)):
                        dt = datetime.fromtimestamp(raw_ts, tz=timezone.utc)
                    else:
                        clean_ts = str(raw_ts).replace("Z", "+00:00")
                        dt = datetime.fromisoformat(clean_ts)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                    all_with_dt.append((abs((dt - ref_time).total_seconds()), r))
                except Exception:
                    continue
            if all_with_dt:
                all_with_dt.sort(key=lambda x: x[0])
                return all_with_dt[0][1]
            return None

        valid_candidates.sort(key=lambda x: x[0])
        return valid_candidates[0][1]

    def _parse_single_metar(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Decodes a single METAR object into standardized domain dictionary.
        """
        icao = str(item.get("icaoId") or item.get("station_id") or "").upper()
        obs_time = item.get("obsTime") or item.get("reportTime")
        raw_ob = str(item.get("rawOb") or "")

        # Wind direction & speed
        raw_wdir = item.get("wdir")
        raw_wspd = item.get("wspd")
        raw_wgst = item.get("wgst")

        dir_deg: Optional[float] = None
        if raw_wdir is not None:
            if str(raw_wdir).strip().upper() == "VRB":
                dir_deg = None  # Variable direction
            else:
                try:
                    val = float(raw_wdir)
                    if 0.0 <= val <= 360.0:
                        dir_deg = val
                except (ValueError, TypeError):
                    dir_deg = None

        spd_ms: Optional[float] = None
        if raw_wspd is not None:
            try:
                val = float(raw_wspd)
                if val >= 0.0:
                    spd_ms = round(val * KNOTS_TO_MS, 2)
            except (ValueError, TypeError):
                spd_ms = None

        gust_ms: Optional[float] = None
        if raw_wgst is not None:
            try:
                val = float(raw_wgst)
                if val >= 0.0:
                    gust_ms = round(val * KNOTS_TO_MS, 2)
            except (ValueError, TypeError):
                gust_ms = None

        # Wind vector (u, v) components
        u_vector: Optional[float] = None
        v_vector: Optional[float] = None
        if spd_ms is not None:
            if spd_ms < 0.5:
                # Calm wind
                u_vector = 0.0
                v_vector = 0.0
            elif dir_deg is not None:
                rad = math.radians(dir_deg)
                # Meteorological wind FROM direction: pointing vector is u = -s*sin(rad), v = -s*cos(rad)
                u_vector = round(-spd_ms * math.sin(rad), 3)
                v_vector = round(-spd_ms * math.cos(rad), 3)

        # Visibility: statute miles vs metric override
        visibility_m: Optional[float] = None
        visib_sm = item.get("visib")
        if visib_sm is not None:
            try:
                visibility_m = round(float(visib_sm) * STATUTE_MILES_TO_METERS, 1)
            except (ValueError, TypeError):
                visibility_m = None

        # Metric override from rawOb (regex: \s(\d{4})\s e.g. " 0800 ")
        if raw_ob:
            match = re.search(r"\s(\d{4})\s", raw_ob)
            if match:
                metric_val = float(match.group(1))
                if metric_val <= 9999.0:
                    visibility_m = metric_val

        # Present weather token decoding
        wx_string = str(item.get("wxString") or "").strip()
        decoded_weather: List[str] = []
        for token, desc in WEATHER_TOKEN_MAP.items():
            if token in wx_string:
                decoded_weather.append(desc)

        return {
            "icaoId": icao,
            "station_id": icao,
            "name": item.get("name") or icao,
            "obsTime": obs_time,
            "latitude": float(item.get("lat")) if item.get("lat") is not None else None,
            "longitude": float(item.get("lon")) if item.get("lon") is not None else None,
            "wind_speed_ms": spd_ms,
            "wind_direction_deg": dir_deg,
            "wind_gust_ms": gust_ms,
            "u": u_vector,
            "v": v_vector,
            "visibility_m": visibility_m,
            "raw_visibility_sm": visib_sm,
            "wx_tokens": wx_string,
            "weather_decoded": decoded_weather,
            "rawOb": raw_ob,
            "is_estimated": False,
            "source": "noaa_awc_metar",
        }

    def get_fallback(
        self,
        target_airports: Optional[List[str]] = None,
        hour_idx: int = -1,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        Generates fallback airport observations using baseline airports.json.
        """
        airports_to_use = target_airports or self.target_airports
        fallbacks: List[Dict[str, Any]] = []
        for icao in airports_to_use:
            fb = self.fallback_engine.get_airport_metar_fallback(icao, hour_idx=hour_idx)
            if fb:
                fallbacks.append(fb)
        return fallbacks
