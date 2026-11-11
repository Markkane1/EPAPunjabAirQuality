"""
Temporal Quality Control (QC), Outlier Scrubbing, Completeness Rules, and Animation Lerp.
Implements:
1. T10: Step 0 zero/negative purge.
2. 7-hour rolling median spike filter (>4M and >3ref).
3. 3-hour logger hold (sensor freeze) filter with i >= 2 index guard (AQI exempt).
4. 75% temporal completeness aggregation rule.
5. Continuous sub-hourly linear interpolation (lerp) for 60 FPS animation scrubbing.
Zero external framework dependencies (standard library and math only).
"""
import math
from typing import List, Optional, Tuple, Union

DEFAULT_COMPLETENESS_RATIO: float = 0.75
MEDIAN_WINDOW_HALF_WIDTH: int = 3  # 7-hour rolling window: [i - 3, i + 3]
MIN_MEDIAN_WINDOW_SAMPLES: int = 3
SPIKE_MEDIAN_MULTIPLIER: float = 4.0
SPIKE_REF_MULTIPLIER: float = 3.0


def temporal_qc_clean(
    series: List[Optional[float]],
    ref_limit: float,
    pollutant: str,
) -> Tuple[List[Optional[float]], int]:
    """
    Sanitizes zero/negatives, cleans 7-hour rolling median spikes, and purges 3-hour logger holds
    (TRANSFORMATION_LOGIC_SPEC.md §2.10.1).
    
    Steps:
    0. Purge zero/negative values: convert v <= 0.0, None, NaN to None.
    1. 7-Hour Rolling Window Median Spike Filter:
       W_i = {v_j in [max(0, i-3), min(N-1, i+3)] with v_j != None}
       If |W_i| >= 3:
           M_i = median(W_i)
           If v_i > 4.0 * M_i AND v_i > 3.0 * ref_limit -> v_i = None, spikes += 1
    2. 3-Hour Logger Hold (Sensor Freeze) Filter with Index Guard (i >= 2):
       For physical pollutants (p != 'AQI'):
           For i >= 2:
               If v_i == v_{i-1} == v_{i-2} and v_i != None -> v_i = None
       (AQI is exempt from hold filter as integer AQI values may genuinely stay constant).
       
    Args:
        series: Raw hourly time-series array.
        ref_limit: Statutory standard reference limit ref_p (e.g. 35 for PM2.5).
        pollutant: Pollutant name string.
        
    Returns:
        (cleaned_series, spike_count)
    """
    if not series:
        return ([], 0)

    # Step 0: Zero and negative purge
    cleaned: List[Optional[float]] = []
    for v in series:
        if v is None:
            cleaned.append(None)
            continue
        try:
            fv = float(v)
            if math.isnan(fv) or fv <= 0.0 or math.isinf(fv):
                cleaned.append(None)
            else:
                cleaned.append(fv)
        except (ValueError, TypeError):
            cleaned.append(None)

    n = len(cleaned)
    spike_count = 0

    # Step 1: 7-Hour Rolling Window Median Spike Filter
    for i in range(n):
        curr = cleaned[i]
        if curr is None:
            continue

        w_start = max(0, i - MEDIAN_WINDOW_HALF_WIDTH)
        w_end = min(n, i + MEDIAN_WINDOW_HALF_WIDTH + 1)
        window = [cleaned[j] for j in range(w_start, w_end) if cleaned[j] is not None]

        if len(window) >= MIN_MEDIAN_WINDOW_SAMPLES:
            window.sort()
            mid = len(window) // 2
            if len(window) % 2 != 0:
                median_val = window[mid]
            else:
                median_val = (window[mid - 1] + window[mid]) / 2.0

            if curr > SPIKE_MEDIAN_MULTIPLIER * median_val and curr > SPIKE_REF_MULTIPLIER * ref_limit:
                cleaned[i] = None
                spike_count += 1

    # Step 2: 3-Hour Logger Hold (Sensor Freeze) Filter with Index Guard (i >= 2)
    # Physical pollutants only; dimensionless integer 'AQI' is exempt
    if pollutant.strip().upper() != "AQI":
        pre_hold = list(cleaned)
        for i in range(2, n):
            v0 = pre_hold[i]
            v1 = pre_hold[i - 1]
            v2 = pre_hold[i - 2]
            if v0 is not None and v1 is not None and v2 is not None:
                if v0 == v1 == v2:
                    cleaned[i] = None

    return (cleaned, spike_count)


def check_completeness(
    series: List[Optional[float]],
    required_ratio: float = DEFAULT_COMPLETENESS_RATIO,
) -> Optional[float]:
    """
    Evaluates regulatory 75% temporal completeness rule for time aggregation
    (TRANSFORMATION_LOGIC_SPEC.md §2.10.1).
    
    Formula:
        N_valid = sum( v != None )
        Required = max(1, round(required_ratio * H))
        Mean = sum(valid) / N_valid if N_valid >= Required else None
        
    Args:
        series: Array of hourly observation values.
        required_ratio: Minimum fraction of valid samples required (default: 0.75).
        
    Returns:
        Mean of valid observations, or None if completeness threshold not met.
    """
    total_hours = len(series)
    if total_hours == 0:
        return None

    valid_values = [v for v in series if v is not None and not math.isnan(v)]
    n_valid = len(valid_values)

    min_required = max(1, int(round(required_ratio * total_hours)))
    if n_valid < min_required:
        return None

    return sum(valid_values) / n_valid


def subhourly_lerp(
    series: List[Optional[float]],
    fp: float,
) -> Optional[float]:
    """
    Continuous sub-hourly linear interpolation for smooth 60 FPS animation scrubbing
    (TRANSFORMATION_LOGIC_SPEC.md §2.10.1).
    
    Formula:
        i = floor(fp), j = min(N-1, i+1), f = fp - i
        lerp(a, b, f) =
            b if a is None
            a if b is None
            a + (b - a) * f otherwise
            
    Args:
        series: Array of hourly observations.
        fp: Floating-point scrubber position in [0.0, N-1.0].
        
    Returns:
        Interpolated scalar value, or None if both bounding endpoints are None.
    """
    n = len(series)
    if n == 0:
        return None
    if n == 1:
        return series[0]

    # Clamp fp to valid index bounds [0.0, n - 1.0]
    clamped_fp = max(0.0, min(float(n - 1), fp))
    i = int(math.floor(clamped_fp))
    j = min(n - 1, i + 1)
    f = clamped_fp - i

    a = series[i]
    b = series[j]

    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a

    return a + (b - a) * f
