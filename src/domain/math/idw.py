"""
Inverse Distance Weighting (IDW) Geostatistical Interpolation.
Implements:
1. T1: Discrete Geodesic District-to-District IDW with Haversine distance and d0=5km clamping.
2. T2: Anisotropic Wind-Steered 2D Continuous Surface IDW with plume dispersion physics.
Zero external framework dependencies (standard library, math, and numpy).
"""
import math
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from src.domain.math.geodesy import haversine_distance

DEFAULT_IDW_POWER: float = 2.0
DEFAULT_D0_CLAMP_KM: float = 5.0
DEFAULT_EPSILON_SQ_PX: float = 16.0  # 4.0 px softening radius squared
DEFAULT_VELOCITY_SATURATION_MS: float = 1.5
MIN_ANISOTROPIC_MULTIPLIER: float = 0.30
MAX_ANISOTROPIC_MULTIPLIER: float = 1.70


def discrete_geodesic_idw(
    target: Tuple[float, float],
    stations: List[Dict[str, Any]],
    power: float = DEFAULT_IDW_POWER,
    d0: float = DEFAULT_D0_CLAMP_KM,
) -> Optional[float]:
    """
    Imputes missing pollutant concentration or scalar reading for a target coordinate
    using discrete great-circle Haversine inverse distance weighting with singularity clamping
    (TRANSFORMATION_LOGIC_SPEC.md §2.1).
    
    Formula:
        d_i = haversine(target, station_i)
        d_eff = max(d_i, d0)
        w_i = 1.0 / (d_eff ^ power)
        V = sum(w_i * v_i) / sum(w_i)
        
    Args:
        target: (latitude, longitude) of target unmonitored district centroid.
        stations: list of station dicts with 'coords': (lat, lon) and 'value': float.
        power: distance exponent p (default: 2.0).
        d0: minimum distance clamp in km to prevent singularity (default: 5.0 km).
        
    Returns:
        Interpolated scalar value, or None if no valid reporting stations exist.
    """
    if not stations:
        return None

    t_lat, t_lon = target
    w_sum = 0.0
    v_sum = 0.0

    for st in stations:
        val = st.get("value")
        if val is None:
            continue
        try:
            f_val = float(val)
        except (ValueError, TypeError):
            continue
        if math.isnan(f_val):
            continue

        coords = st.get("coords")
        if coords is None:
            c_lat = st.get("latitude", st.get("lat"))
            c_lon = st.get("longitude", st.get("lon"))
            if c_lat is not None and c_lon is not None:
                coords = (float(c_lat), float(c_lon))
        if not coords or len(coords) < 2:
            continue

        s_lat, s_lon = coords[0], coords[1]
        dist = haversine_distance(t_lat, t_lon, s_lat, s_lon)
        d_eff = max(dist, d0)
        weight = 1.0 / (d_eff ** power)

        w_sum += weight
        v_sum += weight * f_val

    if w_sum <= 0.0:
        return None

    return v_sum / w_sum


def discrete_geodesic_idw_vector(
    target: Tuple[float, float],
    stations: List[Dict[str, Any]],
    power: float = DEFAULT_IDW_POWER,
    d0: float = DEFAULT_D0_CLAMP_KM,
) -> Optional[Tuple[float, float]]:
    """
    Interpolates orthogonal horizontal wind components (u, v) independently
    using discrete geodesic IDW.
    """
    if not stations:
        return None

    t_lat, t_lon = target
    w_sum = 0.0
    u_sum = 0.0
    v_sum = 0.0

    for st in stations:
        u = st.get("u")
        v = st.get("v")
        if u is None or v is None:
            continue
        try:
            fu, fv = float(u), float(v)
        except (ValueError, TypeError):
            continue
        if math.isnan(fu) or math.isnan(fv):
            continue

        coords = st.get("coords")
        if coords is None:
            c_lat = st.get("latitude", st.get("lat"))
            c_lon = st.get("longitude", st.get("lon"))
            if c_lat is not None and c_lon is not None:
                coords = (float(c_lat), float(c_lon))
        if not coords or len(coords) < 2:
            continue

        dist = haversine_distance(t_lat, t_lon, coords[0], coords[1])
        d_eff = max(dist, d0)
        weight = 1.0 / (d_eff ** power)

        w_sum += weight
        u_sum += weight * fu
        v_sum += weight * fv

    if w_sum <= 0.0:
        return None

    return (u_sum / w_sum, v_sum / w_sum)


def calculate_distance_opacity(km_min: float) -> int:
    """
    Computes geostatistical confidence opacity taper based on distance to nearest monitor
    (TRANSFORMATION_LOGIC_SPEC.md §2.2.2).
    
    alpha = 235 if km_min < 45.0 km
    alpha = 95 if km_min > 140.0 km
    alpha = 235 - 140 * ((km_min - 45.0) / 95.0) otherwise
    """
    if km_min < 45.0:
        return 235
    if km_min > 140.0:
        return 95
    alpha = 235.0 - 140.0 * ((km_min - 45.0) / (140.0 - 45.0))
    return int(round(alpha))


def anisotropic_idw(
    target_px: Tuple[float, float],
    stations: List[Dict[str, Any]],
    wind_vector: Optional[Tuple[float, float]] = None,
    scale: float = 1.0,
    epsilon_sq: float = DEFAULT_EPSILON_SQ_PX,
) -> Tuple[float, float, int]:
    """
    Anisotropic Wind-Steered Continuous 2D IDW (TRANSFORMATION_LOGIC_SPEC.md §2.2).
    Modulates interpolation kernel weights dynamically based on advection direction
    and velocity saturation.
    
    Formula:
        d_i^2 = (x - x_i)^2 + (y - y_i)^2
        w0_i = 1.0 / (d_i^2 + epsilon^2)
        cos(alpha_i) = (delta_x * u_i - delta_y * v_i) / (d_i * s_i)
        psi_i = 1.0 + 0.70 * cos(alpha_i) * min(1.0, s_i / 1.5)
        w_i = w0_i * max(0.30, psi_i) if s_i > 0.5 and d_i > 2.0 else w0_i
        
    Args:
        target_px: (x, y) query coordinates in canvas pixel space.
        stations: list of stations with 'coords_px': (x, y), 'value': float,
                  and optionally 'u', 'v' wind vectors.
        wind_vector: optional fallback/global (u, v) wind vector if station lacks one.
        scale: pixel scale factor S for km conversion (km = px * 111.0 / S).
        epsilon_sq: kernel softening parameter squared (default: 16.0 px^2).
        
    Returns:
        (interpolated_value, nearest_station_km, alpha_channel)
    """
    if not stations:
        return (0.0, 999.0, 95)

    tx, ty = target_px
    w_sum = 0.0
    v_sum = 0.0
    min_d_px = float("inf")

    for st in stations:
        val = st.get("value")
        if val is None:
            continue
        try:
            f_val = float(val)
        except (ValueError, TypeError):
            continue
        if math.isnan(f_val):
            continue

        c_px = st.get("coords_px")
        if c_px is None:
            c_px = (st.get("x"), st.get("y"))
        if c_px[0] is None or c_px[1] is None:
            continue

        sx, sy = float(c_px[0]), float(c_px[1])
        dx = tx - sx
        dy = ty - sy
        d_sq = dx * dx + dy * dy
        d_px = math.sqrt(d_sq)

        if d_px < min_d_px:
            min_d_px = d_px

        # Base isotropic softened weight
        w0 = 1.0 / (d_sq + epsilon_sq)

        # Retrieve wind components (u, v)
        u = st.get("u")
        v = st.get("v")
        if (u is None or v is None) and wind_vector is not None:
            u, v = wind_vector
        if u is None or v is None:
            u, v = 0.0, 0.0
        else:
            u, v = float(u), float(v)

        s = math.sqrt(u * u + v * v)

        # Anisotropic kernel modulation
        if s > 0.5 and d_px > 2.0:
            # Screen y points southwards; meteorological northward v > 0 travels towards -y
            cos_alpha = (dx * u - dy * v) / (d_px * s)
            # Clamp cos_alpha to [-1.0, 1.0] for precision
            cos_alpha = max(-1.0, min(1.0, cos_alpha))
            sat = min(1.0, s / DEFAULT_VELOCITY_SATURATION_MS)
            psi = 1.0 + 0.70 * cos_alpha * sat
            mult = min(MAX_ANISOTROPIC_MULTIPLIER, max(MIN_ANISOTROPIC_MULTIPLIER, psi))
            weight = w0 * mult
        else:
            weight = w0

        w_sum += weight
        v_sum += weight * f_val

    if w_sum <= 0.0:
        return (0.0, 999.0, 95)

    interp_val = v_sum / w_sum
    # Convert min distance in pixels to km: km = d_px * (111.0 / scale)
    km_min = min_d_px * (111.0 / scale) if scale > 0 else min_d_px
    alpha = calculate_distance_opacity(km_min)

    return (interp_val, km_min, alpha)
