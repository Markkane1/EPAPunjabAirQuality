"""
World Meteorological Organization (WMO) FM-12 SYNOP Decoder.
Parses telegraphic synoptic telegrams (AAXX) from Ogimet gateway for WMO blocks 415, 416, 417.
Implements telegraphic decoding, 65s HTTP 429 rate limit backoff floor, and fallback failover.
Adheres to DATA_SOURCES_AND_STREAMS.md §3.3.
"""
from datetime import datetime, timezone
import logging
import math
import re
from typing import Any, Dict, List, Optional
import httpx

from src.pipelines.base import BaseIngestionWorker
from src.pipelines.fallback_engine import FallbackTemplateEngine, WMO_FALLBACK_MAP

logger = logging.getLogger(__name__)

TARGET_WMO_BLOCKS: List[str] = ["415", "416", "417"]

MONITORED_WMO_STATIONS: Dict[str, Dict[str, Any]] = {
    "41640": {"name": "Lahore PBO", "lat": 31.550, "lon": 74.330, "elev": 214, "block": "416"},
    "41641": {"name": "Lahore Airport", "lat": 31.520, "lon": 74.400, "elev": 217, "block": "416"},
    "41571": {"name": "Islamabad", "lat": 33.620, "lon": 73.100, "elev": 540, "block": "415"},
    "41598": {"name": "Jhelum", "lat": 32.930, "lon": 73.720, "elev": 234, "block": "415"},
    "41600": {"name": "Sialkot", "lat": 32.500, "lon": 74.530, "elev": 256, "block": "416"},
    "41675": {"name": "Multan", "lat": 30.200, "lon": 71.430, "elev": 124, "block": "416"},
    "41700": {"name": "Bahawalpur", "lat": 29.400, "lon": 71.680, "elev": 116, "block": "417"},
}

KNOTS_TO_MS: float = 0.514444


class SynopIngestionWorker(BaseIngestionWorker):
    """
    Ingestion client and FM-12 AAXX telegraphic decoder for Ogimet WMO SYNOP feed.
    Base URL: https://www.ogimet.com/cgi-bin/getsynop
    """

    DEFAULT_BASE_URL: str = "https://www.ogimet.com/cgi-bin/getsynop"
    DEFAULT_USER_AGENT: str = "EMC-EPA-Punjab-AQ-dashboard/1.0"
    RATE_LIMIT_BACKOFF_FLOOR: float = 65.0  # Mandatory 65s floor to prevent IP bans

    def __init__(
        self,
        base_url: Optional[str] = None,
        user_agent: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        fallback_engine: Optional[FallbackTemplateEngine] = None,
        blocks: Optional[List[str]] = None,
        timeout: float = 30.0,
    ) -> None:
        super().__init__(
            stream_id="STR-03-SYNOP",
            name="WMO FM-12 SYNOP Ingestion Worker",
            polling_cadence="15 * * * *",
            fallback_engine=fallback_engine,
        )
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.client = client
        self.blocks = blocks or TARGET_WMO_BLOCKS
        self.timeout = timeout

    async def fetch_data(
        self,
        block: Optional[str] = None,
        begin_str: Optional[str] = None,
        end_str: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """
        Executes HTTP GET for raw SYNOP lines.
        Enforces 65-second minimum backoff floor on HTTP 429.
        """
        now = datetime.now(timezone.utc)
        target_block = block or self.blocks[0]
        b_str = begin_str or (now.strftime("%Y%m%d%H00"))
        e_str = end_str or (now.strftime("%Y%m%d%H59"))

        params = {
            "block": target_block,
            "begin": b_str,
            "end": e_str,
        }
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/plain, */*",
        }

        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout, connect=10.0),
            headers=headers,
            follow_redirects=True,
        )

        try:
            resp = await client.get(self.base_url, params=params)
            if resp.status_code == 429:
                logger.error("Ogimet returned HTTP 429 Too Many Requests. Enforcing %.0fs backoff floor.", self.RATE_LIMIT_BACKOFF_FLOOR)
                raise httpx.HTTPStatusError("HTTP 429 Too Many Requests from Ogimet", request=resp.request, response=resp)
            resp.raise_for_status()
            return resp.text
        finally:
            if owns_client:
                await client.aclose()

    def decode_synop_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Decodes a single FM-12 AAXX telegraphic line into domain parameters:
        AAXX 09184 41640 11560 81802 10224 20182 40162 57018 70582 8536/ 333 55300 20000=
        """
        if "AAXX" not in line:
            return None

        # Clean line and split tokens
        clean_line = line.replace("=", "").strip()
        tokens = clean_line.split()
        if "AAXX" not in tokens:
            return None

        aaxx_idx = tokens.index("AAXX")
        # Ensure sufficient trailing tokens
        if len(tokens) <= aaxx_idx + 4:
            return None

        # Token 1: YYGGiw (e.g. 09184 -> Day 09, Hour 18, iw = 4)
        header_token = tokens[aaxx_idx + 1]
        iw = int(header_token[-1]) if header_token and header_token[-1].isdigit() else 1

        # Token 2: IIiii (WMO station ID, e.g. 41640)
        station_token = tokens[aaxx_idx + 2]
        wmo_id = str(station_token).strip()

        # Search for wind group: Nddff
        # Usually token at index aaxx_idx + 4
        # Format: 5 digits where dd in [00..36, 99], ff in [00..99]
        wind_speed_ms: Optional[float] = None
        wind_direction_deg: Optional[float] = None
        temp_c: Optional[float] = None
        dewpoint_c: Optional[float] = None

        # Scan section 1 groups (up to '333' or end)
        sec1_tokens: List[str] = []
        for t in tokens[aaxx_idx + 3:]:
            if t == "333" or t == "555":
                break
            sec1_tokens.append(t)

        # Inspect token 1 of sec1 (which is token index 4 overall) for Nddff
        if len(sec1_tokens) >= 2:
            wind_group = sec1_tokens[1]
            if len(wind_group) == 5 and wind_group.isdigit():
                # N = wind_group[0]
                dd = int(wind_group[1:3])
                ff = int(wind_group[3:5])

                # Check auxiliary group 00fff in section 3 if ff == 99
                if ff == 99:
                    aux_match = re.search(r"\b00(\d{3})\b", clean_line)
                    if aux_match:
                        ff = int(aux_match.group(1))

                # Direction decoding
                if 1 <= dd <= 36:
                    wind_direction_deg = float(dd * 10)
                elif dd == 0:
                    wind_direction_deg = None  # Calm
                else:  # 99 variable
                    wind_direction_deg = None

                # Speed decoding based on iw
                if iw in (3, 4):  # knots
                    wind_speed_ms = round(ff * KNOTS_TO_MS, 2)
                else:  # m/s
                    wind_speed_ms = float(ff)

        # Temperature group: 1snTTT (occurs in section 1 strictly after Nddff, so sec1_tokens[2:])
        for t in sec1_tokens[2:]:
            if len(t) == 5 and t.startswith("1") and t[1:].isdigit():
                sn = int(t[1])
                ttt = int(t[2:5])
                val = ttt / 10.0
                temp_c = -val if sn == 1 else val
                break

        # Dewpoint group: 2snTdTdTd (occurs in section 1 strictly after Nddff, so sec1_tokens[2:])
        for t in sec1_tokens[2:]:
            if len(t) == 5 and t.startswith("2") and t[1:].isdigit():
                sn = int(t[1])
                td = int(t[2:5])
                val = td / 10.0
                dewpoint_c = -val if sn == 1 else val
                break

        # Calculate Cartesian (u, v)
        u_vector: Optional[float] = None
        v_vector: Optional[float] = None
        if wind_speed_ms is not None:
            if wind_speed_ms < 0.5:
                u_vector = 0.0
                v_vector = 0.0
            elif wind_direction_deg is not None:
                rad = math.radians(wind_direction_deg)
                u_vector = round(-wind_speed_ms * math.sin(rad), 3)
                v_vector = round(-wind_speed_ms * math.cos(rad), 3)

        meta = MONITORED_WMO_STATIONS.get(wmo_id, {
            "name": f"WMO-{wmo_id}",
            "lat": None,
            "lon": None,
            "elev": None,
            "block": wmo_id[:3] if len(wmo_id) >= 3 else "",
        })

        return {
            "wmo_id": wmo_id,
            "station_name": meta["name"],
            "latitude": meta["lat"],
            "longitude": meta["lon"],
            "elevation_m": meta["elev"],
            "block": meta["block"],
            "wind_speed_ms": wind_speed_ms,
            "wind_direction_deg": wind_direction_deg,
            "u": u_vector,
            "v": v_vector,
            "temperature_c": temp_c,
            "dewpoint_c": dewpoint_c,
            "raw_telegram": clean_line,
            "is_estimated": False,
            "source": "ogimet_wmo_synop",
        }

    def parse_and_validate(self, raw_data: Any) -> List[Dict[str, Any]]:
        """
        Parses text payload into decoded SYNOP observations.
        """
        if not isinstance(raw_data, str):
            if isinstance(raw_data, bytes):
                raw_data = raw_data.decode("utf-8", errors="ignore")
            else:
                return []

        observations: List[Dict[str, Any]] = []
        for line in raw_data.splitlines():
            line_str = line.strip()
            if not line_str or "AAXX" not in line_str:
                continue
            decoded = self.decode_synop_line(line_str)
            if decoded:
                observations.append(decoded)

        return observations

    def get_fallback(
        self,
        wmo_ids: Optional[List[str]] = None,
        hour_idx: int = -1,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        Generates schema-conforming SYNOP fallback records using baseline data.
        """
        target_ids = wmo_ids or list(MONITORED_WMO_STATIONS.keys())
        fallbacks: List[Dict[str, Any]] = []
        for wid in target_ids:
            fb = self.fallback_engine.get_synop_fallback(wid, hour_idx=hour_idx)
            if fb:
                fallbacks.append(fb)
        return fallbacks
