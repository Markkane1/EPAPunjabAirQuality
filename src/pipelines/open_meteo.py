"""
ECMWF IFS Numerical Weather Prediction Ingestion Worker via Open-Meteo.
Performs multi-point centroid queries across 41 Punjab districts, extracts 10m wind fields,
and applies aerodynamic surface roughness scaling factor K_R = 0.22686.
Adheres to DATA_SOURCES_AND_STREAMS.md §3.4 and DATA_PIPELINES_ARCHITECTURE.md §3.4.
"""
from datetime import datetime, timezone
import logging
import math
from typing import Any, Dict, List, Optional, Tuple, Union
import httpx

from src.pipelines.base import BaseIngestionWorker
from src.pipelines.fallback_engine import FallbackTemplateEngine

logger = logging.getLogger(__name__)

# Official aerodynamic roughness scaling reconciliation factor (§3.4.2)
ROUGHNESS_SCALING_FACTOR: float = 0.22686
DEFAULT_FALLBACK_FACTOR: float = 0.34


class OpenMeteoIngestionWorker(BaseIngestionWorker):
    """
    Client for Open-Meteo ECMWF IFS 0.25 NWP feed across 41 district centroids.
    Base URL: https://api.open-meteo.com/v1/forecast
    """

    DEFAULT_BASE_URL: str = "https://api.open-meteo.com/v1/forecast"
    DEFAULT_USER_AGENT: str = "EMC-EPA-Punjab-AQ-dashboard/1.0"

    def __init__(
        self,
        base_url: Optional[str] = None,
        user_agent: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        fallback_engine: Optional[FallbackTemplateEngine] = None,
        roughness_k_r: float = ROUGHNESS_SCALING_FACTOR,
        timeout: float = 60.0,
    ) -> None:
        super().__init__(
            stream_id="STR-04-ECMWF-IFS",
            name="ECMWF IFS Open-Meteo Ingestion Worker",
            polling_cadence="0 * * * *",
            fallback_engine=fallback_engine,
        )
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.client = client
        self.roughness_k_r = roughness_k_r
        self.timeout = timeout

    async def fetch_data(
        self,
        centroids: Optional[List[Tuple[float, float]]] = None,
        district_names: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Executes HTTP GET for multi-point coordinates.
        Defaults to 41 district centroids from FallbackTemplateEngine.
        """
        if centroids is None:
            districts = self.fallback_engine.districts
            lat_list = [f"{d['latitude']:.4f}" for d in districts]
            lon_list = [f"{d['longitude']:.4f}" for d in districts]
        else:
            lat_list = [f"{c[0]:.4f}" for c in centroids]
            lon_list = [f"{c[1]:.4f}" for c in centroids]

        params = {
            "latitude": ",".join(lat_list),
            "longitude": ",".join(lon_list),
            "hourly": "wind_speed_10m,wind_direction_10m",
            "models": "ecmwf_ifs025",
            "wind_speed_unit": "ms",
            "timezone": "Asia/Karachi",
            "past_days": "1",
            "forecast_days": "1",
        }
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }

        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout, connect=15.0),
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
        district_names: Optional[List[str]] = None,
        hour_index: int = -1,
    ) -> List[Dict[str, Any]]:
        """
        Parses Open-Meteo response array/object.
        Applies roughness scaling: w_calibrated = K_R * w_ECMWF.
        Calculates (u, v) vectors.
        """
        data_list: List[Dict[str, Any]] = []
        if isinstance(raw_data, list):
            data_list = raw_data
        elif isinstance(raw_data, dict):
            data_list = [raw_data]

        names = district_names or [d["name"] for d in self.fallback_engine.districts]
        results: List[Dict[str, Any]] = []

        for idx, item in enumerate(data_list):
            dname = names[idx] if idx < len(names) else f"District_{idx}"
            hourly = item.get("hourly", {})
            speeds = hourly.get("wind_speed_10m", [])
            dirs = hourly.get("wind_direction_10m", [])
            times = hourly.get("time", [])

            # Determine hour index (default: latest or specified)
            target_idx = hour_index if 0 <= hour_index < len(speeds) else (len(speeds) - 1 if speeds else 0)

            spd = float(speeds[target_idx]) if target_idx < len(speeds) else 0.0
            deg = float(dirs[target_idx]) if target_idx < len(dirs) else 0.0
            time_str = times[target_idx] if target_idx < len(times) else ""

            # Decompose into raw (u, v)
            if spd < 0.5:
                u_raw = 0.0
                v_raw = 0.0
            else:
                rad = math.radians(deg)
                u_raw = -spd * math.sin(rad)
                v_raw = -spd * math.cos(rad)

            # Apply aerodynamic surface roughness scaling
            u_calibrated = round(u_raw * self.roughness_k_r, 4)
            v_calibrated = round(v_raw * self.roughness_k_r, 4)
            spd_calibrated = round(spd * self.roughness_k_r, 3)

            results.append({
                "district": dname,
                "timestamp": time_str,
                "wind_speed_raw_ms": spd,
                "wind_direction_deg": deg,
                "wind_speed_calibrated_ms": spd_calibrated,
                "u_calibrated": u_calibrated,
                "v_calibrated": v_calibrated,
                "roughness_factor": self.roughness_k_r,
                "is_estimated": False,
                "source": "ecmwf_open_meteo",
            })

        return results

    def get_fallback(self, hour_idx: int = -1, **kwargs: Any) -> List[Dict[str, Any]]:
        """Generates fallback district forecasts from baseline data."""
        return self.fallback_engine.get_open_meteo_fallback(hour_idx=hour_idx)
