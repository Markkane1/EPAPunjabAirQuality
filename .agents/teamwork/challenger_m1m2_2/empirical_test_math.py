import math
import sys
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(root))

from src.domain.math.idw import discrete_geodesic_idw, DEFAULT_D0_CLAMP_KM
from src.domain.math.projection import KX_MERIDIONAL, equirectangular_project, equirectangular_unproject, STANDARD_PARALLEL_DEG
from src.domain.math.cpf import calculate_cpf_rose, MIN_SECTOR_SAMPLES
from src.domain.math.qc import check_completeness, DEFAULT_COMPLETENESS_RATIO
from src.domain.math.geodesy import haversine_distance

def test_idw_singularity_clamp():
    print("=== 1. DISCRETE GEODESIC IDW SINGULARITY CLAMP TEST ===")
    target = (31.5204, 74.3587)  # Lahore
    stA = {'coords': (31.5204, 74.3587), 'value': 100.0}  # d = 0.0
    stB = {'coords': (31.5204 + 0.09, 74.3587), 'value': 50.0}
    dist_B = haversine_distance(target[0], target[1], stB['coords'][0], stB['coords'][1])
    print(f"Distance stA: 0.0 km, Distance stB: {dist_B:.4f} km")

    expected_wA = 1.0 / (5.0 ** 2)
    expected_wB = 1.0 / (dist_B ** 2)
    expected_val = (expected_wA * 100.0 + expected_wB * 50.0) / (expected_wA + expected_wB)

    val_clamped = discrete_geodesic_idw(target, [stA, stB], power=2.0, d0=5.0)
    print(f"IDW result with d0=5.0: {val_clamped:.6f}, Expected: {expected_val:.6f}")
    assert abs(val_clamped - expected_val) < 1e-5, f"Mismatch: {val_clamped} vs {expected_val}"

    # Single station at d = 0
    val_single = discrete_geodesic_idw(target, [stA], power=2.0, d0=5.0)
    print(f"Single station at d=0: {val_single}")
    assert val_single == 100.0, "Single station should return station value"

    # Multi-station with d < d0 (e.g. d = 2.0 km)
    stC = {'coords': (31.5204 + 0.018, 74.3587), 'value': 80.0}
    dist_C = haversine_distance(target[0], target[1], stC['coords'][0], stC['coords'][1])
    print(f"Distance stC: {dist_C:.4f} km (< d0=5.0 km)")
    # Both stA and stC have d < 5.0, so both should be clamped to dEff = 5.0 km
    # wA = 1/25, wC = 1/25 -> expected average = (100 + 80) / 2 = 90.0
    val_sub_d0 = discrete_geodesic_idw(target, [stA, stC], power=2.0, d0=5.0)
    print(f"IDW result with both d < d0: {val_sub_d0:.6f}, Expected: 90.0")
    assert abs(val_sub_d0 - 90.0) < 1e-5, f"Mismatch: {val_sub_d0} vs 90.0"

    print("IDW Singularity Clamp: PASSED\n")

def test_plate_carree_aspect_ratio():
    print("=== 2. PLATE CARREE ASPECT RATIO K_X = cos 31° TEST ===")
    cos_31 = math.cos(math.radians(31.0))
    print(f"Theoretical cos(31 deg): {cos_31:.10f}")
    print(f"KX_MERIDIONAL in code:   {KX_MERIDIONAL:.10f}")
    assert abs(KX_MERIDIONAL - cos_31) < 1e-12, "KX_MERIDIONAL mismatch!"

    # Forward & inverse projection roundtrip
    pt = (31.5, 74.3)
    px = equirectangular_project(pt[0], pt[1], 1200.0, 900.0)
    unproj = equirectangular_unproject(px[0], px[1], 1200.0, 900.0)
    print(f"Forward project: {pt} -> {px}")
    print(f"Inverse project: {px} -> {unproj}")
    assert abs(pt[0] - unproj[0]) < 1e-5 and abs(pt[1] - unproj[1]) < 1e-5, "Roundtrip projection failed!"

    # Differential aspect ratio at latitude 31 deg
    p0 = equirectangular_project(31.0, 74.0, 1200.0, 900.0)
    p_lon = equirectangular_project(31.0, 75.0, 1200.0, 900.0)
    p_lat = equirectangular_project(32.0, 74.0, 1200.0, 900.0)
    dx_1deg = abs(p_lon[0] - p0[0])
    dy_1deg = abs(p_lat[1] - p0[1])
    aspect = dx_1deg / dy_1deg
    print(f"dx 1deg lon: {dx_1deg:.4f} px, dy 1deg lat: {dy_1deg:.4f} px, aspect dx/dy: {aspect:.10f}")
    assert abs(aspect - cos_31) < 1e-5, f"Aspect ratio does not match cos 31°! {aspect} vs {cos_31}"

    print("Plate Carrée aspect ratio: PASSED\n")

def test_cpf_suppression_and_calm():
    print("=== 3. CPF N_k < 6 SMALL SAMPLE SUPPRESSION & CALM EXCLUSION TEST ===")
    obs = []
    # 5 samples in Sector 0 (North, wd = 0 deg), speed = 2.0 m/s
    for _ in range(5):
        obs.append({'concentration': 100.0, 'wind_speed': 2.0, 'wind_direction': 0.0})

    # 6 samples in Sector 4 (East, wd = 90 deg), speed = 2.0 m/s (3 exceed tau=100)
    for _ in range(3):
        obs.append({'concentration': 200.0, 'wind_speed': 2.0, 'wind_direction': 90.0})
    for _ in range(3):
        obs.append({'concentration': 50.0, 'wind_speed': 2.0, 'wind_direction': 90.0})

    # 10 calm samples (ws = 0.2 m/s), wd = 0.0, conc = 300.0
    for _ in range(10):
        obs.append({'concentration': 300.0, 'wind_speed': 0.2, 'wind_direction': 0.0})

    res = calculate_cpf_rose(obs, threshold_p75=100.0)
    sec0 = res['sectors'][0]
    sec4 = res['sectors'][4]
    print(f"Sector 0 (N_k=5) result: {sec0} (Expected: None)")
    print(f"Sector 4 (N_k=6) result: {sec4} (Expected: 0.5)")
    assert sec0 is None, f"Sector 0 with Nk=5 should be suppressed! Got {sec0}"
    assert sec4 == 0.5, f"Sector 4 with Nk=6 should be 0.5! Got {sec4}"

    # Verify calm ratio
    expected_calm_ratio = round(10 / 21, 4)
    print(f"Calm ratio: {res['calm_ratio']}, Expected: {expected_calm_ratio}")
    assert abs(res['calm_ratio'] - expected_calm_ratio) < 1e-4, "Calm ratio mismatch!"

    print("CPF Small-Sample Suppression & Calm Exclusion: PASSED\n")

def test_completeness_rule():
    print("=== 4. 75% TEMPORAL COMPLETENESS RULE TEST ===")
    # H = 24h
    res_24_pass = check_completeness([10.0] * 18 + [None] * 6)
    res_24_fail = check_completeness([10.0] * 17 + [None] * 7)
    print(f"24h (18 valid / 24): {res_24_pass} (Expected: 10.0)")
    print(f"24h (17 valid / 24): {res_24_fail} (Expected: None)")
    assert res_24_pass == 10.0, "18/24 should pass"
    assert res_24_fail is None, "17/24 should fail"

    # H = 7h: round(0.75 * 7) = round(5.25) = 5
    res_7_pass = check_completeness([20.0] * 5 + [None] * 2)
    res_7_fail = check_completeness([20.0] * 4 + [None] * 3)
    print(f"7h (5 valid / 7): {res_7_pass} (Expected: 20.0)")
    print(f"7h (4 valid / 7): {res_7_fail} (Expected: None)")
    assert res_7_pass == 20.0, "5/7 should pass"
    assert res_7_fail is None, "4/7 should fail"

    # H = 1h: max(1, round(0.75 * 1)) = 1
    res_1_pass = check_completeness([15.0])
    res_1_fail = check_completeness([None])
    print(f"1h (1 valid / 1): {res_1_pass} (Expected: 15.0)")
    print(f"1h (0 valid / 1): {res_1_fail} (Expected: None)")
    assert res_1_pass == 15.0, "1/1 should pass"
    assert res_1_fail is None, "0/1 should fail"

    # H = 216h: round(0.75 * 216) = 162
    res_216_pass = check_completeness([50.0] * 162 + [None] * 54)
    res_216_fail = check_completeness([50.0] * 161 + [None] * 55)
    print(f"216h (162 valid / 216): {res_216_pass} (Expected: 50.0)")
    print(f"216h (161 valid / 216): {res_216_fail} (Expected: None)")
    assert res_216_pass == 50.0, "162/216 should pass"
    assert res_216_fail is None, "161/216 should fail"

    print("75% Completeness Rule: PASSED\n")

if __name__ == '__main__':
    test_idw_singularity_clamp()
    test_plate_carree_aspect_ratio()
    test_cpf_suppression_and_calm()
    test_completeness_rule()
    print("ALL PYTHON MATHEMATICAL SPECIFICATION TESTS PASSED SUCCESSFULLY!")
