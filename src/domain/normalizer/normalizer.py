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


# --- GAP-GEO-03: Automated Shapefile & Geometric Coordinate Sanitizer ---

PUNJAB_PROVINCIAL_BOUNDS = {
    "lat_min": 27.5,
    "lat_max": 34.5,
    "lon_min": 69.0,
    "lon_max": 75.8,
}

CANONICAL_COORDINATES: Dict[str, Tuple[float, float]] = {
    "gulberg iii": (31.5097, 74.3478),
    "dc office sialkot": (32.4945, 74.5372),
    "wazirabad": (32.4428, 74.1197),
    "sahiwal": (30.6682, 73.1114),
    "rajanpur": (29.1044, 70.3297),
    "talagang": (32.9283, 72.4189),
    "khushab": (32.2955, 72.3522),
    "safari park-lhr": (31.3821, 74.2238),
}


def is_point_in_polygon(lat: float, lon: float, polygon_coords: Sequence[Sequence[float]]) -> bool:
    """
    Standard ray-casting algorithm to test whether a (lat, lon) point lies within a polygon.
    Handles both [lon, lat] and [lat, lon] rings automatically.
    """
    if not polygon_coords or len(polygon_coords) < 3:
        return False

    pts: List[Tuple[float, float]] = []
    for p in polygon_coords:
        if len(p) >= 2:
            x, y = float(p[0]), float(p[1])
            if x <= 45.0 and y > 45.0:  # [lat, lon]
                pts.append((y, x))
            else:  # [lon, lat]
                pts.append((x, y))

    inside = False
    n = len(pts)
    px, py = lon, lat
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        if ((y1 > py) != (y2 > py)) and (px < (x2 - x1) * (py - y1) / (y2 - y1 + 1e-12) + x1):
            inside = not inside
    return inside


def sanitize_station_coordinates(
    station_name_or_id: str,
    lat: float,
    lon: float,
    boundary: Optional[Sequence[Sequence[float]]] = None,
) -> Tuple[float, float, bool]:
    """
    Automated Shapefile & Telemetry Coordinate Sanitizer (GAP-GEO-03).
    1. Checks if station name matches known shapefile coordinate traps (e.g. Wazirabad in India,
       Gulberg III offset 35 km south). If so, returns authoritative rectified coordinates.
    2. Detects and corrects centroid inversion where latitude and longitude were transposed.
    3. Verifies coordinates against provincial bounding box (27.5-34.5 N, 69.0-75.8 E).
    4. If boundary polygon is provided, verifies point containment.
    Returns: (sanitized_lat, sanitized_lon, was_rectified)
    """
    normalized_name = str(station_name_or_id).strip().lower()
    for key, (c_lat, c_lon) in CANONICAL_COORDINATES.items():
        if key in normalized_name:
            return (c_lat, c_lon, True)

    was_rectified = False
    # Centroid inversion trap check: if lat > 45 and lon <= 45
    if lat > 45.0 and lon <= 45.0:
        lat, lon = lon, lat
        was_rectified = True

    # Check provincial bounding box
    if not (
        PUNJAB_PROVINCIAL_BOUNDS["lat_min"] <= lat <= PUNJAB_PROVINCIAL_BOUNDS["lat_max"]
        and PUNJAB_PROVINCIAL_BOUNDS["lon_min"] <= lon <= PUNJAB_PROVINCIAL_BOUNDS["lon_max"]
    ):
        was_rectified = True

    # Check boundary polygon if supplied
    if boundary and not is_point_in_polygon(lat, lon, boundary):
        was_rectified = True

    return (lat, lon, was_rectified)
