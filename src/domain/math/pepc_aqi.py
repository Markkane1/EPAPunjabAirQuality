"""
Official Punjab Environmental Protection Council (PEPC) AQI Calculations and Color Scales.
Implements:
1. T9: Statutory piecewise linear sub-index interpolation across continuous half-open intervals.
2. 500 operational ceiling cap.
3. Particulate-matter composite AQI: max(I_PM2.5, I_PM10).
4. Official 7-category color palette and continuous 7-stop PEQS RGB gradient ramp.
Zero external framework dependencies (standard library and math only).
"""
import math
from typing import Any, Dict, List, Optional, Tuple, Union

# Statutory Continuous Breakpoint Matrix (TRANSFORMATION_LOGIC_SPEC.md §2.9.2)
PEPC_BREAKPOINTS: Dict[str, List[float]] = {
    "PM10": [0.0, 75.0, 150.0, 250.0, 350.0, 450.0, 550.0],
    "PM2.5": [0.0, 15.0, 35.0, 70.0, 140.0, 250.0, 350.0],
    "SO2": [0.0, 60.0, 120.0, 220.0, 320.0, 800.0, 1600.0],
    "NO2": [0.0, 40.0, 80.0, 130.0, 180.0, 380.0, 580.0],
    "O3": [0.0, 65.0, 130.0, 195.0, 260.0, 450.0, 550.0],
    "CO": [0.0, 2.5, 5.0, 7.5, 10.0, 25.0, 40.0],
}

# Sub-index tiers corresponding to category thresholds
AQI_TIERS: List[int] = [0, 50, 100, 150, 200, 300, 400, 500]

# Official 7-Category Descriptors and Hex Palette (TRANSFORMATION_LOGIC_SPEC.md §2.9.2)
PEPC_CATEGORIES: List[Dict[str, Any]] = [
    {"index_max": 50, "name": "Good", "hex": "#00B050"},
    {"index_max": 100, "name": "Satisfactory", "hex": "#92D050"},
    {"index_max": 150, "name": "Moderate", "hex": "#FFFF00"},
    {"index_max": 200, "name": "Unhealthy (Sensitive)", "hex": "#ED7D31"},
    {"index_max": 300, "name": "Unhealthy", "hex": "#FF0000"},
    {"index_max": 400, "name": "Very Unhealthy", "hex": "#7030A0"},
    {"index_max": 500, "name": "Hazardous", "hex": "#C00000"},
]

# Continuous PEQS Multi-Stop Color Scale Limits & Stops (§2.9.4)
PEQS_MULTIPLIERS: Tuple[float, ...] = (0.0, 0.5, 1.0, 1.5, 2.5, 4.0, 6.0)
PEQS_RGB_STOPS: Tuple[Tuple[int, int, int], ...] = (
    (58, 165, 93),   # Clean Green
    (156, 204, 58),  # Light Green
    (242, 194, 48),  # Yellow (At Standard)
    (240, 122, 38),  # Orange (1.5x Limit)
    (214, 52, 44),   # Red (2.5x Limit)
    (142, 59, 143),  # Purple (4.0x Limit)
    (90, 21, 48),    # Deep Maroon (6.0x Limit)
)


def normalize_pollutant_key(pollutant: str) -> str:
    """Normalizes pollutant string to canonical dictionary key."""
    clean = pollutant.strip().upper().replace(".", "").replace("_", "")
    if clean in ("PM25", "PM2"):
        return "PM2.5"
    if clean in ("PM10", "PM1"):
        return "PM10"
    return clean


def pepc_calculate_aqi(pollutant: str, concentration: Optional[float]) -> Optional[int]:
    """
    Computes statutory Punjab Air Quality Index (AQI) sub-index for a given pollutant concentration
    using official PEPC piecewise linear interpolation across continuous half-open intervals
    (TRANSFORMATION_LOGIC_SPEC.md §2.9.2).
    
    Formula:
        I_p = round( ((I_high - I_low) / (BP_high - BP_low)) * (C_p - BP_low) + I_low )
        
    Special Rules:
        - If concentration <= 0.0 or NaN: returns None (zero/negative sanitization).
        - If concentration == 0.0: returns 0.
        - If concentration > BP_6: clamped to 500 (operational ceiling cap).
        
    Args:
        pollutant: chemical species ('PM2.5', 'PM10', 'SO2', 'NO2', 'O3', 'CO').
        concentration: measured concentration in ug/m3 (mg/m3 for CO).
        
    Returns:
        Integer AQI value in [0, 500], or None if concentration is invalid or unmonitored pollutant.
    """
    if concentration is None:
        return None
    try:
        c = float(concentration)
    except (ValueError, TypeError):
        return None

    if math.isnan(c) or c < 0.0:
        return None

    if c == 0.0:
        return 0

    key = normalize_pollutant_key(pollutant)
    if key not in PEPC_BREAKPOINTS:
        return None

    bps = PEPC_BREAKPOINTS[key]
    tiers = AQI_TIERS

    # Operational Ceiling Cap
    if c > bps[-1]:
        return 500

    # Continuous half-open intervals: (BP_low, BP_high]
    for i in range(1, len(bps)):
        bp_low = bps[i - 1]
        bp_high = bps[i]
        if bp_low < c <= bp_high:
            i_low = tiers[i - 1]
            i_high = tiers[i]
            val = ((i_high - i_low) / (bp_high - bp_low)) * (c - bp_low) + i_low
            return int(round(val))

    return 500


def pepc_composite_aqi(
    pm25_aqi: Optional[int], pm10_aqi: Optional[int]
) -> Optional[int]:
    """
    Computes Composite Punjab Air Quality Index (TRANSFORMATION_LOGIC_SPEC.md §2.9.3).
    
    Statutory Rule:
        Composite AQI is strictly governed by particulate matter sub-indices:
        AQI_composite = max(I_PM2.5, I_PM10)
        Gaseous pollutants (NO2, SO2, CO, O3) are monitored individually and do not govern composite AQI.
        
    Args:
        pm25_aqi: PM2.5 AQI sub-index [0, 500].
        pm10_aqi: PM10 AQI sub-index [0, 500].
        
    Returns:
        Maximum particulate sub-index, or None if both inputs are None.
    """
    valid = [v for v in (pm25_aqi, pm10_aqi) if v is not None and not math.isnan(v)]
    if not valid:
        return None
    return int(max(valid))


def pepc_get_category(aqi: Optional[int]) -> str:
    """
    Returns official PEPC category name descriptor for given AQI value.
    """
    if aqi is None:
        return "Unknown"
    for cat in PEPC_CATEGORIES:
        if aqi <= cat["index_max"]:
            return cat["name"]
    return "Hazardous"


def pepc_get_color(aqi: Optional[int]) -> str:
    """
    Returns official PEPC hex color string for given AQI value.
    """
    if aqi is None:
        return "#808080"  # Neutral gray
    for cat in PEPC_CATEGORIES:
        if aqi <= cat["index_max"]:
            return cat["hex"]
    return "#C00000"


def pepc_interpolate_color(value: float, ref_limit: float) -> Tuple[int, int, int]:
    """
    Computes continuous 7-stop PEQS RGB color vector relative to statutory standard limit
    (TRANSFORMATION_LOGIC_SPEC.md §2.9.4).
    
    Args:
        value: concentration value.
        ref_limit: statutory reference limit (e.g. 35 ug/m3 for PM2.5).
        
    Returns:
        (R, G, B) tuple of integers in [0, 255].
    """
    if ref_limit <= 0.0 or value <= 0.0 or math.isnan(value):
        return PEQS_RGB_STOPS[0]

    mult_val = value / ref_limit
    num_stops = len(PEQS_MULTIPLIERS)

    if mult_val <= PEQS_MULTIPLIERS[0]:
        return PEQS_RGB_STOPS[0]
    if mult_val >= PEQS_MULTIPLIERS[-1]:
        return PEQS_RGB_STOPS[-1]

    for k in range(1, num_stops):
        m0 = PEQS_MULTIPLIERS[k - 1]
        m1 = PEQS_MULTIPLIERS[k]
        if m0 <= mult_val <= m1:
            t = (mult_val - m0) / (m1 - m0)
            c0 = PEQS_RGB_STOPS[k - 1]
            c1 = PEQS_RGB_STOPS[k]
            r = int(round((1.0 - t) * c0[0] + t * c1[0]))
            g = int(round((1.0 - t) * c0[1] + t * c1[1]))
            b = int(round((1.0 - t) * c0[2] + t * c1[2]))
            return (r, g, b)

    return PEQS_RGB_STOPS[-1]


def pepc_interpolate_color_hex(value: float, ref_limit: float) -> str:
    """
    Returns continuous 7-stop PEQS interpolated color formatted as a Hex string '#RRGGBB'.
    """
    r, g, b = pepc_interpolate_color(value, ref_limit)
    return f"#{r:02X}{g:02X}{b:02X}"
