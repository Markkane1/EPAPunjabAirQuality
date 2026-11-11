"""
Transboundary Atmospheric Cross-Border Inflow and Outflow Index.
Implements:
1. T8: 120km border-belt district inflow/outflow evaluation against Indian wind sectors.
2. 39 border normal vector node dot products for animated map chevrons.
3. 117 CAMS boundary perimeter integration.
Zero external framework dependencies (standard library and math only).
"""
import math
from typing import Any, Dict, List, Optional, Tuple

from src.domain.math.geodesy import degrees_to_sector_16
from src.domain.math.wind import CALM_WIND_THRESHOLD_MS, cartesian_to_polar_wind

BORDER_CORRIDOR_LIMIT_KM: float = 120.0  # 120 km border-belt corridor limit
BORDER_RESIDENCE_SCALE_KM: float = 100.0  # e-folding decay scale
FLOW_NORMAL_THRESHOLD_MS: float = 0.25    # Chevron animation threshold (+inflow, -outflow)


def calculate_district_transboundary_flux(
    border_distance_km: float,
    india_sectors: List[int],
    concentration: float,
    u_wind: float,
    v_wind: float,
    is_estimated: bool = False,
) -> float:
    """
    Evaluates hourly transboundary flux value (TBVal_d) for an individual border district
    (TRANSFORMATION_LOGIC_SPEC.md §2.8.2).
    
    Formula:
        direction_from = cartesian_to_polar(u, v)
        k = degrees_to_sector_16(direction_from)
        w_d = sqrt(u^2 + v^2)
        
        If w_d < 0.5 m/s (calm) -> TBVal = 0.0
        If k in india_sectors -> Inflow: +C * w * exp(-d_border / 100)
        If (k + 8) mod 16 in india_sectors -> Outflow: -C * w * exp(-d_border / 100)
        Else -> Neutral / Parallel: 0.0
        
    Args:
        border_distance_km: distance from district centroid to international border in km.
        india_sectors: list of compass sector indices (0-15) where wind blows from India.
        concentration: measured mass concentration (ug/m3).
        u_wind, v_wind: local horizontal wind vector components in m/s.
        is_estimated: whether district data is imputed (excluded from regional totals).
        
    Returns:
        Signed TBVal: positive = inflow from India, negative = outflow to India, 0.0 = calm/neutral.
    """
    if border_distance_km > BORDER_CORRIDOR_LIMIT_KM:
        return 0.0

    if concentration <= 0.0 or math.isnan(concentration):
        return 0.0

    w_speed = math.sqrt(u_wind * u_wind + v_wind * v_wind)
    if w_speed < CALM_WIND_THRESHOLD_MS:
        return 0.0  # Calm winds yield zero flux

    _, dir_from = cartesian_to_polar_wind(u_wind, v_wind)
    sector_k = degrees_to_sector_16(dir_from)

    decay = math.exp(-border_distance_km / BORDER_RESIDENCE_SCALE_KM)
    magnitude = concentration * w_speed * decay

    # Inflow check (wind blows FROM India into Pakistan)
    if sector_k in india_sectors:
        return magnitude

    # Outflow check (wind blows FROM Pakistan into India, 180 deg opposite)
    outflow_sector = (sector_k + 8) % 16
    if outflow_sector in india_sectors:
        return -magnitude

    # Neutral or parallel flow along border
    return 0.0


def calculate_border_normal_flux(
    u_wind: float,
    v_wind: float,
    nx: float,
    ny: float,
) -> float:
    """
    Calculates normal velocity projection onto border normal node (TRANSFORMATION_LOGIC_SPEC.md §2.8.2).
    
    Formula:
        Phi_j = u_j * nx_j + v_j * ny_j
        
    Positive Phi (> +0.25 m/s): Transboundary Inflow (entering Punjab)
    Negative Phi (< -0.25 m/s): Transboundary Outflow (exiting Punjab)
    """
    return u_wind * nx + v_wind * ny


def calculate_transboundary_index(
    border_districts: List[Dict[str, Any]],
    border_normals: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Computes aggregated regional transboundary inflow/outflow metrics and border node fluxes
    (TRANSFORMATION_LOGIC_SPEC.md §2.8).
    
    Args:
        border_districts: List of district dicts with:
            - 'district_id' or 'name'
            - 'border_distance_km'
            - 'india_sectors'
            - 'concentration' or 'value'
            - 'u', 'v' (or 'wind_speed', 'wind_direction')
            - 'is_estimated' (bool, optional)
        border_normals: Optional list of 39 border normal vector nodes with 'u', 'v', 'nx', 'ny'.
        
    Returns:
        Dict containing:
            - 'inflow_total': sum of positive district flux values across monitored border districts
            - 'outflow_total': sum of absolute negative flux values across monitored border districts
            - 'net_flux': inflow_total - outflow_total
            - 'district_values': mapping of district_id to TBVal
            - 'normal_fluxes': list of dot product velocities across border nodes
    """
    district_values: Dict[str, float] = {}
    inflow_total = 0.0
    outflow_total = 0.0

    for d in border_districts:
        d_id = str(d.get("district_id", d.get("name", d.get("district", ""))))
        dist_km = float(d.get("border_distance_km", 999.0))
        india_sec = d.get("india_sectors", [])
        is_est = bool(d.get("is_estimated", d.get("est", False)))

        val = d.get("concentration", d.get("value", 0.0))
        if val is None:
            val = 0.0
        c = float(val)

        u = d.get("u")
        v = d.get("v")
        if u is None or v is None:
            spd = d.get("wind_speed", d.get("speed", 0.0))
            dr = d.get("wind_direction", d.get("direction", 0.0))
            if spd is not None and dr is not None:
                rad = math.radians(float(dr))
                u = -float(spd) * math.sin(rad)
                v = -float(spd) * math.cos(rad)
            else:
                u, v = 0.0, 0.0

        tb_val = calculate_district_transboundary_flux(
            border_distance_km=dist_km,
            india_sectors=list(india_sec),
            concentration=c,
            u_wind=float(u),
            v_wind=float(v),
            is_estimated=is_est,
        )

        district_values[d_id] = round(tb_val, 4)

        # Only monitored stations contribute to official regional inflow/outflow totals
        if not is_est:
            if tb_val > 0.0:
                inflow_total += tb_val
            elif tb_val < 0.0:
                outflow_total += abs(tb_val)

    # 39 Border animation nodes normal vector flow
    normal_fluxes: List[float] = []
    if border_normals:
        for node in border_normals:
            u_n = float(node.get("u", 0.0))
            v_n = float(node.get("v", 0.0))
            nx = float(node.get("nx", 0.0))
            ny = float(node.get("ny", 0.0))
            phi = calculate_border_normal_flux(u_n, v_n, nx, ny)
            normal_fluxes.append(round(phi, 4))

    net_flux = inflow_total - outflow_total

    return {
        "inflow_total": round(inflow_total, 4),
        "outflow_total": round(outflow_total, 4),
        "net_flux": round(net_flux, 4),
        "district_values": district_values,
        "normal_fluxes": normal_fluxes,
    }
