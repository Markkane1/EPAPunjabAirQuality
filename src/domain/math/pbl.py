"""
Transformation 11: Atmospheric Ventilation Index & Planetary Boundary Layer Dispersion.
Formula: VI = h_PBL * w_sfc (m^2/s)
Adheres to TRANSFORMATION_LOGIC_SPEC.md §Transformation 11.
"""
from typing import Dict, List, Optional, Tuple

# Diurnal Climatological PBL heights for November Punjab smog conditions (meters AGL)
# Index corresponds to hour of day in PKT (0..23)
NOVEMBER_CLIMATOLOGICAL_PBL_PKT: List[float] = [
    150.0, 140.0, 130.0, 120.0, 120.0, 130.0, 160.0, 220.0,  # 00:00 - 07:00 (Severe Nocturnal Trap)
    350.0, 500.0, 680.0, 850.0, 950.0, 1050.0, 1100.0, 1020.0,  # 08:00 - 15:00 (Convective Growth)
    850.0, 600.0, 380.0, 250.0, 200.0, 180.0, 160.0, 150.0,   # 16:00 - 23:00 (Evening Inversion Onset)
]

# Statutory Dispersion Risk Thresholds (m^2/s)
VI_CRITICAL_TRAP_THRESHOLD: float = 2000.0
VI_POOR_THRESHOLD: float = 4000.0
VI_MODERATE_THRESHOLD: float = 6000.0

DISPERSION_CRITICAL_TRAP: str = "Critical Trap / Severe Smog"
DISPERSION_POOR: str = "Poor Dispersion"
DISPERSION_MODERATE: str = "Moderate Dispersion"
DISPERSION_GOOD: str = "Good Dispersion"

# Color mappings for UI / report visualization
DISPERSION_COLORS: Dict[str, str] = {
    DISPERSION_CRITICAL_TRAP: "#C00000",  # Severe / Dark Red
    DISPERSION_POOR: "#FF0000",           # Poor / Red
    DISPERSION_MODERATE: "#FFFF00",       # Moderate / Yellow
    DISPERSION_GOOD: "#00B050",           # Good / Green
}


def calculate_ventilation_index(pbl_height_m: float, surface_wind_speed_ms: float) -> float:
    """
    Calculates Atmospheric Ventilation Index:
        VI = h_PBL * w_sfc (m^2/s)

    Args:
        pbl_height_m: Mixing layer height above ground level (m).
        surface_wind_speed_ms: Surface 10m wind speed (m/s).

    Returns:
        Ventilation index in m^2/s, rounded to 1 decimal place.
    """
    h = max(0.0, float(pbl_height_m))
    w = max(0.0, float(surface_wind_speed_ms))
    return round(h * w, 1)


def classify_ventilation_index(vi: float) -> str:
    """
    Classifies Ventilation Index into statutory dispersion risk bands:
        VI < 2000: Critical Trap / Severe Smog
        2000 <= VI < 4000: Poor Dispersion
        4000 <= VI < 6000: Moderate Dispersion
        VI >= 6000: Good Dispersion
    """
    if vi < VI_CRITICAL_TRAP_THRESHOLD:
        return DISPERSION_CRITICAL_TRAP
    elif vi < VI_POOR_THRESHOLD:
        return DISPERSION_POOR
    elif vi < VI_MODERATE_THRESHOLD:
        return DISPERSION_MODERATE
    else:
        return DISPERSION_GOOD


def calculate_and_classify_vi(
    pbl_height_m: float, surface_wind_speed_ms: float
) -> Tuple[float, str, str]:
    """
    Computes ventilation index, classifies dispersion risk, and returns (vi, category, hex_color).
    """
    vi = calculate_ventilation_index(pbl_height_m, surface_wind_speed_ms)
    category = classify_ventilation_index(vi)
    color = DISPERSION_COLORS.get(category, "#808080")
    return vi, category, color
