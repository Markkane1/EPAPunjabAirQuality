"""
EPA Punjab Air Quality Monitoring, Processing, and Visualization System.
Canonical Domain Normalizer Engine addressing all 5 Schema Traps:

1. Centroid Inversion: Inverts [latitude, longitude] to [longitude, latitude] for map engines
   while preserving already-projected label coordinates and GeoJSON boundary rings.
2. Aerodrome Wind Discrimination: Differentiates null telemetry dropout from calm (0.0 <= ws < 0.50 m/s)
   and active advection vectors.
3. Station 172 Blacklist: Hard-blocks wind rendering for Wazirabad (140 deg vane offset).
4. Dynamic Network Station Counts: Evaluates fixed (74) vs mobile (5) station inventory.
5. Unified Estimation Flag: Standardizes est / is_monitored into is_estimated and flags diagonal cross-hatching.
"""
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from src.domain.math.wind import WIND_BLACKLIST_STATIONS, is_station_blacklisted


def is_blacklisted_station(station_id_or_name: Optional[Union[str, int]]) -> bool:
    """Checks if a station is blacklisted for wind measurements (Schema Trap 3)."""
    return is_station_blacklisted(station_id_or_name)


def blacklist_banner_text(station: Optional[Union[Dict[str, Any], str, int]]) -> Optional[str]:
    """Returns warning banner text if station anemometer is blacklisted."""
    if station is None:
        return None
    if isinstance(station, dict):
        sid = station.get("id") or station.get("station_id") or station.get("numeric_id")
        sname = station.get("name")
        if is_station_blacklisted(sid) or is_station_blacklisted(sname):
            return "ANEMOMETER BLACKLISTED (VANE OFFSET)"
        return None
    if is_station_blacklisted(station):
        return "ANEMOMETER BLACKLISTED (VANE OFFSET)"
    return None


def normalize_centroid(centroid: Union[Sequence[float], Tuple[float, float], List[float]]) -> Tuple[float, float]:
    """
    Trap 1: Inverts raw district centroid [latitude, longitude] to canonical [longitude, latitude].
    Notice: In South Asia (lat ~27-35, lon ~68-76), if first <= 45 and second > 45,
    input is [lat, lon] -> inverts to (lon, lat).
    If first > 45 and second <= 45, input is already [lon, lat] -> returns (first, second).
    """
    if not centroid or len(centroid) < 2:
        return (0.0, 0.0)
    try:
        first = float(centroid[0])
        second = float(centroid[1])
    except (ValueError, TypeError):
        return (0.0, 0.0)

    if math.isnan(first) or math.isnan(second):
        return (0.0, 0.0)

    if abs(first) <= 45.0 and abs(second) > 45.0:
        return (second, first)
    return (first, second)


def normalize_wind(
    speed: Optional[float],
    direction: Optional[float],
    station_id_or_name: Optional[Union[str, int]] = None,
) -> Dict[str, Any]:
    """
    Trap 2 & Trap 3: Canonical wind vector normalizer.
    - Station 172 (Wazirabad) -> 'blacklisted'
    - Null / NaN / Inf / out-of-range (< 0 or > 30 m/s) -> 'dropout'
    - 0.0 <= speed < 0.50 m/s -> 'calm'
    - speed >= 0.50 m/s -> 'active'
    """
    # Check Trap 3: Station 172 Wazirabad Blacklist
    if is_station_blacklisted(station_id_or_name):
        return {
            "state": "blacklisted",
            "speed": None,
            "direction": None,
            "u": None,
            "v": None,
            "blacklisted": True,
            "blacklist_reason": "ANEMOMETER BLACKLISTED (VANE OFFSET)",
        }

    # Check Trap 2: Telemetry Dropout (null, NaN, Inf, or non-physical speed)
    if (
        speed is None
        or direction is None
        or math.isnan(speed)
        or math.isnan(direction)
        or math.isinf(speed)
        or math.isinf(direction)
        or speed < 0.0
        or speed > 30.0
        or direction < 0.0
        or direction > 360.0
    ):
        return {
            "state": "dropout",
            "speed": None,
            "direction": None,
            "u": None,
            "v": None,
            "blacklisted": False,
        }

    # Check Trap 2: Aerodynamic Calm (< 0.50 m/s)
    if speed < 0.50:
        return {
            "state": "calm",
            "speed": round(speed, 2),
            "direction": round(direction, 1),
            "u": 0.0,
            "v": 0.0,
            "blacklisted": False,
        }

    # Active Advection Vector:
    # Meteorological azimuth: direction wind blows FROM (0=N, 90=E, 180=S, 270=W).
    # Vector (u, v) points in direction air mass travels TO:
    # u = -speed * sin(direction * pi / 180)
    # v = -speed * cos(direction * pi / 180)
    rad = math.radians(direction)
    u = -speed * math.sin(rad)
    v = -speed * math.cos(rad)

    return {
        "state": "active",
        "speed": round(speed, 2),
        "direction": round(direction, 1),
        "u": 0.0 if abs(u) < 1e-12 else round(u, 4),
        "v": 0.0 if abs(v) < 1e-12 else round(v, 4),
        "blacklisted": False,
    }


def is_district_estimated(district: Optional[Dict[str, Any]]) -> bool:
    """
    Trap 5: Unifies district estimation flags into canonical is_estimated: bool.
    True if est: true, is_estimated: true, or is_monitored: false.
    """
    if not district:
        return True
    if "is_estimated" in district and isinstance(district["is_estimated"], bool):
        return district["is_estimated"]
    if "isEstimated" in district and isinstance(district["isEstimated"], bool):
        return district["isEstimated"]
    if district.get("is_monitored") is False:
        return True
    if district.get("est") is True:
        return True
    if district.get("station_count") == 0:
        return True
    return False


def should_apply_diagonal_hatching(district: Optional[Dict[str, Any]]) -> bool:
    """Determines whether diagonal cross-hatching styling must be applied (Trap 5)."""
    return is_district_estimated(district)


def count_station_networks(stations: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    """
    Trap 4: Dynamically counts station inventory breakdown (fixed vs mobile).
    """
    fixed = 0
    mobile = 0

    for st in stations:
        is_mobile = (
            st.get("mobile") is True
            or st.get("station_type") == "mobile"
            or st.get("network_type") == "mobile"
            or "mobile" in str(st.get("name", "")).lower()
        )
        if is_mobile:
            mobile += 1
        else:
            fixed += 1

    return {"fixed": fixed, "mobile": mobile, "total": fixed + mobile}
