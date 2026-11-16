"""
Transformation 10: 24-Hour Diurnal Persistence Forecast Engine.
Preserves diurnal profile while scaling with recent-to-historical trend ratio.
Adheres to TRANSFORMATION_LOGIC_SPEC.md §Transformation 10.
"""
from typing import Dict, List, Optional


def calculate_24h_persistence_forecast(
    recent_24h_series: List[float],
    historical_24h_series: Optional[List[float]] = None,
    min_concentration: float = 0.0,
    max_scale_factor: float = 5.0,
    min_scale_factor: float = 0.2,
) -> List[float]:
    """
    Computes 24-hour diurnal persistence forecast for day d+1:
        C_{d+1, h} = C_{d, h} * ( mean(C_{recent}) / mean(C_{historical}) )

    Args:
        recent_24h_series: Hourly concentrations for day d (length up to 24).
        historical_24h_series: Baseline/historical hourly concentrations. Defaults to recent_24h_series.
        min_concentration: Lower floor for pollutant concentration.
        max_scale_factor: Upper bound clamp on ratio to prevent runaway forecasts.
        min_scale_factor: Lower bound clamp on ratio.

    Returns:
        List of 24 forecasted hourly concentrations.
    """
    if not recent_24h_series:
        return [0.0] * 24

    # Ensure 24 elements (pad or truncate if necessary)
    if len(recent_24h_series) < 24:
        # Repeat or pad with last known value
        last_val = recent_24h_series[-1]
        c_recent = list(recent_24h_series) + [last_val] * (24 - len(recent_24h_series))
    else:
        c_recent = list(recent_24h_series[:24])

    if historical_24h_series is None or len(historical_24h_series) == 0:
        c_hist = c_recent
    else:
        if len(historical_24h_series) < 24:
            last_val = historical_24h_series[-1]
            c_hist = list(historical_24h_series) + [last_val] * (24 - len(historical_24h_series))
        else:
            c_hist = list(historical_24h_series[:24])

    # Calculate 24h arithmetic means
    valid_recent = [v for v in c_recent if v is not None and v >= 0]
    valid_hist = [v for v in c_hist if v is not None and v >= 0]

    mean_recent = sum(valid_recent) / len(valid_recent) if valid_recent else 0.0
    mean_hist = sum(valid_hist) / len(valid_hist) if valid_hist else 0.0

    if mean_hist > 1e-6:
        ratio = mean_recent / mean_hist
        ratio = max(min_scale_factor, min(ratio, max_scale_factor))
    else:
        ratio = 1.0

    forecast: List[float] = []
    for val in c_recent:
        projected = round(val * ratio, 2)
        forecast.append(max(min_concentration, projected))

    return forecast


def calculate_multi_district_forecast(
    district_series: Dict[str, List[float]],
    historical_district_series: Optional[Dict[str, List[float]]] = None,
) -> Dict[str, List[float]]:
    """
    Computes 24h persistence forecasts across all provided districts.
    """
    historical_district_series = historical_district_series or {}
    results: Dict[str, List[float]] = {}
    for dname, recent_s in district_series.items():
        hist_s = historical_district_series.get(dname)
        results[dname] = calculate_24h_persistence_forecast(recent_s, hist_s)
    return results
