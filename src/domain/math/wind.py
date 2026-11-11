"""
Meteorological Wind Kinematics and QC Validation.
Implements polar-to-Cartesian (u, v) and Cartesian-to-polar conversions,
anemometer physical boundary validation, and Wazirabad hardware offset blacklisting.
Zero external framework dependencies (standard library and math only).
"""
import math
from typing import Any, Dict, List, Optional, Set, Tuple

# Physical Anemometer Quality Control Limits (TRANSFORMATION_LOGIC_SPEC.md §2.4.0)
MIN_WIND_SPEED_MS: float = 0.0
MAX_WIND_SPEED_MS: float = 30.0  # 108 km/h upper physical bound for surface stations
MIN_WIND_DIR_DEG: float = 0.0
MAX_WIND_DIR_DEG: float = 360.0
CALM_WIND_THRESHOLD_MS: float = 0.5  # Aerodynamic calm cutoff

# Stations with persistent mechanical/sensor offsets blacklisted from wind analysis
# Wazirabad AQMS anemometer has an uncalibrated 140 degree hardware vane offset
WIND_BLACKLIST_STATIONS: Set[str] = {
    "wazirabad",
    "wazirabad aqms",
    "pk_waz_001",
    "wazirabad station",
}


def is_station_blacklisted(station_name: Optional[str]) -> bool:
    """
    Checks if a station is blacklisted for wind measurements (e.g. Wazirabad).
    """
    if not station_name:
        return False
    normalized = station_name.strip().lower()
    if normalized in WIND_BLACKLIST_STATIONS:
        return True
    return "wazirabad" in normalized


def is_anemometer_valid(
    speed_ms: Optional[float],
    dir_deg: Optional[float],
    station_name: Optional[str] = None,
) -> bool:
    """
    Validates anemometer measurement against physical bounds and station blacklists.
    (TRANSFORMATION_LOGIC_SPEC.md §2.4.0).
    
    Returns False if:
    - Values are None, NaN, or Infinite
    - Speed is outside [0.0, 30.0] m/s (filters error code 99.9 or dir in speed field)
    - Direction is outside [0.0, 360.0] degrees
    - Station is blacklisted (Wazirabad 140 deg offset)
    """
    if speed_ms is None or dir_deg is None:
        return False
    if math.isnan(speed_ms) or math.isnan(dir_deg):
        return False
    if math.isinf(speed_ms) or math.isinf(dir_deg):
        return False

    if not (MIN_WIND_SPEED_MS <= speed_ms <= MAX_WIND_SPEED_MS):
        return False
    if not (MIN_WIND_DIR_DEG <= dir_deg <= MAX_WIND_DIR_DEG):
        return False

    if is_station_blacklisted(station_name):
        return False

    return True


def is_calm_wind(speed_ms: Optional[float], calm_threshold: float = CALM_WIND_THRESHOLD_MS) -> bool:
    """
    Determines whether wind speed is classified as aerodynamic calm (<0.5 m/s).
    """
    if speed_ms is None or math.isnan(speed_ms):
        return True
    return speed_ms < calm_threshold


def polar_to_cartesian_wind(
    speed_ms: Optional[float],
    dir_deg: Optional[float],
    station_name: Optional[str] = None,
) -> Optional[Tuple[float, float]]:
    """
    Converts polar meteorological wind report (speed, direction FROM) into
    Cartesian kinematic advection flow vectors (u, v) in m/s (TRANSFORMATION_LOGIC_SPEC.md §2.4.2).
    
    Meteorological Convention:
        dir_deg is azimuth the wind blows FROM (0=North, 90=East, 180=South, 270=West).
        The advection vector (u, v) points in the direction the air mass travels TO:
        u = -speed * sin(dir * pi / 180)  (eastward positive)
        v = -speed * cos(dir * pi / 180)  (northward positive)
        
    Returns:
        (u, v) tuple in m/s, or None if inputs fail quality control.
    """
    if not is_anemometer_valid(speed_ms, dir_deg, station_name):
        return None

    # Handle calm case explicitly to avoid -0.0
    if speed_ms == 0.0:
        return (0.0, 0.0)

    theta_rad = math.radians(dir_deg)
    u = -speed_ms * math.sin(theta_rad)
    v = -speed_ms * math.cos(theta_rad)

    # Clean near-zero floating point values
    if abs(u) < 1e-12:
        u = 0.0
    if abs(v) < 1e-12:
        v = 0.0

    return (u, v)


def cartesian_to_polar_wind(u: float, v: float) -> Tuple[float, float]:
    """
    Reconstructs scalar wind speed (m/s) and meteorological direction FROM (deg)
    from Cartesian flow velocity components (u, v) (TRANSFORMATION_LOGIC_SPEC.md §2.4.2).
    
    Formula:
        speed = sqrt(u^2 + v^2)
        direction_from = (degrees(atan2(-u, -v)) + 360) mod 360
    """
    speed = math.sqrt(u * u + v * v)
    if speed == 0.0:
        return (0.0, 0.0)

    direction = (math.degrees(math.atan2(-u, -v)) + 360.0) % 360.0
    return (speed, direction)


def wind_direction_to_bearing(u: float, v: float) -> float:
    """
    Computes azimuth angle the advection vector is blowing TO (degrees clockwise from North).
    Formula: (degrees(atan2(u, v)) + 360) mod 360
    """
    if u == 0.0 and v == 0.0:
        return 0.0
    return (math.degrees(math.atan2(u, v)) + 360.0) % 360.0


def blend_winds(
    target_coords: Tuple[float, float],
    wind_sources: List[Dict[str, Any]],
    softening_sq: float = 400.0,
) -> Optional[Tuple[float, float]]:
    """
    Spatial vector wind field blending (TRANSFORMATION_LOGIC_SPEC.md §2.4.2 windAt).
    Blends ground station and airport wind vectors using inverse squared distance with softening.
    
    w_i = 1.0 / (d_i^2 + softening_sq)
    W = sum(w_i * w_vec_i) / sum(w_i)
    
    Args:
        target_coords: (x, y) or (lat, lon)
        wind_sources: list of dicts with 'coords' and 'u', 'v' (or 'speed', 'direction')
        softening_sq: default 400.0 (20px softening)
    """
    if not wind_sources:
        return None

    tx, ty = target_coords
    w_sum = 0.0
    u_sum = 0.0
    v_sum = 0.0

    for src in wind_sources:
        u = src.get("u")
        v = src.get("v")
        if u is None or v is None:
            spd = src.get("wind_speed") or src.get("speed")
            dr = src.get("wind_direction") or src.get("direction")
            st_name = src.get("station_name") or src.get("name")
            uv = polar_to_cartesian_wind(spd, dr, st_name)
            if uv is None:
                continue
            u, v = uv

        coords = src.get("coords")
        if not coords:
            coords = (src.get("x", src.get("latitude")), src.get("y", src.get("longitude")))
        if coords[0] is None or coords[1] is None:
            continue

        sx, sy = coords
        dx = tx - sx
        dy = ty - sy
        d_sq = dx * dx + dy * dy
        weight = 1.0 / (d_sq + softening_sq)

        w_sum += weight
        u_sum += weight * u
        v_sum += weight * v

    if w_sum <= 0.0:
        return None

    return (u_sum / w_sum, v_sum / w_sum)
