"""
Conditional Probability Function (CPF) Wind Rose Modeling.
Performs directional source apportionment across 16 compass sectors (22.5 deg width)
with aerodynamic calm wind exclusion (<0.5 m/s) and small-sample suppression (Nk < 6).
Zero external framework dependencies (standard library and numpy).
"""
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.domain.math.geodesy import degrees_to_sector_16
from src.domain.math.wind import CALM_WIND_THRESHOLD_MS

MIN_SECTOR_SAMPLES: int = 6  # Small-sample suppression threshold (TRANSFORMATION_LOGIC_SPEC.md §2.5.2)
DEFAULT_SECTOR_COUNT: int = 16
DEFAULT_ISOTROPIC_BASELINE: float = 0.25  # P75 null hypothesis baseline


def calculate_pooled_p75(
    observations: List[Dict[str, Any]],
    calm_threshold: float = CALM_WIND_THRESHOLD_MS,
) -> float:
    """
    Computes 75th percentile concentration threshold (tau = P75) over pooled
    individual station-hour observations with C > 0 and wind >= calm_threshold
    (TRANSFORMATION_LOGIC_SPEC.md §2.5.2).
    """
    valid_c: List[float] = []
    for obs in observations:
        val = obs.get("value")
        if val is None:
            val = obs.get("concentration")
        if val is None:
            continue
        try:
            c = float(val)
        except (ValueError, TypeError):
            continue
        if c <= 0.0 or math.isnan(c):
            continue

        ws = obs.get("wind_speed")
        if ws is None:
            ws = obs.get("speed")
        if ws is not None:
            try:
                f_ws = float(ws)
                if f_ws < calm_threshold or math.isnan(f_ws):
                    continue
            except (ValueError, TypeError):
                continue

        valid_c.append(c)

    if not valid_c:
        return 0.0

    return float(np.percentile(valid_c, 75))


def calculate_cpf_rose(
    observations: List[Dict[str, Any]],
    threshold_p75: Optional[float] = None,
    calm_threshold: float = CALM_WIND_THRESHOLD_MS,
    min_samples: int = MIN_SECTOR_SAMPLES,
) -> Dict[str, Any]:
    """
    Calculates 16-sector Conditional Probability Function (CPF) polar rose
    (TRANSFORMATION_LOGIC_SPEC.md §2.5.2).
    
    Algorithm:
    1. Filter aerodynamic calm observations (wind_speed < 0.5 m/s) and track calm_ratio.
    2. If threshold_p75 is not provided, evaluate P75 over pooled valid non-calm hours.
    3. Bin non-calm observations into 16 directional sectors (22.5 deg width).
    4. Count total valid hours Nk and exceedance hours mk (C > threshold_p75) per sector.
    5. Small-Sample Suppression:
       If Nk >= 6: CPF_k = round(mk / Nk, 4)
       If Nk < 6:  CPF_k = None (prevents false 100% spikes from 1-2 chance events)
       
    Args:
        observations: List of observation dicts containing 'value' (concentration),
                      'wind_speed', and 'wind_direction'.
        threshold_p75: Optional precomputed P75 threshold. If None, derived from observations.
        calm_threshold: Wind speed cutoff in m/s (default: 0.5 m/s).
        min_samples: Minimum observations required per sector (default: 6).
        
    Returns:
        Dict with keys:
            'sectors': List of 16 Optional[float] values (None if suppressed)
            'calm_ratio': float in [0.0, 1.0]
            'threshold': float (tau)
            'sector_counts': List of 16 integer observation counts
            'sector_exceedances': List of 16 integer exceedance counts
    """
    total_obs = len(observations)
    if total_obs == 0:
        return {
            "sectors": [None] * DEFAULT_SECTOR_COUNT,
            "calm_ratio": 0.0,
            "threshold": threshold_p75 if threshold_p75 is not None else 0.0,
            "sector_counts": [0] * DEFAULT_SECTOR_COUNT,
            "sector_exceedances": [0] * DEFAULT_SECTOR_COUNT,
        }

    # Derive tau if not supplied
    tau = threshold_p75 if threshold_p75 is not None else calculate_pooled_p75(observations, calm_threshold)

    calm_count = 0
    sector_n = [0] * DEFAULT_SECTOR_COUNT
    sector_m = [0] * DEFAULT_SECTOR_COUNT

    for obs in observations:
        val = obs.get("value")
        if val is None:
            val = obs.get("concentration")
        if val is None:
            continue
        try:
            c = float(val)
        except (ValueError, TypeError):
            continue
        if c <= 0.0 or math.isnan(c):
            continue

        ws = obs.get("wind_speed")
        if ws is None:
            ws = obs.get("speed")
        wd = obs.get("wind_direction")
        if wd is None:
            wd = obs.get("direction")

        if ws is None or math.isnan(float(ws)) or float(ws) < calm_threshold:
            calm_count += 1
            continue

        if wd is None or math.isnan(float(wd)):
            continue

        f_ws = float(ws)
        f_wd = float(wd)

        sector_idx = degrees_to_sector_16(f_wd)
        sector_n[sector_idx] += 1
        if c > tau:
            sector_m[sector_idx] += 1

    calm_ratio = calm_count / total_obs if total_obs > 0 else 0.0

    sectors: List[Optional[float]] = []
    for k in range(DEFAULT_SECTOR_COUNT):
        if sector_n[k] >= min_samples:
            sectors.append(round(sector_m[k] / sector_n[k], 4))
        else:
            sectors.append(None)  # Small-sample suppression

    return {
        "sectors": sectors,
        "calm_ratio": round(calm_ratio, 4),
        "threshold": round(tau, 4),
        "sector_counts": sector_n,
        "sector_exceedances": sector_m,
    }


def calculate_rose_geometry(
    cpf_sectors: List[Optional[float]],
    radius: float = 100.0,
    muted_stub_px: float = 10.0,
) -> List[Dict[str, Any]]:
    """
    Generates sector polygon wedge coordinates for rendering polar wind roses on canvas
    (TRANSFORMATION_LOGIC_SPEC.md §2.5.2 geometry).
    
    Formula:
        a_start = (k * 22.5 - 11.25 - 90) * pi / 180
        a_end = a_start + 22.5 * pi / 180
        r_k = max(2.0, R * min(1.0, CPF_k / 0.80)) if CPF_k is not None else 10.0 px
    """
    geometry: List[Dict[str, Any]] = []
    for k in range(min(DEFAULT_SECTOR_COUNT, len(cpf_sectors))):
        val = cpf_sectors[k]
        a_start = math.radians(k * 22.5 - 11.25 - 90.0)
        a_end = a_start + math.radians(22.5)

        if val is not None:
            r_k = max(2.0, radius * min(1.0, val / 0.80))
            is_suppressed = False
        else:
            r_k = muted_stub_px
            is_suppressed = True

        geometry.append({
            "sector": k,
            "a_start_rad": a_start,
            "a_end_rad": a_end,
            "radius_px": round(r_k, 2),
            "cpf_value": val,
            "is_suppressed": is_suppressed,
        })

    return geometry
