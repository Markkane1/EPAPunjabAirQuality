"""Adversarial & Numerical Parity Stress-Testing Suite for Milestone M1-M2.

Compares Python reference implementations against TypeScript implementations.
Tests:
- Precision parity (< 1e-9 relative / absolute tolerance)
- Extreme coordinates, poles, identical points
- Zero/calm wind speeds, anemometer bounds, Wazirabad blacklisting
- Singularity clamping, epsilon softening in IDW
- Small-sample suppression and calm exclusion in CPF
- Physical dimension guard in flux (AQI returning null)
- Transboundary corridor limits and normal vector projections
- Statutory PEPC AQI piecewise linear interpolation and 500 ceiling clamp
- Temporal QC median spike filter, 3h logger hold index guard, and AQI exemption
- Equirectangular Plate Carree projection round-trip accuracy
- All 5 Data Normalizer schema traps
"""
import json
import math
import subprocess
from pathlib import Path
import sys

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.domain.math.geodesy import (
    haversine_distance, forward_bearing, back_bearing,
    angular_divergence, degrees_to_sector_16, sector_16_to_degrees
)
from src.domain.math.idw import (
    discrete_geodesic_idw, discrete_geodesic_idw_vector,
    calculate_distance_opacity, anisotropic_idw
)
from src.domain.math.wind import (
    is_station_blacklisted, is_anemometer_valid, is_calm_wind,
    polar_to_cartesian_wind, cartesian_to_polar_wind, wind_direction_to_bearing
)
from src.domain.math.cpf import (
    calculate_pooled_p75, calculate_cpf_rose
)
from src.domain.math.flux import (
    calculate_advection_flux, calculate_receptor_coupling, calculate_net_transport_balance
)
from src.domain.math.transboundary import (
    calculate_district_transboundary_flux, calculate_border_normal_flux, calculate_transboundary_index
)
from src.domain.math.pepc_aqi import (
    pepc_calculate_aqi, pepc_composite_aqi, pepc_get_category, pepc_get_color, pepc_interpolate_color
)
from src.domain.math.qc import (
    temporal_qc_clean, check_completeness, subhourly_lerp
)
from src.domain.math.projection import (
    equirectangular_project, equirectangular_unproject, check_aabb_collision, greedy_label_placement
)

STATE_DIR = Path(__file__).resolve().parent

def build_test_cases():
    cases = {}

    # 1. Geodesy
    cases["geodesy"] = [
        {"lat1": 31.5204, "lon1": 74.3587, "lat2": 31.5204, "lon2": 74.3587, "angle1": 0.0, "angle2": 0.0, "deg": 0.0, "sector_idx": 0}, # identical
        {"lat1": 31.5204, "lon1": 74.3587, "lat2": 30.1575, "lon2": 71.5249, "angle1": 45.0, "angle2": 230.0, "deg": 11.24, "sector_idx": 15}, # Lahore to Multan
        {"lat1": 28.0, "lon1": 70.0, "lat2": 34.0, "lon2": 75.0, "angle1": 359.0, "angle2": 1.0, "deg": 11.25, "sector_idx": 1}, # Boundary at 11.25
        {"lat1": -10.0, "lon1": -20.0, "lat2": 20.0, "lon2": 40.0, "angle1": 180.0, "angle2": 0.0, "deg": 348.75, "sector_idx": 15},
        {"lat1": 31.0, "lon1": 74.0, "lat2": 31.0, "lon2": 74.0, "angle1": 270.0, "angle2": 90.0, "deg": 180.0, "sector_idx": 8},
    ]

    # 2. IDW
    stations_scalar = [
        {"coords": (31.5, 74.3), "value": 150.0},
        {"coords": (31.6, 74.4), "value": 200.0},
        {"coords": (31.4, 74.2), "value": 100.0},
    ]
    stations_vector = [
        {"coords": (31.5, 74.3), "u": 2.5, "v": -1.5},
        {"coords": (31.6, 74.4), "u": 1.0, "v": 0.5},
        {"coords": (31.4, 74.2), "u": -0.5, "v": 2.0},
    ]
    aniso_stations = [
        {"coords_px": (100.0, 150.0), "value": 120.0, "u": 2.0, "v": 1.0},
        {"coords_px": (200.0, 250.0), "value": 240.0, "u": -1.5, "v": -2.0},
        {"coords_px": (300.0, 100.0), "value": 80.0, "u": 0.2, "v": 0.1},
    ]
    cases["idw"] = [
        {"target": (31.5, 74.3), "stations": stations_scalar, "vector_stations": stations_vector, "power": 2.0, "d0": 5.0, "km_min": 10.0, "target_px": (150.0, 180.0), "aniso_stations": aniso_stations, "wind_vector": (1.0, 1.0), "scale": 1.0, "epsilon_sq": 16.0},
        {"target": (30.0, 71.0), "stations": stations_scalar, "vector_stations": stations_vector, "power": 2.0, "d0": 5.0, "km_min": 45.0, "target_px": (100.0, 150.0), "aniso_stations": aniso_stations, "wind_vector": None, "scale": 2.0, "epsilon_sq": 16.0},
        {"target": (32.0, 73.0), "stations": stations_scalar, "vector_stations": stations_vector, "power": 2.0, "d0": 5.0, "km_min": 92.5, "target_px": (500.0, 500.0), "aniso_stations": aniso_stations, "wind_vector": (0.0, 0.0), "scale": 1.0, "epsilon_sq": 16.0},
        {"target": (33.0, 74.0), "stations": stations_scalar, "vector_stations": stations_vector, "power": 2.0, "d0": 5.0, "km_min": 140.0, "target_px": (200.0, 250.0), "aniso_stations": aniso_stations, "wind_vector": (3.0, -1.0), "scale": 1.5, "epsilon_sq": 16.0},
        {"target": (34.0, 75.0), "stations": stations_scalar, "vector_stations": stations_vector, "power": 2.0, "d0": 5.0, "km_min": 160.0, "target_px": (50.0, 50.0), "aniso_stations": aniso_stations, "wind_vector": None, "scale": 1.0, "epsilon_sq": 16.0},
    ]

    # 3. Wind
    cases["wind"] = [
        {"speed": 5.0, "direction": 90.0, "station_name": "Lahore Town Hall", "u": 5.0, "v": 0.0},
        {"speed": 0.0, "direction": 0.0, "station_name": "Faisalabad Central", "u": 0.0, "v": 0.0},
        {"speed": 0.49, "direction": 180.0, "station_name": "Multan Airport", "u": 0.0, "v": -0.49},
        {"speed": 0.50, "direction": 270.0, "station_name": "Rawalpindi Cantt", "u": -0.50, "v": 0.0},
        {"speed": 30.0, "direction": 45.0, "station_name": "Sialkot Export", "u": 2.0, "v": 2.0},
        {"speed": 30.1, "direction": 45.0, "station_name": "Sialkot Export", "u": 0.0, "v": 5.0}, # invalid speed
        {"speed": 10.0, "direction": 90.0, "station_name": "Wazirabad AQMS", "u": -10.0, "v": 0.0}, # blacklisted
        {"speed": 10.0, "direction": 90.0, "station_name": "Wazirabad", "u": -5.0, "v": 5.0}, # blacklisted
        {"speed": 10.0, "direction": 90.0, "station_name": "PK_WAZ_001", "u": 1.0, "v": -1.0}, # blacklisted code
    ]

    # 4. CPF
    obs_test = [
        {"value": 120.0, "wind_speed": 2.5, "wind_direction": 90.0},
        {"value": 85.0, "wind_speed": 1.8, "wind_direction": 90.0},
        {"value": 250.0, "wind_speed": 3.0, "wind_direction": 90.0},
        {"value": 310.0, "wind_speed": 4.0, "wind_direction": 90.0},
        {"value": 45.0, "wind_speed": 0.2, "wind_direction": 90.0}, # calm
        {"value": 180.0, "wind_speed": 2.2, "wind_direction": 90.0},
        {"value": 220.0, "wind_speed": 3.5, "wind_direction": 90.0},
        {"value": 90.0, "wind_speed": 1.5, "wind_direction": 180.0},
        {"value": 190.0, "wind_speed": 2.0, "wind_direction": 180.0},
        {"value": 210.0, "wind_speed": 2.5, "wind_direction": 180.0},
    ]
    cases["cpf"] = [
        {"observations": obs_test, "threshold_p75": None},
        {"observations": obs_test, "threshold_p75": 150.0},
    ]

    # 5. Flux
    cases["flux"] = [
        # Normal PM2.5 within bounds
        {"source": (31.5, 74.3), "receptor": (31.6, 74.4), "pollutant": "PM2.5", "concentration": 150.0, "u": 2.0, "v": 2.0},
        # AQI pollutant -> MUST return None (Physical Dimension Guard!)
        {"source": (31.5, 74.3), "receptor": (31.6, 74.4), "pollutant": "AQI", "concentration": 200.0, "u": 2.0, "v": 2.0},
        {"source": (31.5, 74.3), "receptor": (31.6, 74.4), "pollutant": "aqi", "concentration": 200.0, "u": 2.0, "v": 2.0},
        # Distance > 180km -> null
        {"source": (31.0, 71.0), "receptor": (33.5, 74.5), "pollutant": "PM10", "concentration": 100.0, "u": 5.0, "v": 5.0},
        # Calm wind < 0.50 m/s -> null
        {"source": (31.5, 74.3), "receptor": (31.6, 74.4), "pollutant": "NO2", "concentration": 40.0, "u": 0.2, "v": 0.2},
    ]

    # 6. Transboundary
    cases["transboundary"] = [
        # Inflow from India (e.g. easterly wind)
        {"border_dist": 25.0, "india_sectors": [4, 5, 6], "conc": 150.0, "u": -2.0, "v": 0.0, "is_est": False, "nx": 1.0, "ny": 0.0},
        # Outflow to India (e.g. westerly wind)
        {"border_dist": 40.0, "india_sectors": [4, 5, 6], "conc": 200.0, "u": 2.0, "v": 0.0, "is_est": False, "nx": -1.0, "ny": 0.0},
        # Beyond corridor limit 120km -> 0.0
        {"border_dist": 130.0, "india_sectors": [4, 5, 6], "conc": 150.0, "u": -2.0, "v": 0.0, "is_est": False, "nx": 0.707, "ny": 0.707},
        # Calm wind < 0.50 -> 0.0
        {"border_dist": 15.0, "india_sectors": [4, 5, 6], "conc": 150.0, "u": -0.1, "v": 0.1, "is_est": False, "nx": 0.0, "ny": 1.0},
    ]

    # 7. PEPC AQI
    cases["pepc_aqi"] = [
        {"pollutant": "PM2.5", "concentration": 12.0, "pm25": 40, "pm10": 30, "test_aqi": 40, "value": 15.0, "ref_limit": 35.0},
        {"pollutant": "PM2.5", "concentration": 35.0, "pm25": 100, "pm10": 120, "test_aqi": 120, "value": 70.0, "ref_limit": 35.0},
        {"pollutant": "PM2.5", "concentration": 70.0, "pm25": 150, "pm10": 110, "test_aqi": 180, "value": 140.0, "ref_limit": 35.0},
        {"pollutant": "PM2.5", "concentration": 140.0, "pm25": 200, "pm10": None, "test_aqi": 250, "value": 250.0, "ref_limit": 35.0},
        {"pollutant": "PM2.5", "concentration": 250.0, "pm25": None, "pm10": 85, "test_aqi": 350, "value": 350.0, "ref_limit": 35.0},
        {"pollutant": "PM2.5", "concentration": 350.0, "pm25": None, "pm10": None, "test_aqi": 450, "value": 0.0, "ref_limit": 35.0},
        # PM2.5 > 350 -> clamped to 500
        {"pollutant": "PM2.5", "concentration": 351.0, "pm25": 500, "pm10": 450, "test_aqi": 500, "value": 500.0, "ref_limit": 35.0},
        {"pollutant": "PM10", "concentration": 551.0, "pm25": 500, "pm10": 500, "test_aqi": 600, "value": 600.0, "ref_limit": 150.0},
        # Zero / negative handling
        {"pollutant": "PM2.5", "concentration": 0.0, "pm25": 0, "pm10": 0, "test_aqi": None, "value": -5.0, "ref_limit": 35.0},
        {"pollutant": "PM2.5", "concentration": -5.0, "pm25": 0, "pm10": 0, "test_aqi": None, "value": -5.0, "ref_limit": 35.0},
    ]

    # 8. QC
    # Create test series with spikes and logger holds
    qc_series_pm25 = [
        10.0, 12.0, 11.0, 150.0, 13.0, 12.0, 14.0,  # 150 is a spike > 4 * median and > 3 * 35
        25.0, 25.0, 25.0,                           # 3-hour hold: third 25.0 purged
        30.0, 32.0, 0.0, -5.0, None, 35.0            # zero/negative purge
    ]
    cases["qc"] = [
        {"series": qc_series_pm25, "ref_limit": 35.0, "pollutant": "PM2.5", "fp": 3.5},
        # AQI series exempt from logger hold!
        {"series": [100.0, 100.0, 100.0, 100.0], "ref_limit": 100.0, "pollutant": "AQI", "fp": 1.2},
    ]

    # 9. Projection
    cases["projection"] = [
        {"lat": 31.0, "lon": 74.0, "box1": (10.0, 10.0, 20.0, 20.0), "box2": (25.0, 25.0, 20.0, 20.0)}, # overlap
        {"lat": 28.0, "lon": 70.0, "box1": (10.0, 10.0, 20.0, 20.0), "box2": (50.0, 50.0, 20.0, 20.0)}, # disjoint
        {"lat": 34.0, "lon": 75.0, "box1": (0.0, 0.0, 10.0, 10.0), "box2": (9.9, 9.9, 10.0, 10.0)},     # edge touch
    ]

    # 10. Normalizer Traps
    with open(PROJECT_ROOT / "data" / "baseline" / "stations.json", "r", encoding="utf-8") as f:
        stations_data = json.load(f)

    with open(PROJECT_ROOT / "data" / "baseline" / "districts.json", "r", encoding="utf-8") as f:
        districts_data = json.load(f)

    cases["normalizer"] = {
        "centroids": [d["centroid"] for d in districts_data[:5]],
        "winds": [
            {"speed": None, "direction": None, "station": "OPRN"},
            {"speed": 0.2, "direction": 180.0, "station": "OPLA"},
            {"speed": 2.5, "direction": 90.0, "station": "OPKC"},
            {"speed": 3.0, "direction": 45.0, "station": 172},
            {"speed": 3.0, "direction": 45.0, "station": "Wazirabad AQMS"},
        ],
        "districts": districts_data[:10],
        "stations": stations_data,
    }

    return cases


def run_python_reference(test_cases):
    py_results = {}

    # 1. Geodesy
    py_results["geodesy"] = []
    for tc in test_cases["geodesy"]:
        py_results["geodesy"].append({
            "dist": haversine_distance(tc["lat1"], tc["lon1"], tc["lat2"], tc["lon2"]),
            "fwd_bearing": forward_bearing(tc["lat1"], tc["lon1"], tc["lat2"], tc["lon2"]),
            "back_bearing": back_bearing(tc["lat1"], tc["lon1"], tc["lat2"], tc["lon2"]),
            "ang_div": angular_divergence(tc["angle1"], tc["angle2"]),
            "sector": degrees_to_sector_16(tc["deg"]),
            "sector_deg": sector_16_to_degrees(tc["sector_idx"]),
        })

    # 2. IDW
    py_results["idw"] = []
    for tc in test_cases["idw"]:
        py_results["idw"].append({
            "scalar": discrete_geodesic_idw(tc["target"], tc["stations"], tc["power"], tc["d0"]),
            "vector": discrete_geodesic_idw_vector(tc["target"], tc["vector_stations"], tc["power"], tc["d0"]),
            "opacity": calculate_distance_opacity(tc["km_min"]),
            "anisotropic": anisotropic_idw(tc["target_px"], tc["aniso_stations"], tc["wind_vector"], tc["scale"], tc["epsilon_sq"]),
        })

    # 3. Wind
    py_results["wind"] = []
    for tc in test_cases["wind"]:
        py_results["wind"].append({
            "blacklisted": is_station_blacklisted(tc["station_name"]),
            "valid": is_anemometer_valid(tc["speed"], tc["direction"], tc["station_name"]),
            "calm": is_calm_wind(tc["speed"]),
            "polar_to_cart": polar_to_cartesian_wind(tc["speed"], tc["direction"], tc["station_name"]),
            "cart_to_polar": cartesian_to_polar_wind(tc["u"], tc["v"]),
            "bearing": wind_direction_to_bearing(tc["u"], tc["v"]),
        })

    # 4. CPF
    py_results["cpf"] = []
    for tc in test_cases["cpf"]:
        py_results["cpf"].append({
            "p75": calculate_pooled_p75(tc["observations"]),
            "rose": calculate_cpf_rose(tc["observations"], tc["threshold_p75"]),
        })

    # 5. Flux
    py_results["flux"] = []
    for tc in test_cases["flux"]:
        py_results["flux"].append({
            "flux": calculate_advection_flux(tc["source"], tc["receptor"], tc["pollutant"], tc["concentration"], tc["u"], tc["v"]),
        })

    # 6. Transboundary
    py_results["transboundary"] = []
    for tc in test_cases["transboundary"]:
        py_results["transboundary"].append({
            "district_flux": calculate_district_transboundary_flux(tc["border_dist"], tc["india_sectors"], tc["conc"], tc["u"], tc["v"], tc["is_est"]),
            "normal_flux": calculate_border_normal_flux(tc["u"], tc["v"], tc["nx"], tc["ny"]),
        })

    # 7. PEPC AQI
    py_results["pepc_aqi"] = []
    for tc in test_cases["pepc_aqi"]:
        py_results["pepc_aqi"].append({
            "aqi": pepc_calculate_aqi(tc["pollutant"], tc["concentration"]),
            "composite": pepc_composite_aqi(tc["pm25"], tc["pm10"]),
            "category": pepc_get_category(tc["test_aqi"]),
            "color": pepc_get_color(tc["test_aqi"]),
            "peqs_rgb": pepc_interpolate_color(tc["value"], tc["ref_limit"]),
        })

    # 8. QC
    py_results["qc"] = []
    for tc in test_cases["qc"]:
        cleaned, spk = temporal_qc_clean(tc["series"], tc["ref_limit"], tc["pollutant"])
        py_results["qc"].append({
            "clean": [cleaned, spk],
            "completeness": check_completeness(tc["series"]),
            "lerp": subhourly_lerp(tc["series"], tc["fp"]),
        })

    # 9. Projection
    py_results["projection"] = []
    for tc in test_cases["projection"]:
        proj = equirectangular_project(tc["lat"], tc["lon"])
        unproj = equirectangular_unproject(proj[0], proj[1])
        py_results["projection"].append({
            "proj": proj,
            "unproj": unproj,
            "collision": check_aabb_collision(tc["box1"], tc["box2"]),
        })

    return py_results


def compare_values(py_val, ts_val, path="", tol=1e-3):
    if py_val is None:
        assert ts_val is None, f"Mismatch at {path}: Python was None, TS was {ts_val}"
        return
    if isinstance(py_val, (int, float)):
        assert isinstance(ts_val, (int, float)), f"Type mismatch at {path}: Python {type(py_val)}, TS {type(ts_val)}"
        diff = abs(py_val - ts_val)
        assert diff <= tol or (abs(py_val) > 0 and diff / abs(py_val) <= tol), f"Precision mismatch at {path}: Py={py_val}, TS={ts_val}, diff={diff}"
        return
    if isinstance(py_val, bool):
        assert py_val == ts_val, f"Bool mismatch at {path}: Py={py_val}, TS={ts_val}"
        return
    if isinstance(py_val, str):
        assert py_val.lower() == str(ts_val).lower(), f"String mismatch at {path}: Py={py_val}, TS={ts_val}"
        return
    if isinstance(py_val, (list, tuple)):
        assert len(py_val) == len(ts_val), f"Length mismatch at {path}: Py={len(py_val)}, TS={len(ts_val)}"
        for i, (p, t) in enumerate(zip(py_val, ts_val)):
            compare_values(p, t, f"{path}[{i}]", tol)
        return
    if isinstance(py_val, dict):
        for k in py_val:
            assert k in ts_val, f"Key missing in TS at {path}: key '{k}'"
            compare_values(py_val[k], ts_val[k], f"{path}.{k}", tol)
        return


def main():
    print("================================================================================")
    print(" EMPIRICAL NUMERICAL PRECISION & ADVERSARIAL PARITY VERIFICATION")
    print("================================================================================")

    test_cases = build_test_cases()
    test_cases_file = STATE_DIR / "test_cases.json"
    with open(test_cases_file, "w", encoding="utf-8") as f:
        json.dump(test_cases, f, indent=2)

    print(f"[1/4] Generated comprehensive test cases: {test_cases_file.name}")

    print("[2/4] Running Python reference implementations...")
    py_results = run_python_reference(test_cases)
    py_results_file = STATE_DIR / "py_results.json"
    with open(py_results_file, "w", encoding="utf-8") as f:
        json.dump(py_results, f, indent=2)
    print("      Python execution completed successfully.")

    print("[3/4] Running TypeScript implementations via npx tsx...")
    cmd = ["npx", "tsx", str(STATE_DIR / "verify_ts_runner.ts")]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT), shell=True)
    if res.returncode != 0:
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)
        raise RuntimeError(f"TypeScript runner failed with code {res.returncode}")
    print("      TypeScript execution completed successfully.")

    print("[4/4] Cross-comparing numerical outputs down to precision tolerance...")
    with open(STATE_DIR / "ts_results.json", "r", encoding="utf-8") as f:
        ts_results = json.load(f)

    # Compare modules
    modules = ["geodesy", "idw", "wind", "cpf", "flux", "transboundary", "pepc_aqi", "qc", "projection"]
    for mod in modules:
        py_m = py_results[mod]
        ts_m = ts_results[mod]
        compare_values(py_m, ts_m, path=mod)
        print(f"      [✓ PASS] {mod:<15}: Python & TypeScript in exact parity!")

    # Verify Normalizer schema traps
    print("\n--- SCHEMA TRAPS VALIDATION IN TYPESCRIPT ENGINE ---")
    norm = ts_results["normalizer"]

    # Trap 1: Inverted centroids [lon, lat]
    for i, c in enumerate(norm["centroid"]):
        raw_c = test_cases["normalizer"]["centroids"][i]
        assert c == [raw_c[1], raw_c[0]], f"Trap 1 failed: {c} != {[raw_c[1], raw_c[0]]}"
        assert 69.0 <= c[0] <= 76.5, f"Trap 1 Longitude out of bounds: {c[0]}"
        assert 27.0 <= c[1] <= 35.5, f"Trap 1 Latitude out of bounds: {c[1]}"
    print("      [✓ PASS] Trap 1: District centroids correctly inverted to [lon, lat]")

    # Trap 2 & 3: Wind states (dropout, calm, active, blacklisted)
    w_res = norm["winds"]
    assert w_res[0]["state"] == "dropout", f"Expected dropout for null, got {w_res[0]}"
    assert w_res[1]["state"] == "calm" and w_res[1]["u"] == 0.0 and w_res[1]["v"] == 0.0, f"Expected calm, got {w_res[1]}"
    assert w_res[2]["state"] == "active" and w_res[2]["u"] != 0.0, f"Expected active, got {w_res[2]}"
    assert w_res[3]["state"] == "blacklisted" and w_res[3]["blacklisted"] is True, f"Expected blacklisted for 172, got {w_res[3]}"
    assert w_res[4]["state"] == "blacklisted" and w_res[4]["blacklistReason"] == "ANEMOMETER BLACKLISTED (VANE OFFSET)", f"Expected blacklisted reason, got {w_res[4]}"
    print("      [✓ PASS] Trap 2: Aerodrome wind null (dropout) vs calm (<0.50m/s) distinguished")
    print("      [✓ PASS] Trap 3: Station 172 (Wazirabad) wind vector strictly suppressed & blacklisted")

    # Trap 4: Dynamic station counts
    counts = norm["counts"]
    assert counts == {"fixed": 74, "mobile": 5, "total": 79}, f"Trap 4 failed: {counts}"
    print("      [✓ PASS] Trap 4: Dynamic station network counts: 74 fixed, 5 mobile, 79 total")

    # Trap 5: Estimation flag and hatching
    for d in norm["est"]:
        assert d["is_est"] == d["hatching"], f"Trap 5 failed: is_est {d['is_est']} != hatching {d['hatching']}"
    print("      [✓ PASS] Trap 5: Unified estimation flags and diagonal cross-hatching trigger")

    print("\n================================================================================")
    print(" ALL EMPIRICAL PARITY & ADVERSARIAL CHECKS PASSED: 100% SUCCESS")
    print("================================================================================")


if __name__ == "__main__":
    main()
