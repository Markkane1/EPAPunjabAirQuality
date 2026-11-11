"""
Atmospheric Advection Transport Flux and Source-Receptor Pathway Coupling.
Implements:
1. T6: Physical Inter-District Advection Transport Flux (strictly disabled for 'AQI').
2. T7: Receptor CPF Pathway Coupling, Top-60 Truncation, and Net Transport Balance.
Zero external framework dependencies (standard library and math only).
"""
import math
from typing import Any, Dict, List, Optional, Tuple, Union

from src.domain.math.geodesy import (
    angular_divergence,
    degrees_to_sector_16,
    forward_bearing,
    haversine_distance,
)
from src.domain.math.wind import (
    CALM_WIND_THRESHOLD_MS,
    wind_direction_to_bearing,
)

MAX_TRANSPORT_DISTANCE_KM: float = 180.0  # Maximum inter-district advective distance
MAX_TRANSPORT_CONE_DEG: float = 35.0     # Advection plume divergence angle limit
RESIDENCE_SCALE_KM: float = 100.0        # Atmospheric dispersion e-folding length L_S
ISOTROPIC_OMEGA_FALLBACK: float = 0.25   # Null-hypothesis isotropic receptor feedback
MAX_PATHWAY_LINKS: int = 60              # Bounded top pathway link count


def calculate_advection_flux(
    source_station: Union[Dict[str, Any], Tuple[float, float]],
    receptor_coords: Tuple[float, float],
    pollutant: str,
    concentration: Optional[float] = None,
    u_wind: Optional[float] = None,
    v_wind: Optional[float] = None,
    max_dist_km: float = MAX_TRANSPORT_DISTANCE_KM,
    max_cone_deg: float = MAX_TRANSPORT_CONE_DEG,
    residence_km: float = RESIDENCE_SCALE_KM,
) -> Optional[Dict[str, Any]]:
    """
    Estimates hourly physical mass transfer between source and receptor districts
    using vector kinematics and exponential dispersion decay (TRANSFORMATION_LOGIC_SPEC.md §2.6).
    
    CRITICAL DOMAIN GUARD:
        Physical advection transport is strictly disabled for the dimensionless ordinal index 'AQI'.
        AQI is a segmented non-linear health index, not a conserved physical mass concentration.
        Multiplying AQI by velocity violates dimensional analysis and mass conservation.
        Returns None when pollutant == 'AQI'.
        
    Formula:
        Flux = C_a * w_a * cos(delta_theta) * exp(-d / L_S)
        if w_a >= 0.5 m/s, delta_theta <= 35.0 deg, d <= 180.0 km
        
    Args:
        source_station: Dict with 'coords'/'latitude'/'longitude', 'value', 'u', 'v'
                        or Tuple (lat, lon) when parameters passed separately.
        receptor_coords: (lat, lon) coordinates of receptor district centroid.
        pollutant: chemical species name (e.g. 'PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3').
        concentration: optional scalar concentration override.
        u_wind, v_wind: optional wind vector overrides.
        max_dist_km: maximum transport distance in km (default: 180.0 km).
        max_cone_deg: maximum plume divergence angle in degrees (default: 35.0 deg).
        residence_km: characteristic e-folding distance (default: 100.0 km).
        
    Returns:
        Dict with 'flux', 'distance_km', 'bearing_deg', 'divergence_deg', or None if out of bounds.
    """
    if not pollutant or pollutant.strip().upper() == "AQI":
        return None  # Physical dimension guard

    # Resolve source coordinates
    if isinstance(source_station, (tuple, list)):
        s_lat, s_lon = float(source_station[0]), float(source_station[1])
    elif isinstance(source_station, dict):
        coords = source_station.get("coords")
        if coords is None:
            c_lat = source_station.get("latitude", source_station.get("lat"))
            c_lon = source_station.get("longitude", source_station.get("lon"))
            if c_lat is not None and c_lon is not None:
                coords = (float(c_lat), float(c_lon))
        if not coords:
            return None
        s_lat, s_lon = float(coords[0]), float(coords[1])
        if concentration is None:
            concentration = source_station.get("value", source_station.get("concentration"))
        if u_wind is None:
            u_wind = source_station.get("u")
        if v_wind is None:
            v_wind = source_station.get("v")
    else:
        return None

    r_lat, r_lon = receptor_coords

    # Geodesic distance
    d_km = haversine_distance(s_lat, s_lon, r_lat, r_lon)
    if d_km <= 0.0 or d_km > max_dist_km:
        return None

    # Concentration check
    if concentration is None:
        return None
    try:
        c_val = float(concentration)
    except (ValueError, TypeError):
        return None
    if c_val <= 0.0 or math.isnan(c_val):
        return None

    # Wind vector check
    if u_wind is None or v_wind is None:
        return None
    try:
        u_val, v_val = float(u_wind), float(v_wind)
    except (ValueError, TypeError):
        return None
    if math.isnan(u_val) or math.isnan(v_val):
        return None

    w_speed = math.sqrt(u_val * u_val + v_val * v_val)
    if w_speed < CALM_WIND_THRESHOLD_MS:
        return None  # Aerodynamic calm cutoff

    # Trajectory forward bearing (source -> receptor)
    theta_brg = forward_bearing(s_lat, s_lon, r_lat, r_lon)

    # Wind advection vector bearing (TO)
    theta_to = wind_direction_to_bearing(u_val, v_val)

    # Angular divergence between trajectory bearing and wind vector
    delta_theta = angular_divergence(theta_to, theta_brg)
    if delta_theta > max_cone_deg:
        return None  # Outside transport cone

    # Physical flux calculation
    decay = math.exp(-d_km / residence_km)
    cos_proj = math.cos(math.radians(delta_theta))
    flux_val = c_val * w_speed * cos_proj * decay

    return {
        "flux": round(flux_val, 4),
        "distance_km": round(d_km, 2),
        "bearing_deg": round(theta_brg, 2),
        "divergence_deg": round(delta_theta, 2),
    }


def calculate_receptor_coupling(
    flux_series: List[Dict[str, Any]],
    receptor_cpfs: Dict[str, Any],
    max_links: int = MAX_PATHWAY_LINKS,
) -> List[Dict[str, Any]]:
    """
    Couples hourly physical advection flux with empirical receptor wind rose feedback
    coefficient Omega to rank inter-district transport pathways (TRANSFORMATION_LOGIC_SPEC.md §2.7).
    
    Formula:
        theta_back = bearing(b -> a)
        k_rec = sector_16(theta_back)
        Omega = CPF_b(k_rec) if (monitored and not null) else 0.25 (isotropic baseline)
        Score_a_to_b = Mean_Flux_a_to_b * Omega
        
    Candidate pathways are sorted descending by score and strictly truncated to top 60 links.
    
    Args:
        flux_series: List of dicts with 'source_district', 'receptor_district',
                     'distance_km', 'bearing_deg', 'mean_flux' (or 'flux').
        receptor_cpfs: Dict mapping district_id to either CPFRoseResult, dict, or list of sectors.
        max_links: Maximum links to return (default: 60).
        
    Returns:
        List of ranked pathway dicts sorted by score descending.
    """
    ranked_links: List[Dict[str, Any]] = []

    for item in flux_series:
        src = item.get("source_district", item.get("src"))
        rcv = item.get("receptor_district", item.get("rcv"))
        if not src or not rcv:
            continue

        raw_flux = item.get("mean_flux", item.get("flux", 0.0))
        if raw_flux is None or raw_flux <= 0.0:
            continue
        try:
            mean_flux = float(raw_flux)
        except (ValueError, TypeError):
            continue

        dist_km = item.get("distance_km", item.get("km", 0.0))
        bearing_fwd = item.get("bearing_deg", item.get("bearing"))

        # Calculate arrival back-bearing at receptor: (bearing + 180) mod 360
        if bearing_fwd is not None:
            theta_back = (float(bearing_fwd) + 180.0) % 360.0
        else:
            theta_back = 0.0

        k_rec = degrees_to_sector_16(theta_back)

        # Retrieve receptor CPF feedback Omega
        omega = ISOTROPIC_OMEGA_FALLBACK
        if rcv in receptor_cpfs:
            rcv_rose = receptor_cpfs[rcv]
            sectors = None
            if hasattr(rcv_rose, "sectors"):
                sectors = rcv_rose.sectors
            elif isinstance(rcv_rose, dict):
                sectors = rcv_rose.get("sectors")
            elif isinstance(rcv_rose, (list, tuple)):
                sectors = rcv_rose

            if sectors and len(sectors) > k_rec and sectors[k_rec] is not None:
                omega = float(sectors[k_rec])

        score = mean_flux * omega

        ranked_links.append({
            "source_district": src,
            "receptor_district": rcv,
            "distance_km": round(float(dist_km), 2),
            "bearing_deg": round(float(bearing_fwd) if bearing_fwd is not None else 0.0, 2),
            "flux": round(mean_flux, 4),
            "omega": round(omega, 4),
            "score": round(score, 4),
        })

    # Sort descending by score and truncate to top 60 links
    ranked_links.sort(key=lambda x: x["score"], reverse=True)
    return ranked_links[:max_links]


def calculate_net_transport_balance(
    pathway_links: List[Dict[str, Any]]
) -> Dict[str, float]:
    """
    Computes net district transport balance from active pathway scores
    (TRANSFORMATION_LOGIC_SPEC.md §2.7.2).
    
    Net Transport_d = sum_{b != d} Score(d -> b) - sum_{a != d} Score(a -> d)
    Positive: Net Exporter (smog source)
    Negative: Net Importer (smog receptor)
    """
    net_balances: Dict[str, float] = {}

    for link in pathway_links:
        src = link.get("source_district")
        rcv = link.get("receptor_district")
        score = float(link.get("score", 0.0))

        if src:
            net_balances[src] = net_balances.get(src, 0.0) + score
        if rcv:
            net_balances[rcv] = net_balances.get(rcv, 0.0) - score

    return {d: round(bal, 4) for d, bal in net_balances.items()}
