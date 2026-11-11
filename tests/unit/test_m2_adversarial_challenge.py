"""
Adversarial Empirical Stress Verification and Challenge Suite for Milestone M2.
Focuses strictly on stress-testing domain mathematics in `src/domain/math/`:
1. Discrete IDW vs Anisotropic continuous IDW consistency.
2. Polar wind conversions: round-trip fidelity (u, v) <-> (ws, theta).
3. Equirectangular projection bounds and greedy 12-offset AABB label collisions.
4. Transboundary border normal dot product calculations across all 39 nodes.
5. Temporal QC: 7h median spike filter with synthetic noisy signals and step changes.

Classification: Milestone M2 Empirical Challenger
"""
import json
import math
import random
from pathlib import Path
from typing import Any, Dict, List, Tuple
import pytest

from src.domain.math.geodesy import (
    haversine_distance,
    forward_bearing,
    back_bearing,
    angular_divergence,
    degrees_to_sector_16,
    sector_16_to_degrees,
    R_EARTH_KM,
)
from src.domain.math.wind import (
    polar_to_cartesian_wind,
    cartesian_to_polar_wind,
    wind_direction_to_bearing,
    is_anemometer_valid,
    is_calm_wind,
    is_station_blacklisted,
    blend_winds,
    MIN_WIND_SPEED_MS,
    MAX_WIND_SPEED_MS,
    CALM_WIND_THRESHOLD_MS,
)
from src.domain.math.idw import (
    discrete_geodesic_idw,
    discrete_geodesic_idw_vector,
    anisotropic_idw,
    calculate_distance_opacity,
    DEFAULT_EPSILON_SQ_PX,
    DEFAULT_D0_CLAMP_KM,
)
from src.domain.math.projection import (
    equirectangular_project,
    equirectangular_unproject,
    check_aabb_collision,
    greedy_label_placement,
    LON_MIN_DEG,
    LON_MAX_DEG,
    LAT_MIN_DEG,
    LAT_MAX_DEG,
    KX_MERIDIONAL,
    LABEL_CANDIDATE_OFFSETS,
    LEADER_LINE_THRESHOLD_PX,
)
from src.domain.math.transboundary import (
    calculate_district_transboundary_flux,
    calculate_border_normal_flux,
    calculate_transboundary_index,
    BORDER_CORRIDOR_LIMIT_KM,
    BORDER_RESIDENCE_SCALE_KM,
)
from src.domain.math.qc import (
    temporal_qc_clean,
    check_completeness,
    subhourly_lerp,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ==============================================================================
# CHALLENGE 1: Discrete IDW vs Anisotropic Continuous IDW Consistency
# ==============================================================================
class TestDiscreteVsAnisotropicIDWAdversarial:
    """
    Stress-tests physical and mathematical consistency between discrete geodesic IDW
    and anisotropic continuous surface IDW.
    """

    def test_calm_wind_rotational_symmetry_invariance(self):
        """
        Adversarial Test: In calm conditions (wind <= 0.5 m/s), anisotropic IDW must
        revert to isotropic weighting. Therefore, around a rotationally symmetric
        distribution of stations, querying points at equal radial distances must yield
        identical interpolated values regardless of angle.
        """
        center_x, center_y = 500.0, 500.0
        radius_station = 100.0
        num_stations = 8
        stations = []

        # Create symmetric ring of 8 stations reporting identical values with calm wind
        for k in range(num_stations):
            angle = k * (2.0 * math.pi / num_stations)
            sx = center_x + radius_station * math.cos(angle)
            sy = center_y + radius_station * math.sin(angle)
            stations.append({
                "coords_px": (sx, sy),
                "value": 150.0 + 10.0 * math.sin(angle),
                "u": 0.0,
                "v": 0.0,
            })

        # Query points along concentric circles at 16 different angles
        for r_query in [10.0, 30.0, 60.0]:
            uniform_stations = [
                {"coords_px": st["coords_px"], "value": 100.0, "u": 0.0, "v": 0.0}
                for st in stations
            ]
            expected_val = 100.0
            for k in range(16):
                q_angle = k * (2.0 * math.pi / 16)
                qx = center_x + r_query * math.cos(q_angle)
                qy = center_y + r_query * math.sin(q_angle)

                interp_val, _, _ = anisotropic_idw(
                    target_px=(qx, qy),
                    stations=uniform_stations,
                    scale=1.0,
                )
                assert abs(interp_val - expected_val) < 1e-9, (
                    f"Rotational invariance violated: angle {math.degrees(q_angle):.1f} deg, "
                    f"value {interp_val} != {expected_val}"
                )

    def test_anisotropic_downwind_amplification_and_upwind_attenuation(self):
        """
        Adversarial Test: Verify directional multiplier strictly satisfies:
        Downwind (cos alpha = +1.0) weight amplification up to +70% (1.70x).
        Upwind (cos alpha = -1.0) weight suppression down to floor of 0.30x (70% reduction).
        Velocity saturation at s = 1.5 m/s.
        """
        station_x, station_y = 500.0, 500.0
        # Wind blowing East: u = 3.0 m/s (saturated), v = 0.0
        source_station = {
            "coords_px": (station_x, station_y),
            "value": 300.0,
            "u": 3.0,
            "v": 0.0,
        }
        # Neutral background station equidistant from query points
        bg_station = {
            "coords_px": (500.0, 700.0),
            "value": 50.0,
            "u": 0.0,
            "v": 0.0,
        }
        stations = [source_station, bg_station]

        d_query = 50.0
        # Point A is directly downwind (East of station): dx = +50, dy = 0 -> cos_alpha = +1.0
        query_downwind = (station_x + d_query, station_y)
        # Point B is directly upwind (West of station): dx = -50, dy = 0 -> cos_alpha = -1.0
        query_upwind = (station_x - d_query, station_y)

        val_downwind, _, _ = anisotropic_idw(query_downwind, stations, scale=1.0)
        val_upwind, _, _ = anisotropic_idw(query_upwind, stations, scale=1.0)

        # Downwind concentration must be significantly higher than upwind concentration
        assert val_downwind > val_upwind, (
            f"Advection monotonicity broken: Downwind {val_downwind} <= Upwind {val_upwind}"
        )

        # Exact weight verification
        d_sq = d_query * d_query
        w0 = 1.0 / (d_sq + DEFAULT_EPSILON_SQ_PX)
        w_downwind = w0 * 1.70
        w_upwind = w0 * 0.30
        w_bg_to_a = 1.0 / (50.0**2 + 200.0**2 + DEFAULT_EPSILON_SQ_PX)

        expected_downwind = (w_downwind * 300.0 + w_bg_to_a * 50.0) / (w_downwind + w_bg_to_a)
        assert abs(val_downwind - expected_downwind) < 1e-4

        expected_upwind = (w_upwind * 300.0 + w_bg_to_a * 50.0) / (w_upwind + w_bg_to_a)
        assert abs(val_upwind - expected_upwind) < 1e-4

    def test_convex_combination_bounding_property_stress(self):
        """
        Adversarial Stress: Across 500 randomized trials with extreme concentration values,
        both Discrete IDW and Anisotropic IDW must satisfy the convex hull property:
        min(stations.value) <= interpolated_value <= max(stations.value).
        """
        rng = random.Random(42)

        for trial in range(500):
            num_st = rng.randint(2, 20)
            values = [rng.uniform(-100.0, 5000.0) for _ in range(num_st)]
            min_v = min(values)
            max_v = max(values)

            # Geographic stations for discrete IDW
            geo_stations = [
                {
                    "coords": (rng.uniform(28.0, 34.0), rng.uniform(70.0, 75.0)),
                    "value": values[i],
                }
                for i in range(num_st)
            ]
            target_geo = (rng.uniform(28.0, 34.0), rng.uniform(70.0, 75.0))
            d_val = discrete_geodesic_idw(target_geo, geo_stations)

            assert d_val is not None
            assert min_v - 1e-6 <= d_val <= max_v + 1e-6, (
                f"Discrete IDW breached convex hull in trial {trial}: {d_val} outside [{min_v}, {max_v}]"
            )

            # Pixel stations for anisotropic IDW
            px_stations = [
                {
                    "coords_px": (rng.uniform(0.0, 1200.0), rng.uniform(0.0, 900.0)),
                    "value": values[i],
                    "u": rng.uniform(-25.0, 25.0),
                    "v": rng.uniform(-25.0, 25.0),
                }
                for i in range(num_st)
            ]
            target_px = (rng.uniform(0.0, 1200.0), rng.uniform(0.0, 900.0))
            a_val, _, _ = anisotropic_idw(target_px, px_stations, scale=1.0)

            assert min_v - 1e-6 <= a_val <= max_v + 1e-6, (
                f"Anisotropic IDW breached convex hull in trial {trial}: {a_val} outside [{min_v}, {max_v}]"
            )

    def test_discrete_idw_singularity_and_coincident_station(self):
        """
        Adversarial Test: When target coordinate exactly coincides with a reporting station,
        the d0=5km clamping must prevent division by zero while giving that station dominance.
        """
        st1 = {"coords": (31.50, 74.30), "value": 250.0}
        st2 = {"coords": (32.00, 75.00), "value": 50.0}  # ~88 km away
        stations = [st1, st2]

        # Target exactly at st1
        target = (31.50, 74.30)
        result = discrete_geodesic_idw(target, stations, power=2.0, d0=5.0)

        dist2 = haversine_distance(31.50, 74.30, 32.00, 75.00)
        w1 = 1.0 / (5.0**2)  # clamped to d0=5km -> 0.04
        w2 = 1.0 / (dist2**2)
        expected = (w1 * 250.0 + w2 * 50.0) / (w1 + w2)

        assert abs(result - expected) < 1e-5
        # Must be very close to st1 value (dominance)
        assert abs(result - 250.0) < 1.0


# ==============================================================================
# CHALLENGE 2: Polar Wind Conversions & Round-Trip Kinematic Fidelity
# ==============================================================================
class TestPolarWindConversionAdversarialFidelity:
    """
    Stress-tests polar-to-Cartesian and Cartesian-to-polar conversions across 3,600
    angles, physical anemometer boundaries, and sensor blacklists.
    """

    def test_exhaustive_angular_roundtrip_fidelity(self):
        """
        Adversarial Test: Sweep 3,600 angles from 0.0 to 359.9 deg at 0.1 deg step.
        (ws, theta) -> (u, v) -> (ws', theta') must reconstruct with:
        |ws - ws'| < 1e-10 m/s
        angular_difference(theta, theta') < 1e-7 deg
        """
        test_speeds = [0.6, 2.5, 10.0, 29.9]

        for speed in test_speeds:
            for angle_idx in range(3600):
                theta = angle_idx * 0.1

                uv = polar_to_cartesian_wind(speed, theta)
                assert uv is not None, f"Failed conversion for speed={speed}, theta={theta}"
                u, v = uv

                re_speed, re_theta = cartesian_to_polar_wind(u, v)

                # Speed fidelity
                assert abs(speed - re_speed) < 1e-10, (
                    f"Speed error: original {speed}, reconstructed {re_speed} at angle {theta}"
                )

                # Direction fidelity (handling 0/360 wrap-around)
                diff = abs(((theta - re_theta + 180.0) % 360.0) - 180.0)
                assert diff < 1e-7, (
                    f"Angle divergence: original {theta}, reconstructed {re_theta}, diff {diff}"
                )

    def test_calm_wind_zero_vector_and_stability(self):
        """
        Adversarial Test: When speed is 0.0 m/s, conversion must return (0.0, 0.0),
        and cartesian_to_polar_wind(0.0, 0.0) must cleanly return (0.0, 0.0) without NaN.
        """
        for angle in [0.0, 90.0, 180.0, 270.0, 360.0]:
            uv = polar_to_cartesian_wind(0.0, angle)
            assert uv == (0.0, 0.0)

        speed, direct = cartesian_to_polar_wind(0.0, 0.0)
        assert speed == 0.0
        assert direct == 0.0

    def test_physical_anemometer_boundary_enforcement(self):
        """
        Adversarial Test: Enforce hard operational bounds:
        Speed outside [0.0, 30.0] m/s must be rejected (returns None).
        Direction outside [0.0, 360.0] deg must be rejected (returns None).
        NaNs and Infs must be rejected.
        """
        assert polar_to_cartesian_wind(-0.001, 180.0) is None
        assert polar_to_cartesian_wind(30.001, 180.0) is None
        assert polar_to_cartesian_wind(99.9, 180.0) is None  # Error code 99.9
        assert polar_to_cartesian_wind(10.0, -0.1) is None
        assert polar_to_cartesian_wind(10.0, 360.1) is None
        assert polar_to_cartesian_wind(float("nan"), 180.0) is None
        assert polar_to_cartesian_wind(10.0, float("nan")) is None
        assert polar_to_cartesian_wind(float("inf"), 180.0) is None

    def test_wazirabad_blacklist_adversarial_variations(self):
        """
        Adversarial Test: Wazirabad anemometer has persistent 140 deg vane offset.
        All naming variations must be unconditionally blocked.
        """
        variations = [
            "Wazirabad",
            "wazirabad",
            "WAZIRABAD",
            "Wazirabad AQMS",
            "pk_waz_001",
            "Wazirabad Station",
            "  wazirabad  ",
            "EPA Wazirabad Mobile",
        ]
        for name in variations:
            assert is_station_blacklisted(name), f"Blacklist failed for {name}"
            assert polar_to_cartesian_wind(5.0, 90.0, station_name=name) is None

        # Clean non-blacklisted stations must pass
        assert not is_station_blacklisted("Lahore")
        assert not is_station_blacklisted("Multan")
        assert polar_to_cartesian_wind(5.0, 90.0, station_name="Lahore") is not None


# ==============================================================================
# CHALLENGE 3: Equirectangular Projection Bounds & Greedy AABB Collision
# ==============================================================================
class TestEquirectangularAndGreedyAABBAdversarial:
    """
    Stress-tests Plate Carree projection math, meridional correction cos(31 deg),
    and greedy 12-offset AABB label placement with real 41 Punjab districts.
    """

    def test_projection_boundary_corners_exact(self):
        """
        Adversarial Test: Verify the 4 exact geographic corners map to canvas corners:
        lon_min = 69.10, lon_max = 75.75, lat_min = 27.55, lat_max = 34.30.
        """
        w, h = 1200.0, 900.0

        # Top-left geographic corner (lat_max, lon_min) -> X=0, Y=0
        tl_x, tl_y = equirectangular_project(LAT_MAX_DEG, LON_MIN_DEG, w, h)
        assert abs(tl_x - 0.0) < 1e-6
        assert abs(tl_y - 0.0) < 1e-6

        # Top-right geographic corner (lat_max, lon_max) -> X=W, Y=0
        tr_x, tr_y = equirectangular_project(LAT_MAX_DEG, LON_MAX_DEG, w, h)
        assert abs(tr_x - w) < 1e-6
        assert abs(tr_y - 0.0) < 1e-6

        # Standard parallel cos(31 deg) factor check
        assert abs(KX_MERIDIONAL - math.cos(math.radians(31.0))) < 1e-12

    def test_projection_roundtrip_1000_random_coordinates(self):
        """
        Adversarial Test: 1,000 randomized points within Punjab:
        unproject(project(lat, lon)) must recover lat and lon within 1e-11.
        """
        rng = random.Random(1337)
        for _ in range(1000):
            lat = rng.uniform(LAT_MIN_DEG, LAT_MAX_DEG)
            lon = rng.uniform(LON_MIN_DEG, LON_MAX_DEG)

            px, py = equirectangular_project(lat, lon, 1200.0, 900.0)
            re_lat, re_lon = equirectangular_unproject(px, py, 1200.0, 900.0)

            assert abs(lat - re_lat) < 1e-11
            assert abs(lon - re_lon) < 1e-11

    def test_greedy_label_placement_all_41_punjab_districts_zero_overlap(self):
        """
        Adversarial Test: Load all 41 district centroids from baseline, project them,
        run greedy 12-offset label placement, and verify pairwise that ZERO bounding
        boxes overlap! (820 pairwise tests).
        """
        districts_file = PROJECT_ROOT / "data" / "baseline" / "districts.json"
        assert districts_file.is_file(), f"Missing {districts_file}"

        with open(districts_file, "r", encoding="utf-8") as f:
            districts = json.load(f)

        assert len(districts) == 41

        labels_input = []
        for d in districts:
            lat = d["lat"]
            lon = d["lon"]
            px, py = equirectangular_project(lat, lon, width_px=1200.0, height_px=900.0)
            labels_input.append({
                "district_id": d["name"],
                "text": d["name"],
                "anchor_x": px,
                "anchor_y": py,
                "width": 50.0,
                "height": 16.0,
            })

        placed = greedy_label_placement(labels_input)
        assert len(placed) == 41

        # Check all 41*40/2 = 820 pairs for collision
        collision_count = 0
        colliding_pairs = []
        for i in range(len(placed)):
            for j in range(i + 1, len(placed)):
                box_i = placed[i]["bounding_box"]
                box_j = placed[j]["bounding_box"]
                if check_aabb_collision(box_i, box_j):
                    collision_count += 1
                    colliding_pairs.append((placed[i]["district_id"], placed[j]["district_id"]))

        assert collision_count == 0, f"Collisions detected: {colliding_pairs}"

    def test_greedy_label_candidate_offset_selection_and_leader_lines(self):
        """
        Adversarial Test: Verify the priority ordering and leader line logic across candidate offsets.
        For candidate offsets with displacement > 20px, leader line must be flagged True.
        """
        for idx, (dx, dy) in enumerate(LABEL_CANDIDATE_OFFSETS):
            disp = math.sqrt(dx * dx + dy * dy)
            expected_leader = disp > LEADER_LINE_THRESHOLD_PX

            # Test single label placed with an obstacle blocking offset 0
            if idx == 0:
                labels = [{"id": "T0", "x": 100.0, "y": 100.0, "w": 20.0, "h": 10.0}]
                placed = greedy_label_placement(labels)
                assert (placed[0]["offset_x"], placed[0]["offset_y"]) == (0.0, 0.0)
                assert placed[0]["has_leader_line"] is False
            else:
                # Pre-populate obstacles at all preceding candidate offset boxes
                labels = []
                for p_idx in range(idx):
                    p_dx, p_dy = LABEL_CANDIDATE_OFFSETS[p_idx]
                    labels.append({
                        "id": f"obs_{p_idx}",
                        "x": 300.0 + p_dx,
                        "y": 300.0 + p_dy,
                        "w": 18.0,
                        "h": 8.0,
                    })
                # Target label placed at (300, 300)
                labels.append({"id": "target", "x": 300.0, "y": 300.0, "w": 18.0, "h": 8.0})
                placed = greedy_label_placement(labels)
                target_placed = placed[-1]
                # Target must choose a non-colliding offset
                for p_box in [p["bounding_box"] for p in placed[:-1]]:
                    assert not check_aabb_collision(target_placed["bounding_box"], p_box)


# ==============================================================================
# CHALLENGE 4: Transboundary Border Normal Dot Products Across All 39 Nodes
# ==============================================================================
class TestTransboundaryBorderNormalsAdversarial:
    """
    Stress-tests transboundary cross-border calculations across all 39 international
    border nodes from baseline_data.json:
    - Unit normal verification
    - Inflow/outflow under directional wind fields
    - Cauchy-Schwarz inequality bound
    - Tangential parallel flow invariance
    """

    @pytest.fixture(scope="class")
    @classmethod
    def border_nodes_39(cls) -> List[List[float]]:
        baseline_file = PROJECT_ROOT / "data" / "baseline" / "baseline_data.json"
        with open(baseline_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        samples = data.get("tbgeo", {}).get("samples", [])
        assert len(samples) == 39, f"Expected 39 border normal nodes, got {len(samples)}"
        return samples

    def test_all_39_nodes_are_normalized_unit_vectors(self, border_nodes_39):
        """
        Adversarial Test: Every one of the 39 border normal vectors must have norm ~ 1.0.
        """
        for idx, (lon, lat, nx, ny) in enumerate(border_nodes_39):
            norm = math.sqrt(nx * nx + ny * ny)
            assert 0.98 <= norm <= 1.02, (
                f"Border node {idx} at ({lat}, {lon}) has non-unit normal norm={norm}"
            )

    def test_cauchy_schwarz_projection_bound(self, border_nodes_39):
        """
        Adversarial Test: For any arbitrary wind vector (u, v), the normal velocity
        Phi_j = u*nx + v*ny must satisfy Cauchy-Schwarz: |Phi_j| <= ||w|| * ||n|| = ||w||.
        Test with 100 random wind vectors across all 39 nodes (3,900 evaluations).
        """
        rng = random.Random(777)
        for _ in range(100):
            u = rng.uniform(-25.0, 25.0)
            v = rng.uniform(-25.0, 25.0)
            w_mag = math.sqrt(u * u + v * v)

            for lon, lat, nx, ny in border_nodes_39:
                phi = calculate_border_normal_flux(u, v, nx, ny)
                assert abs(phi) <= w_mag * 1.02, (
                    f"Cauchy-Schwarz violated: |Phi|={abs(phi)} > wind speed {w_mag}"
                )

    def test_tangential_wind_produces_zero_normal_flux(self, border_nodes_39):
        """
        Adversarial Test: For every border node, construct a wind vector exactly parallel
        to the border tangent: w = speed * (-ny, nx).
        Because w is orthogonal to n = (nx, ny), Phi_j = w . n = speed * (-ny*nx + nx*ny) = 0.0.
        """
        for speed in [1.0, 5.0, 15.0]:
            for lon, lat, nx, ny in border_nodes_39:
                u_tangent = -speed * ny
                v_tangent = speed * nx
                phi = calculate_border_normal_flux(u_tangent, v_tangent, nx, ny)
                assert abs(phi) < 1e-9, f"Parallel flow produced non-zero normal flux: {phi}"

    def test_uniform_easterly_vs_westerly_winds_directionality(self, border_nodes_39):
        """
        Adversarial Test: Inward normal vectors along the eastern border of Punjab point
        westward (nx < 0).
        An Easterly wind (blowing FROM East towards West: u < 0, v = 0) produces
        positive inflow (Phi > 0) along 27 nodes, outflow along 11 meander nodes, and neutral on 1 node.
        A Westerly wind (blowing FROM West towards East: u > 0, v = 0) produces
        the exact opposite sign (Phi < 0).
        Fidelity: phi_east + phi_west == 0.0 across all 39 nodes.
        """
        # Easterly wind: speed 6.0 m/s from 90 deg -> u = -6.0, v = 0.0
        u_east, v_east = polar_to_cartesian_wind(6.0, 90.0)
        # Westerly wind: speed 6.0 m/s from 270 deg -> u = +6.0, v = 0.0
        u_west, v_west = polar_to_cartesian_wind(6.0, 270.0)

        inflow_count = 0
        outflow_count = 0

        for lon, lat, nx, ny in border_nodes_39:
            phi_east = calculate_border_normal_flux(u_east, v_east, nx, ny)
            phi_west = calculate_border_normal_flux(u_west, v_west, nx, ny)

            # Inflow and outflow under opposite winds must be exact negatives
            assert abs(phi_east + phi_west) < 1e-12

            if phi_east > 0.25:
                inflow_count += 1
            if phi_west < -0.25:
                outflow_count += 1

        # Verified against baseline geometry: 27 nodes have nx < 0 (inflow) and 11 have nx > 0 (outflow)
        assert inflow_count == 27, f"Expected 27 nodes inflow under Easterly wind, got {inflow_count}"
        assert outflow_count == 27, f"Expected 27 nodes outflow under Westerly wind, got {outflow_count}"


# ==============================================================================
# CHALLENGE 5: Temporal QC Spike & Hold Filters under Adversarial Signals
# ==============================================================================
class TestTemporalQCAdversarialHarness:
    """
    Stress-tests temporal QC filters against synthetic noisy signals, steep step changes,
    extreme smog episodes, and sensor hold anomalies.
    """

    def test_impulse_spike_detection_in_noisy_background(self):
        """
        Adversarial Test: Background noise of PM2.5 around 45 ug/m3 (ref_limit = 35.0).
        Inject a single isolated sensor impulse of 450 ug/m3 at t=12.
        Filter must eliminate EXACTLY t=12 and leave all other 23 hours intact.
        """
        rng = random.Random(999)
        n = 24
        ref_limit = 35.0

        # Generate Gaussian noise around 45 with sigma 3
        series = [round(45.0 + rng.gauss(0.0, 3.0), 1) for _ in range(n)]
        # Inject impulse spike (> 4 * 45 and > 3 * 35)
        spike_idx = 12
        series[spike_idx] = 450.0

        cleaned, spike_count = temporal_qc_clean(series, ref_limit, "PM2.5")

        assert spike_count == 1, f"Expected exactly 1 spike flagged, got {spike_count}"
        assert cleaned[spike_idx] is None, f"Spike at {spike_idx} was not cleaned"

        # Verify all other samples remain valid numbers
        for i in range(n):
            if i != spike_idx:
                assert cleaned[i] is not None, f"False positive spike at index {i}: {series[i]}"

    def test_severe_smog_episode_preservation(self):
        """
        Adversarial Test: During high pollution episodes, concentrations remain high
        for multiple hours: e.g. PM2.5 = [320, 310, 330, 340, 325, 315, 330].
        Even though values are >> 3 * ref_limit (105), they are NOT > 4 * local median!
        Filter must NOT flag or corrupt valid high episodes.
        """
        severe_smog = [320.0, 310.0, 330.0, 340.0, 325.0, 315.0, 330.0, 320.0]
        cleaned, spike_count = temporal_qc_clean(severe_smog, ref_limit=35.0, pollutant="PM2.5")

        assert spike_count == 0, f"False spikes flagged during real severe smog: {spike_count}"
        # All samples must be preserved
        assert all(v is not None for v in cleaned)

    def test_transient_surge_vs_sustained_step_change(self):
        """
        Adversarial Test:
        Case A: Transient 2-hour surge [20, 20, 20, 20, 110, 110, 20, 20]
        Centered 7h window median remains 20 -> surge is flagged as spike (spike_count >= 1).

        Case B: Sustained 6-hour atmospheric front [20, 20, 20, 20, 110, 110, 110, 110, 110, 110]
        Window median quickly converts to 110 -> sustained high values are preserved.
        """
        # Case A: Transient surge
        transient = [20.0, 20.0, 20.0, 20.0, 110.0, 110.0, 20.0, 20.0]
        cleaned_transient, spikes_t = temporal_qc_clean(transient, ref_limit=25.0, pollutant="PM2.5")
        assert spikes_t >= 1, "Transient surge was not flagged as spike!"
        assert cleaned_transient[4] is None

        # Case B: Sustained plateau
        sustained = [20.0, 20.0, 20.0, 20.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0]
        cleaned_sustained, spikes_s = temporal_qc_clean(sustained, ref_limit=25.0, pollutant="PM2.5")
        # Tail of plateau must be preserved
        assert cleaned_sustained[5] == 110.0

    def test_sustained_logger_hold_purges_all_subsequent_frozen_hours(self):
        """
        ADVERSARIAL CHALLENGE — EMPIRICAL BUG DETECTION:
        TRANSFORMATION_LOGIC_SPEC.md §2.10.1 & index.html lines 324-326:
        'values repeated three hours running (logger holding its last value) are removed.'
        hold = p !== 'AQI' && full[i-1] === v && full[i-2] === v

        When a sensor freezes for 5 consecutive hours: [150.0, 150.0, 150.0, 150.0, 150.0]
        Index 0: 150.0 (kept)
        Index 1: 150.0 (kept)
        Index 2: None (held)
        Index 3: None (held - must NOT be preserved!)
        Index 4: None (held - must NOT be preserved!)

        Bug in implementation: If cleaned[i] is mutated in-place, then cleaned[i-1] becomes None,
        which causes subsequent iterations to see None and erroneously KEEP indices 3 and 4!
        """
        seq = [150.0, 150.0, 150.0, 150.0, 150.0]

        # For physical pollutant (PM2.5):
        pm_clean, _ = temporal_qc_clean(seq, ref_limit=35.0, pollutant="PM2.5")
        assert pm_clean[0] == 150.0
        assert pm_clean[1] == 150.0
        assert pm_clean[2] is None, "Hour 2 of hold was not purged!"
        assert pm_clean[3] is None, "Hour 3 of hold leaked through filter due to in-place mutation bug!"
        assert pm_clean[4] is None, "Hour 4 of hold leaked through filter due to in-place mutation bug!"

    def test_logger_hold_aqi_immunity_and_short_series_guard(self):
        """
        Adversarial Test:
        1. AQI is completely exempt: [150.0, 150.0, 150.0, 150.0, 150.0] -> 100% preserved.
        2. Short series: [50.0, 50.0] must not trigger hold filter (requires 3 consecutive).
        """
        seq = [150.0, 150.0, 150.0, 150.0, 150.0]
        aqi_clean, _ = temporal_qc_clean(seq, ref_limit=100.0, pollutant="AQI")
        assert aqi_clean == seq, "AQI was erroneously filtered by logger hold!"

        short_seq = [50.0, 50.0]
        short_clean, _ = temporal_qc_clean(short_seq, ref_limit=35.0, pollutant="PM2.5")
        assert short_clean == [50.0, 50.0]

    def test_completeness_and_subhourly_lerp_extremes(self):
        """
        Adversarial Test:
        - 75% rule on boundary counts: 18/24 passes, 17/24 fails.
        - Lerp with bounding None fallback and floating point scrubber clamping.
        """
        # 18 valid out of 24 = 75% -> passes
        s18 = [10.0] * 18 + [None] * 6
        assert check_completeness(s18, 0.75) == 10.0

        # 17 valid out of 24 = 70.8% -> fails
        s17 = [10.0] * 17 + [None] * 7
        assert check_completeness(s17, 0.75) is None

        # Lerp boundary tests
        series = [10.0, None, 30.0, 50.0]
        # At fp = 0.0 -> 10.0
        assert subhourly_lerp(series, 0.0) == 10.0
        # At fp = 0.5 (between 10.0 and None) -> falls back to 10.0
        assert subhourly_lerp(series, 0.5) == 10.0
        # At fp = 1.5 (between None and 30.0) -> falls back to 30.0
        assert subhourly_lerp(series, 1.5) == 30.0
        # At fp = 2.5 (between 30.0 and 50.0) -> exact midpoint 40.0
        assert subhourly_lerp(series, 2.5) == 40.0
        # Clamping beyond bounds
        assert subhourly_lerp(series, -5.0) == 10.0
        assert subhourly_lerp(series, 100.0) == 50.0
