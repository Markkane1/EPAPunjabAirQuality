"""
Geodesy and Spatial Coordinate Mathematics.
Implements great-circle Haversine distance, forward and back bearings,
angular divergence, and 16-sector compass rose mapping.
Zero external framework dependencies (standard library and math only).
"""
import math
from typing import Tuple

R_EARTH_KM: float = 6371.0  # WGS-84 mean volumetric spherical radius in km

SECTOR_NAMES_16: Tuple[str, ...] = (
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
)


def haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float, r_earth: float = R_EARTH_KM
) -> float:
    """
    Computes great-circle distance between two geographic coordinates in kilometers
    using the Haversine formula (TRANSFORMATION_LOGIC_SPEC.md §2.1.2).
    
    Args:
        lat1: Latitude of point 1 in decimal degrees.
        lon1: Longitude of point 1 in decimal degrees.
        lat2: Latitude of point 2 in decimal degrees.
        lon2: Longitude of point 2 in decimal degrees.
        r_earth: Earth radius in kilometers (default: 6371.0 km).
        
    Returns:
        Distance in kilometers. Returns 0.0 for identical coordinates.
    """
    if lat1 == lat2 and lon1 == lon2:
        return 0.0

    phi1 = math.radians(lat1)
    lam1 = math.radians(lon1)
    phi2 = math.radians(lat2)
    lam2 = math.radians(lon2)

    dphi = phi2 - phi1
    dlam = lam2 - lam1

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(dlam / 2.0) ** 2)
    # Clamp argument to asin to [0.0, 1.0] for numerical stability
    c = 2.0 * math.asin(math.sqrt(max(0.0, min(1.0, a))))
    return r_earth * c


def forward_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes initial forward great-circle bearing from point 1 to point 2 in degrees.
    Azimuth clockwise from North in range [0.0, 360.0) (TRANSFORMATION_LOGIC_SPEC.md §2.6.2).
    
    Args:
        lat1, lon1: Coordinates of starting point in decimal degrees.
        lat2, lon2: Coordinates of destination point in decimal degrees.
        
    Returns:
        Bearing angle in degrees [0.0, 360.0).
    """
    if lat1 == lat2 and lon1 == lon2:
        return 0.0

    phi1 = math.radians(lat1)
    lam1 = math.radians(lon1)
    phi2 = math.radians(lat2)
    lam2 = math.radians(lon2)

    dlam = lam2 - lam1
    y = math.sin(dlam) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam)

    bearing = (math.degrees(math.atan2(y, x)) + 360.0) % 360.0
    return bearing


def back_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes back-bearing (arrival angle) from destination point 2 back to point 1.
    
    Args:
        lat1, lon1: Starting point coordinates.
        lat2, lon2: Destination coordinates.
        
    Returns:
        Bearing angle in degrees [0.0, 360.0).
    """
    return forward_bearing(lat2, lon2, lat1, lon1)


def angular_divergence(angle1: float, angle2: float) -> float:
    """
    Calculates shortest angular difference between two azimuth angles in degrees.
    Range [0.0, 180.0] (TRANSFORMATION_LOGIC_SPEC.md §2.6.2).
    
    Formula:
        |((angle1 - angle2 + 180) mod 360) - 180|
    """
    diff = abs(((angle1 - angle2 + 180.0) % 360.0) - 180.0)
    return diff


def degrees_to_sector_16(deg: float) -> int:
    """
    Maps continuous azimuth degrees [0, 360) to 16 compass rose sectors (width 22.5 deg).
    Sector 0 is centered on North (-11.25 deg to +11.25 deg).
    Range: [0, 15] (TRANSFORMATION_LOGIC_SPEC.md §2.5.2).
    
    Sector 0: North (0 deg)
    Sector 4: East (90 deg)
    Sector 8: South (180 deg)
    Sector 12: West (270 deg)
    """
    norm_deg = deg % 360.0
    sector = int(math.floor((norm_deg + 11.25) / 22.5)) % 16
    return sector


def sector_16_to_degrees(sector: int) -> float:
    """
    Returns center azimuth in degrees for a given 16-sector index.
    """
    return (sector % 16) * 22.5
