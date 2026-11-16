"""
Stream 8: Planetary Boundary Layer (PBL) / Mixing Layer Height Ingestion Worker.
Queries ECMWF IFS / Open-Meteo boundary_layer_height across 41 district centroids.
Computes Atmospheric Ventilation Index (VI = h_PBL * w_sfc) and classifies statutory dispersion risk.
Adheres to DATA_SOURCES_AND_STREAMS.md §3.8 and TRANSFORMATION_LOGIC_SPEC.md §Transformation 11.
"""
from datetime import datetime, timezone
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

import httpx

from src.domain.math.pbl import (
    calculate_and_classify_vi,
    classify_ventilation_index,
    calculate_ventilation_index,
    DISPERSION_CRITICAL_TRAP,
    DISPERSION_POOR,
    DISPERSION_MODERATE,
    DISPERSION_GOOD,
    NOVEMBER_CLIMATOLOGICAL_PBL_PKT,
)
from src.domain.schemas.pbl import PBLObservation
from src.pipelines.base import BaseIngestionWorker
from src.pipelines.fallback_engine import FallbackTemplateEngine

logger = logging.getLogger(__name__)


class PBLIngestionWorker(BaseIngestionWorker):
    """
    Ingestion Worker for Stream 8 (Planetary Boundary Layer / Mixing Height).
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
        timeout: float = 60.0,
    ) -> None:
        super().__init__(
            stream_id="STR-08-PBL",
            name="ECMWF Open-Meteo PBL Mixing Height Worker",
            polling_cadence="0 * * * *",
            fallback_engine=fallback_engine,
        )
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.client = client
        self.timeout = timeout

    async def fetch_data(
        self,
        centroids: Optional[List[Tuple[float, float]]] = None,
        district_names: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Executes HTTP GET for multi-point boundary_layer_height and wind_speed_10m.
        Defaults to 41 district centroids.
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
            "hourly": "boundary_layer_height,wind_speed_10m",
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
        Parses Open-Meteo PBL JSON payload.
        Computes Atmospheric Ventilation Index (VI) and assigns statutory dispersion categories.
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
            pbl_series = hourly.get("boundary_layer_height", [])
            wspd_series = hourly.get("wind_speed_10m", [])
            time_series = hourly.get("time", [])

            # Select target hour
            target_idx = hour_index if 0 <= hour_index < len(pbl_series) else (len(pbl_series) - 1 if pbl_series else 0)

            pbl_h = float(pbl_series[target_idx]) if target_idx < len(pbl_series) and pbl_series[target_idx] is not None else 200.0
            w_sfc = float(wspd_series[target_idx]) if target_idx < len(wspd_series) and wspd_series[target_idx] is not None else 1.5
            time_str = time_series[target_idx] if target_idx < len(time_series) else datetime.now(timezone.utc).isoformat()

            # Enforce non-negative bounds
            pbl_h = max(0.0, pbl_h)
            w_sfc = max(0.0, w_sfc)

            vi, category, color = calculate_and_classify_vi(pbl_h, w_sfc)

            record = {
                "district": dname,
                "timestamp": time_str,
                "boundary_layer_height": round(pbl_h, 1),
                "surface_wind_speed": round(w_sfc, 2),
                "ventilation_index": vi,
                "dispersion_category": category,
                "dispersion_color": color,
                "is_critical_trap": vi < 2000.0,
                "is_estimated": False,
                "source": "ecmwf_open_meteo",
            }
            results.append(record)

        return results

    def get_fallback(
        self,
        hour_pkt: Optional[int] = None,
        district_names: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        Generates fallback PBL mixing heights and ventilation index using November climatology.
        """
        if hour_pkt is None:
            now_utc = datetime.now(timezone.utc)
            hour_pkt = (now_utc.hour + 5) % 24

        climatological_h = NOVEMBER_CLIMATOLOGICAL_PBL_PKT[hour_pkt % 24]
        names = district_names or [d["name"] for d in self.fallback_engine.districts]
        fallback_time = datetime.now(timezone.utc).isoformat()

        results: List[Dict[str, Any]] = []
        for dname in names:
            # Baseline typical winter breeze ~1.5 m/s
            w_sfc = 1.5
            vi, category, color = calculate_and_classify_vi(climatological_h, w_sfc)

            results.append({
                "district": dname,
                "timestamp": fallback_time,
                "boundary_layer_height": climatological_h,
                "surface_wind_speed": w_sfc,
                "ventilation_index": vi,
                "dispersion_category": category,
                "dispersion_color": color,
                "is_critical_trap": vi < 2000.0,
                "is_estimated": True,
                "source": "climatology_fallback",
            })

        return results
