"""Pytest empirical challenger suite executing the TypeScript verification harness
and cross-verifying Python domain math against the 5 mandated challenge areas.
"""
import subprocess
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def test_typescript_empirical_challenger_suite():
    """Executes the 2,091-assertion TypeScript stress test suite via tsx."""
    ts_test_file = PROJECT_ROOT / "tests" / "unit" / "test_challenger_m1m2.ts"
    assert ts_test_file.exists(), f"Missing {ts_test_file}"

    cmd = f'npx tsx "{ts_test_file}"'
    res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, shell=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr, file=sys.stderr)
    assert res.returncode == 0, f"TypeScript empirical challenger suite failed:\n{res.stdout}\n{res.stderr}"

def test_physical_dimension_guard_in_flux_python():
    """Empirically tests physical dimension guard in Python flux.py."""
    import math
    from src.domain.math.flux import calculate_advection_flux
    from src.domain.math.geodesy import forward_bearing

    lahore = (31.5204, 74.3587)
    gujranwala = (32.1877, 74.1945)

    brg = forward_bearing(lahore[0], lahore[1], gujranwala[0], gujranwala[1])
    rad = math.radians(brg)
    u_aligned = 5.0 * math.sin(rad)
    v_aligned = 5.0 * math.cos(rad)

    # AQI must return None
    for aqi_var in ["AQI", "aqi", " Aqi ", "AQI "]:
        res = calculate_advection_flux(lahore, gujranwala, aqi_var, 250.0, u_aligned, v_aligned)
        assert res is None, f"Expected None for pollutant {aqi_var}"

    # PM2.5 must return valid flux result when aligned in cone
    pm25_res = calculate_advection_flux(lahore, gujranwala, "PM2.5", 100.0, u_aligned, v_aligned)
    assert pm25_res is not None
    assert pm25_res["flux"] > 0.0

def test_pepc_ceiling_clamp_and_intervals_python():
    """Empirically tests 500 ceiling clamp and continuous intervals in Python pepc_aqi.py."""
    from src.domain.math.pepc_aqi import pepc_calculate_aqi

    # Ceiling clamp for PM2.5 > 350
    assert pepc_calculate_aqi("PM2.5", 350.1) == 500
    assert pepc_calculate_aqi("PM2.5", 500.0) == 500
    assert pepc_calculate_aqi("PM2.5", 1000.0) == 500

    # Half-open intervals
    assert pepc_calculate_aqi("PM2.5", 0.0) == 0
    assert pepc_calculate_aqi("PM2.5", 15.0) == 50
    assert pepc_calculate_aqi("PM2.5", 35.0) == 100
    assert pepc_calculate_aqi("PM2.5", 70.0) == 150
    assert pepc_calculate_aqi("PM2.5", 140.0) == 200
    assert pepc_calculate_aqi("PM2.5", 250.0) == 300
    assert pepc_calculate_aqi("PM2.5", 350.0) == 400

def test_temporal_qc_spike_and_logger_hold_python():
    """Empirically tests 7h spike filter and 3h logger hold with AQI exemption in Python qc.py."""
    from src.domain.math.qc import temporal_qc_clean

    ref_pm25 = 35.0

    # Spike filter: 600 is > 4*50=200 and > 3*35=105
    series_spike = [50, 50, 50, 50, 600, 50, 50, 50]
    cleaned_spike, n_spikes = temporal_qc_clean(series_spike, ref_pm25, "PM2.5")
    assert n_spikes == 1
    assert cleaned_spike[4] is None

    # Logger hold: 3 consecutive 50s at index 4 -> None for physical pollutant
    series_hold = [10, 20, 50, 50, 50, 60]
    cleaned_hold, _ = temporal_qc_clean(series_hold, ref_pm25, "PM2.5")
    assert cleaned_hold[4] is None

    # Logger hold AQI exemption: 6 consecutive 150s remain 150
    series_aqi = [150, 150, 150, 150, 150, 150]
    cleaned_aqi, _ = temporal_qc_clean(series_aqi, ref_pm25, "AQI")
    assert cleaned_aqi[4] == 150
    assert cleaned_aqi[5] == 150
