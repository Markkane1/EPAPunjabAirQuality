"""
Adversarial Stress Verification and Empirical Challenge Suite for Milestone M2.
Tests pure mathematical modules in `src/domain/math/` against extreme boundary conditions,
numerical singularities, adversarial edge cases, and statutory regulatory constraints:
1. Wind Speed Boundary Conditions: w_s = 0.0, 0.49, 0.50, 30.0, 31.0 m/s, negative/NaN/Inf.
2. Zero Distance IDW Queries: d = 0.0 km singularity clamping (d_0 = 5.0 km, weight = 0.04).
3. Anisotropic Wind-Steered IDW Kernel: cos(alpha) = -1.0, 0.0, 1.0, screen inversion, velocity saturation.
4. CPF Polar Rose Small-Sample Suppression: N_k = 0, 1, 2, 3, 4, 5 -> None; N_k = 6 -> valid float.
5. Physical Advection Flux: pollutant == 'AQI' returns None, distance > 180 km, divergence > 35 deg.
6. Statutory PEPC AQI: continuous half-open intervals, 500 operational cap, zero/negative suppression.
7. Temporal QC 3h Hold Filter: index guard i >= 2 preventing negative wraparound, AQI exemption.
8. Transboundary and Spatial Projection Edge Cases.
"""
import math
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
    is_anemometer_valid,
    is_calm_wind,
    is_station_blacklisted,
    polar_to_cartesian_wind,
    cartesian_to_polar_wind,
    wind_direction_to_bearing,
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
)
from src.domain.math.cpf import (
    calculate_cpf_rose,
    calculate_pooled_p75,
    calculate_rose_geometry,
    MIN_SECTOR_SAMPLES,
)
from src.domain.math.flux import (
    calculate_advection_flux,
    calculate_receptor_coupling,
    calculate_net_transport_balance,
    MAX_TRANSPORT_DISTANCE_KM,
    MAX_TRANSPORT_CONE_DEG,
)
from src.domain.math.pepc_aqi import (
    pepc_calculate_aqi,
    pepc_composite_aqi,
    pepc_get_category,
    pepc_get_color,
    pepc_interpolate_color,
    pepc_interpolate_color_hex,
    PEPC_BREAKPOINTS,
)
from src.domain.math.qc import (
    temporal_qc_clean,
    check_completeness,
    subhourly_lerp,
)
from src.domain.math.transboundary import (
    calculate_district_transboundary_flux,
    calculate_border_normal_flux,
    calculate_transboundary_index,
    BORDER_CORRIDOR_LIMIT_KM,
)
from src.domain.math.projection import (
    equirectangular_project,
    equirectangular_unproject,
    check_aabb_collision,
    greedy_label_placement,
)


# ==============================================================================
# Suite 1: Extreme Wind Speed & Direction Boundary Conditions
# ==============================================================================
class TestExtremeWindSpeedBoundaries:
    """Stress-tests wind anemometer validation, calm thresholds, and kinematic conversion."""

    @pytest.mark.parametrize(
        "speed,direction,expected_valid,expected_calm",
        [
            # Exactly at minimum physical boundary (0.0 m/s)
            (0.0, 180.0, True, True),
            # Aerodynamic calm boundary edge: just below 0.50 m/s
            (0.49, 180.0, True, True),
            (0.499999, 180.0, True, True),
            # Exactly at aerodynamic calm cutoff: 0.50 m/s (NOT calm)
            (0.50, 180.0, True, False),
            (0.500001, 180.0, True, False),
            # Intermediate active wind
            (15.0, 90.0, True, False),
            # Exactly at maximum physical surface boundary (30.0 m/s = 108 km/h)
            (30.0, 270.0, True, False),
            # Exceeding physical bounds (unphysical / error codes)
            (30.001, 180.0, False, False),
            (31.0, 180.0, False, False),
            (99.9, 180.0, False, False),  # Common sensor error code
            # Negative speeds (unphysical sensor noise)
            (-0.001, 180.0, False, True),
            (-1.0, 180.0, False, True),
            (-30.0, 180.0, False, True),
        ],
    )
    def test_wind_speed_boundaries(self, speed, direction, expected_valid, expected_calm):
        """Validates anemometer quality control across exact numeric boundary limits."""
        assert is_anemometer_valid(speed, direction) == expected_valid
        assert is_calm_wind(speed) == expected_calm

    @pytest.mark.parametrize(
        "speed,direction,should_be_valid",
        [
            (5.0, 0.0, True),       # North (0 deg)
            (5.0, 360.0, True),     # North wrap (360 deg)
            (5.0, -0.01, False),    # Negative azimuth
            (5.0, 360.01, False),   # Beyond full circle
            (5.0, float("nan"), False),
            (float("nan"), 180.0, False),
            (5.0, float("inf"), False),
            (float("inf"), 180.0, False),
            (None, 180.0, False),
            (5.0, None, False),
        ],
    )
    def test_wind_direction_and_nan_guards(self, speed, direction, should_be_valid):
        """Verifies direction angle bounds and NaN/Inf/None rejection."""
        assert is_anemometer_valid(speed, direction) == should_be_valid

    def test_polar_to_cartesian_at_boundary_speeds(self):
        """Verifies polar-to-Cartesian conversion behavior at exact boundary conditions."""
        # Speed 0.0 m/s -> exactly (0.0, 0.0), no negative zeros
        res_0 = polar_to_cartesian_wind(0.0, 180.0)
        assert res_0 == (0.0, 0.0)
        assert not math.copysign(1.0, res_0[0]) < 0  # No -0.0

        # Speed 0.49 m/s (from South = blowing to North: u=0, v=+0.49)
        res_calm = polar_to_cartesian_wind(0.49, 180.0)
        assert res_calm is not None
        assert abs(res_calm[0]) < 1e-6
        assert abs(res_calm[1] - 0.49) < 1e-6

        # Speed 0.50 m/s
        res_active = polar_to_cartesian_wind(0.50, 180.0)
        assert res_active is not None
        assert abs(res_active[0]) < 1e-6
        assert abs(res_active[1] - 0.50) < 1e-6

        # Speed 30.0 m/s (East wind: from 90 deg = blowing to West: u=-30, v=0)
        res_max = polar_to_cartesian_wind(30.0, 90.0)
        assert res_max is not None
        assert abs(res_max[0] - (-30.0)) < 1e-6
        assert abs(res_max[1]) < 1e-6

        # Speed 31.0 m/s -> Out of bounds, returns None
        assert polar_to_cartesian_wind(31.0, 90.0) is None
        assert polar_to_cartesian_wind(-0.5, 90.0) is None

    @pytest.mark.parametrize(
        "station_name,expected_blacklisted",
        [
            ("Wazirabad", True),
            ("wazirabad", True),
            ("WAZIRABAD", True),
            ("  wazirabad aqms  ", True),
            ("PK_WAZ_001", True),
            ("Wazirabad Station", True),
            ("Lahore", False),
            ("Rawalpindi", False),
            ("Multan", False),
            (None, False),
            ("", False),
        ],
    )
    def test_wazirabad_hardware_blacklist_adversarial(self, station_name, expected_blacklisted):
        """Ensures Wazirabad 140 deg physical vane offset is blacklisted regardless of casing/spacing."""
        assert is_station_blacklisted(station_name) == expected_blacklisted
        if expected_blacklisted:
            assert is_anemometer_valid(5.0, 180.0, station_name) is False
            assert polar_to_cartesian_wind(5.0, 180.0, station_name) is None


# ==============================================================================
# Suite 2: Discrete Geodesic IDW Zero Distance & Singularities
# ==============================================================================
class TestDiscreteIDWZeroDistanceAndSingularities:
    """Stress-tests discrete geodesic IDW against zero distance singularities and edge cases."""

    def test_zero_distance_single_station(self):
        """
        When target coordinates exactly coincide with the only reporting station (d = 0.0 km):
        Singularity clamping enforces d_eff = max(0.0, 5.0) = 5.0 km.
        Weight = 1.0 / (5.0^2) = 0.04.
        Interpolated value must exactly equal the station's reported value.
        """
        target = (31.549, 74.364)
        stations = [{"coords": (31.549, 74.364), "value": 178.5}]

        interp = discrete_geodesic_idw(target, stations)
        assert interp is not None
        assert abs(interp - 178.5) < 1e-6

    def test_zero_distance_multi_station_analytical_weights(self):
        """
        Target coincides with station 1 (d = 0.0 km), with station 2 at 10.0 km and station 3 at 20.0 km.
        Clamping ensures station 1 receives weight = 1 / (5^2) = 0.04 (not infinity).
        Station 2 weight = 1 / (10^2) = 0.01.
        Station 3 weight = 1 / (20^2) = 0.0025.
        Expected = (0.04 * 100 + 0.01 * 200 + 0.0025 * 300) / (0.04 + 0.01 + 0.0025)
                 = (4.0 + 2.0 + 0.75) / 0.0525 = 6.75 / 0.0525 = 128.571428...
        """
        t_lat, t_lon = 31.0, 74.0

        # Construct station at exactly 0.0 km
        st1 = {"coords": (31.0, 74.0), "value": 100.0}

        # Find points approximately 10 km and 20 km away
        st2_lat = 31.0 + (10.0 / 111.1949)
        st2 = {"coords": (st2_lat, 74.0), "value": 200.0}

        st3_lat = 31.0 + (20.0 / 111.1949)
        st3 = {"coords": (st3_lat, 74.0), "value": 300.0}

        d1 = haversine_distance(t_lat, t_lon, st1["coords"][0], st1["coords"][1])
        d2 = haversine_distance(t_lat, t_lon, st2["coords"][0], st2["coords"][1])
        d3 = haversine_distance(t_lat, t_lon, st3["coords"][0], st3["coords"][1])
        assert d1 == 0.0
        assert abs(d2 - 10.0) < 0.05
        assert abs(d3 - 20.0) < 0.05

        interp = discrete_geodesic_idw((t_lat, t_lon), [st1, st2, st3])
        assert interp is not None

        # Verify finite interpolated value without floating-point blowup
        w1 = 1.0 / (5.0 ** 2)
        w2 = 1.0 / (d2 ** 2)
        w3 = 1.0 / (d3 ** 2)
        expected = (w1 * 100.0 + w2 * 200.0 + w3 * 300.0) / (w1 + w2 + w3)
        assert abs(interp - expected) < 1e-4

    def test_distance_clamp_flat_response_under_5km(self):
        """
        Distances below 5.0 km (e.g. 0.0, 1.0, 4.99 km) must receive identical clamped weight 0.04.
        """
        t_lat, t_lon = 31.0, 74.0
        st_0 = {"coords": (31.0, 74.0), "value": 50.0}
        st_1 = {"coords": (31.0 + 1.0 / 111.2, 74.0), "value": 150.0}

        # Both have d_eff = 5.0 km, so both receive weight = 0.04.
        # Mean of equal weights must be exactly (50 + 150) / 2 = 100.0
        interp = discrete_geodesic_idw((t_lat, t_lon), [st_0, st_1])
        assert interp is not None
        assert abs(interp - 100.0) < 1e-4

    def test_vector_idw_zero_distance(self):
        """Vector IDW handles target coincident with reporting node without NaN."""
        target = (31.5, 74.3)
        stations = [
            {"coords": (31.5, 74.3), "u": 4.5, "v": -2.3},
            {"coords": (31.6, 74.4), "u": 1.0, "v": 1.0},
        ]
        uv = discrete_geodesic_idw_vector(target, stations)
        assert uv is not None
        assert not math.isnan(uv[0]) and not math.isnan(uv[1])
        assert not math.isinf(uv[0]) and not math.isinf(uv[1])

    def test_discrete_idw_adversarial_station_payloads(self):
        """Gracefully handles null, NaN, string, and malformed station records."""
        target = (31.5, 74.3)
        stations = [
            {"coords": (31.5, 74.3), "value": None},
            {"coords": (31.5, 74.3), "value": float("nan")},
            {"coords": (31.5, 74.3), "value": "corrupted"},
            {"coords": None, "value": 50.0},
            {"coords": (31.5,), "value": 50.0},
            {"coords": (31.5, 74.3)},  # Missing value
        ]
        assert discrete_geodesic_idw(target, stations) is None
        assert discrete_geodesic_idw(target, []) is None


# ==============================================================================
# Suite 3: Anisotropic Wind-Steered Continuous IDW Kernel Evaluations
# ==============================================================================
class TestAnisotropicIDWKernelEvaluations:
    """Stress-tests the anisotropic wind-steered interpolation kernel across directional alignment angles."""

    def test_pure_downwind_amplification_cos_alpha_plus_one(self):
        """
        When query point is directly DOWNWIND of station:
        Station at (100, 100), Eastward wind u = 3.0 m/s, v = 0.0 m/s (s = 3.0 m/s >= 1.5 m/s -> sat = 1.0).
        Query point directly East at (150, 100): dx = 50, dy = 0, d = 50 px.
        cos(alpha) = (50 * 3.0 - 0) / (50 * 3.0) = +1.0.
        psi = 1.0 + 0.70 * (+1.0) * 1.0 = 1.70.
        mult = max(0.30, 1.70) = 1.70 (+70% amplification along plume axis).
        """
        station = {"coords_px": (100.0, 100.0), "value": 200.0, "u": 3.0, "v": 0.0}
        target_downwind = (150.0, 100.0)

        val, d_min, alpha = anisotropic_idw(target_downwind, [station], scale=100.0)
        assert abs(val - 200.0) < 1e-6
        assert abs(d_min - (50.0 * 111.0 / 100.0)) < 1e-4

    def test_pure_upwind_attenuation_cos_alpha_minus_one(self):
        """
        When query point is directly UPWIND of station:
        Station at (100, 100), Eastward wind u = 3.0 m/s, v = 0.0 m/s.
        Query point directly West at (50, 100): dx = -50, dy = 0, d = 50 px.
        cos(alpha) = (-50 * 3.0 - 0) / (50 * 3.0) = -1.0.
        psi = 1.0 + 0.70 * (-1.0) * 1.0 = 0.30.
        mult = max(0.30, 0.30) = 0.30 (70% reduction / 0.30 floor).
        """
        st_downwind_source = {"coords_px": (50.0, 100.0), "value": 200.0, "u": 3.0, "v": 0.0}
        st_upwind_source = {"coords_px": (150.0, 100.0), "value": 0.0, "u": 3.0, "v": 0.0}

        val, _, _ = anisotropic_idw((100.0, 100.0), [st_downwind_source, st_upwind_source])
        # Expected: (w0 * 1.70 * 200.0 + w0 * 0.30 * 0.0) / (w0 * (1.70 + 0.30)) = (1.70 * 200) / 2.0 = 170.0
        assert abs(val - 170.0) < 1e-4

    def test_pure_crosswind_cos_alpha_zero(self):
        """
        When query point is orthogonal (CROSSWIND) to wind vector:
        Station at (100, 100), Eastward wind u = 3.0, v = 0.0.
        Query point at (100, 150): dx = 0, dy = 50.
        cos(alpha) = (0 * 3.0 - 50 * 0) / (50 * 3.0) = 0.0.
        psi = 1.0 + 0.70 * (0.0) = 1.00.
        mult = max(0.30, 1.00) = 1.00 (neutral isotropic weight).
        """
        st1 = {"coords_px": (100.0, 50.0), "value": 100.0, "u": 3.0, "v": 0.0}
        st2 = {"coords_px": (100.0, 150.0), "value": 0.0, "u": 3.0, "v": 0.0}

        val, _, _ = anisotropic_idw((100.0, 100.0), [st1, st2])
        assert abs(val - 50.0) < 1e-4

    def test_screen_y_inversion_northward_wind(self):
        """
        Validates screen coordinate inversion:
        Screen Y points downwards (South), but meteorological northward wind (v > 0)
        carries pollution toward North (screen -y).
        """
        st_north = {"coords_px": (100.0, 100.0), "value": 200.0, "u": 0.0, "v": 3.0}
        st_south = {"coords_px": (100.0, 200.0), "value": 0.0, "u": 0.0, "v": 3.0}

        val_mid, _, _ = anisotropic_idw((100.0, 150.0), [st_north, st_south])
        # st_north is at (100, 100) -> dy = 150 - 100 = +50 (upwind, mult = 0.30)
        # st_south is at (100, 200) -> dy = 150 - 200 = -50 (downwind, mult = 1.70)
        # Expected = (200 * 0.30 + 0 * 1.70) / (0.30 + 1.70) = 60 / 2.0 = 30.0
        assert abs(val_mid - 30.0) < 1e-4

    def test_calm_wind_and_near_field_bypass(self):
        """
        When s <= 0.5 m/s (calm) or d <= 2.0 px:
        Anisotropic multiplier is bypassed; isotropic weight w0 is retained.
        """
        # Calm wind: s = 0.49 m/s
        st_calm1 = {"coords_px": (50.0, 100.0), "value": 100.0, "u": 0.49, "v": 0.0}
        st_calm2 = {"coords_px": (150.0, 100.0), "value": 0.0, "u": 0.49, "v": 0.0}
        val_calm, _, _ = anisotropic_idw((100.0, 100.0), [st_calm1, st_calm2])
        assert abs(val_calm - 50.0) < 1e-4

        # Near field: d = 1.5 px <= 2.0 px
        st_near1 = {"coords_px": (98.5, 100.0), "value": 100.0, "u": 3.0, "v": 0.0}
        st_near2 = {"coords_px": (101.5, 100.0), "value": 0.0, "u": 3.0, "v": 0.0}
        val_near, _, _ = anisotropic_idw((100.0, 100.0), [st_near1, st_near2])
        assert abs(val_near - 50.0) < 1e-4

    @pytest.mark.parametrize(
        "km_min,expected_alpha",
        [
            (0.0, 235),
            (20.0, 235),
            (44.99, 235),
            (45.0, 235),
            (92.5, 165),  # Midpoint: 235 - 140 * 0.5 = 165
            (140.0, 95),
            (140.01, 95),
            (200.0, 95),
            (500.0, 95),
        ],
    )
    def test_distance_opacity_taper_boundaries(self, km_min, expected_alpha):
        """Verifies distance opacity decay across exact [45.0, 140.0] km thresholds."""
        assert calculate_distance_opacity(km_min) == expected_alpha


# ==============================================================================
# Suite 4: CPF Polar Rose Small-Sample Suppression & Calm Handling
# ==============================================================================
class TestCPFPolarRoseSmallSampleSuppression:
    """Stress-tests CPF polar wind rose small-sample suppression rule (N_k < 6 -> None)."""

    @pytest.mark.parametrize("n_samples", [0, 1, 2, 3, 4, 5])
    def test_small_sample_suppression_strictly_enforced(self, n_samples):
        """
        When a sector has fewer than 6 valid hours (N_k < 6), CPF must evaluate to None.
        Prevents false 100% spikes from 1-2 chance occurrences.
        """
        obs = [
            {"value": 150.0, "wind_speed": 3.0, "wind_direction": 0.0}
            for _ in range(n_samples)
        ]
        obs += [
            {"value": 50.0, "wind_speed": 3.0, "wind_direction": 90.0}
            for _ in range(20)
        ]

        rose = calculate_cpf_rose(obs, threshold_p75=80.0)
        assert rose["sectors"][0] is None
        assert rose["sector_counts"][0] == n_samples

    def test_sample_threshold_six_becomes_valid(self):
        """
        Exactly at N_k = 6, suppression is lifted and valid probability is returned.
        """
        obs = [
            {"value": 150.0, "wind_speed": 3.0, "wind_direction": 0.0},
            {"value": 120.0, "wind_speed": 3.0, "wind_direction": 0.0},
            {"value": 90.0, "wind_speed": 3.0, "wind_direction": 0.0},
            {"value": 40.0, "wind_speed": 3.0, "wind_direction": 0.0},
            {"value": 30.0, "wind_speed": 3.0, "wind_direction": 0.0},
            {"value": 20.0, "wind_speed": 3.0, "wind_direction": 0.0},
        ]

        rose = calculate_cpf_rose(obs, threshold_p75=80.0)
        assert rose["sector_counts"][0] == 6
        assert rose["sector_exceedances"][0] == 3
        assert rose["sectors"][0] == 0.50  # 3 / 6 = 0.50

    def test_calm_winds_strictly_excluded_from_sectors(self):
        """
        Winds with speed < 0.5 m/s are classified as aerodynamic calm and excluded from sectors.
        """
        obs = [
            {"value": 200.0, "wind_speed": 0.49, "wind_direction": 0.0}
            for _ in range(10)
        ] + [
            {"value": 100.0, "wind_speed": 0.50, "wind_direction": 90.0}
            for _ in range(6)
        ]

        rose = calculate_cpf_rose(obs, threshold_p75=80.0)
        assert rose["sector_counts"][0] == 0
        assert rose["sectors"][0] is None
        assert rose["sector_counts"][4] == 6
        assert rose["sectors"][4] == 1.0
        assert abs(rose["calm_ratio"] - 0.625) < 1e-4

    def test_rose_geometry_suppressed_vs_active(self):
        """Suppressed sectors generate muted circular stubs (10px) while active generate scaled arcs."""
        sectors = [None] * 16
        sectors[0] = 0.40  # Active

        geom = calculate_rose_geometry(sectors, radius=100.0, muted_stub_px=10.0)
        assert len(geom) == 16
        assert geom[0]["is_suppressed"] is False
        assert abs(geom[0]["radius_px"] - 50.0) < 1e-2
        assert geom[1]["is_suppressed"] is True
        assert geom[1]["radius_px"] == 10.0


# ==============================================================================
# Suite 5: Physical Advection Flux & Pathway Coupling Adversarial Guards
# ==============================================================================
class TestAdvectionFluxAdversarialGuards:
    """Stress-tests physical advection flux domain constraints, distance/angle limits, and ranking."""

    @pytest.mark.parametrize("aqi_str", ["AQI", "aqi", "Aqi", " aqi "])
    def test_mandatory_physical_dimension_guard_disables_aqi(self, aqi_str):
        """
        Physical advection mass flux is strictly disabled for ordinal dimensionless index 'AQI'.
        Multiplying a health index by velocity violates dimensional analysis and mass conservation.
        """
        res = calculate_advection_flux(
            source_station=(31.5, 74.3),
            receptor_coords=(31.7, 74.5),
            pollutant=aqi_str,
            concentration=200.0,
            u_wind=3.0,
            v_wind=3.0,
        )
        assert res is None

    def test_advection_distance_exact_cutoff_180km(self):
        """
        Inter-district advection transport is strictly bounded at MAXD = 180.0 km.
        """
        src = (31.0, 74.0)
        rec_in = (31.0, 74.0 + (179.0 / 95.31))
        d_in = haversine_distance(src[0], src[1], rec_in[0], rec_in[1])
        assert d_in < 180.0

        flux_in = calculate_advection_flux(
            source_station=src,
            receptor_coords=rec_in,
            pollutant="PM2.5",
            concentration=100.0,
            u_wind=5.0,  # Blowing East
            v_wind=0.0,
        )
        assert flux_in is not None
        assert flux_in["flux"] > 0.0

        rec_out = (31.0, 74.0 + (181.5 / 95.31))
        d_out = haversine_distance(src[0], src[1], rec_out[0], rec_out[1])
        assert d_out > 180.0

        flux_out = calculate_advection_flux(
            source_station=src,
            receptor_coords=rec_out,
            pollutant="PM2.5",
            concentration=100.0,
            u_wind=5.0,
            v_wind=0.0,
        )
        assert flux_out is None

    def test_transport_cone_exact_cutoff_35deg(self):
        """
        Transport cone divergence is strictly bounded at delta_theta <= 35.0 deg.
        """
        src = (31.0, 74.0)
        rec = (31.2, 74.2)
        theta_brg = forward_bearing(src[0], src[1], rec[0], rec[1])

        # Wind blowing toward theta_brg + 34.5 deg (within 35 deg cone)
        theta_to_in = (theta_brg + 34.5) % 360.0
        rad_in = math.radians(theta_to_in)
        u_in = 4.0 * math.sin(rad_in)
        v_in = 4.0 * math.cos(rad_in)

        flux_in = calculate_advection_flux(
            source_station=src,
            receptor_coords=rec,
            pollutant="PM2.5",
            concentration=100.0,
            u_wind=u_in,
            v_wind=v_in,
        )
        assert flux_in is not None
        assert abs(flux_in["divergence_deg"] - 34.5) < 0.1

        # Wind blowing toward theta_brg + 35.5 deg (outside 35 deg cone)
        theta_to_out = (theta_brg + 35.5) % 360.0
        rad_out = math.radians(theta_to_out)
        u_out = 4.0 * math.sin(rad_out)
        v_out = 4.0 * math.cos(rad_out)

        flux_out = calculate_advection_flux(
            source_station=src,
            receptor_coords=rec,
            pollutant="PM2.5",
            concentration=100.0,
            u_wind=u_out,
            v_wind=v_out,
        )
        assert flux_out is None

    def test_calm_wind_cutoff_in_flux(self):
        """Advection flux returns None when wind speed < 0.5 m/s, even if perfectly aligned."""
        src = (31.0, 74.0)
        rec = (31.2, 74.2)
        theta_brg = forward_bearing(src[0], src[1], rec[0], rec[1])
        rad = math.radians(theta_brg)

        # Speed 0.49 m/s aligned with bearing
        u_calm = 0.49 * math.sin(rad)
        v_calm = 0.49 * math.cos(rad)
        assert calculate_advection_flux(src, rec, "PM2.5", 100.0, u_calm, v_calm) is None

        # Speed 0.50 m/s aligned with bearing
        u_act = 0.50 * math.sin(rad)
        v_act = 0.50 * math.cos(rad)
        flux_act = calculate_advection_flux(src, rec, "PM2.5", 100.0, u_act, v_act)
        assert flux_act is not None
        assert flux_act["flux"] > 0.0

    def test_top_60_pathway_truncation(self):
        """Generates 100 candidate pathway links and asserts strict truncation to top 60."""
        flux_series = [
            {
                "source_district": f"dist_{i}",
                "receptor_district": "target_dist",
                "distance_km": 50.0,
                "bearing_deg": 90.0,
                "mean_flux": float(i),
            }
            for i in range(1, 101)
        ]

        ranked = calculate_receptor_coupling(flux_series, receptor_cpfs={}, max_links=60)
        assert len(ranked) == 60
        assert ranked[0]["score"] > ranked[-1]["score"]
        assert abs(ranked[0]["score"] - (100.0 * 0.25)) < 1e-4
        assert abs(ranked[-1]["score"] - (41.0 * 0.25)) < 1e-4


# ==============================================================================
# Suite 6: Statutory PEPC AQI Continuous Half-Open Intervals & 500 Cap
# ==============================================================================
class TestPEPCAQIContinuousIntervalsAndCeiling:
    """Stress-tests PEPC piecewise linear interpolation across all interval boundaries and capping."""

    def test_continuous_half_open_pm25_boundary_transitions(self):
        """
        Tests infinitesimally adjacent concentrations across every category boundary
        for PM2.5: [15, 35, 70, 140, 250, 350] ug/m3.
        Verifies (BP_{i-1}, BP_i] half-open intervals.
        """
        # Boundary 1: 15.0 (Good: 50) vs 15.3 (Satisfactory: 51)
        assert pepc_calculate_aqi("PM2.5", 15.0) == 50
        assert pepc_get_category(50) == "Good"
        assert pepc_calculate_aqi("PM2.5", 15.0001) == 50
        assert pepc_calculate_aqi("PM2.5", 15.3) == 51
        assert pepc_get_category(51) == "Satisfactory"

        # Boundary 2: 35.0 (Satisfactory: 100) vs 35.3 (Moderate: 101)
        assert pepc_calculate_aqi("PM2.5", 35.0) == 100
        assert pepc_get_category(100) == "Satisfactory"
        assert pepc_calculate_aqi("PM2.5", 35.0001) == 100
        assert pepc_calculate_aqi("PM2.5", 35.5) == 101
        assert pepc_get_category(101) == "Moderate"

        # Boundary 3: 70.0 (Moderate: 150)
        assert pepc_calculate_aqi("PM2.5", 70.0) == 150

        # Boundary 4: 140.0 (Unhealthy Sensitive: 200)
        assert pepc_calculate_aqi("PM2.5", 140.0) == 200

        # Boundary 5: 250.0 (Unhealthy: 300)
        assert pepc_calculate_aqi("PM2.5", 250.0) == 300

        # Boundary 6: 350.0 (Very Unhealthy: 400)
        assert pepc_calculate_aqi("PM2.5", 350.0) == 400

    def test_operational_ceiling_500_cap(self):
        """
        Concentrations exceeding statutory category 5 (e.g. PM2.5 > 350.0 ug/m3, PM10 > 550.0 ug/m3)
        must be strictly clamped to the operational ceiling of 500.
        """
        # PM2.5 > 350.0
        assert pepc_calculate_aqi("PM2.5", 350.0001) == 500
        assert pepc_calculate_aqi("PM2.5", 400.0) == 500
        assert pepc_calculate_aqi("PM2.5", 850.0) == 500
        assert pepc_calculate_aqi("PM2.5", 5000.0) == 500

        # PM10 > 550.0
        assert pepc_calculate_aqi("PM10", 550.0001) == 500
        assert pepc_calculate_aqi("PM10", 600.0) == 500
        assert pepc_calculate_aqi("PM10", 1200.0) == 500

        # Gaseous caps
        assert pepc_calculate_aqi("SO2", 1600.0001) == 500
        assert pepc_calculate_aqi("NO2", 580.0001) == 500
        assert pepc_calculate_aqi("O3", 550.0001) == 500
        assert pepc_calculate_aqi("CO", 40.0001) == 500

    def test_zero_and_negative_sanitization(self):
        """Negative values, NaN, and None return None; exact 0.0 returns 0."""
        assert pepc_calculate_aqi("PM2.5", 0.0) == 0
        assert pepc_calculate_aqi("PM2.5", -0.0001) is None
        assert pepc_calculate_aqi("PM2.5", -50.0) is None
        assert pepc_calculate_aqi("PM2.5", float("nan")) is None
        assert pepc_calculate_aqi("PM2.5", None) is None
        assert pepc_calculate_aqi("UNKNOWN_POLLUTANT", 50.0) is None

    def test_composite_aqi_particulate_rule(self):
        """Composite AQI is strictly max(I_PM2.5, I_PM10)."""
        assert pepc_composite_aqi(150, 80) == 150
        assert pepc_composite_aqi(80, 220) == 220
        assert pepc_composite_aqi(None, 180) == 180
        assert pepc_composite_aqi(300, None) == 300
        assert pepc_composite_aqi(None, None) is None


# ==============================================================================
# Suite 7: Temporal QC 3h Hold Filter with Index Guard (i >= 2)
# ==============================================================================
class TestTemporalQCHoldFilterAndIndexGuard:
    """Stress-tests the 3h hold filter index boundary guard (i >= 2) and AQI exemption."""

    def test_index_guard_prevents_negative_wraparound(self):
        """
        Verifies that i=0 and i=1 NEVER inspect negative array indices.
        If a buggy implementation used series[i] == series[i-1] == series[i-2],
        at i=0 it would compare series[0] with series[-1] and series[-2].
        """
        series = [100.0, 50.0, 75.0, 100.0, 100.0]
        cleaned, _ = temporal_qc_clean(series, ref_limit=35.0, pollutant="PM2.5")

        assert cleaned[0] == 100.0
        assert cleaned[1] == 50.0
        assert cleaned[2] == 75.0

    def test_three_hour_hold_purging(self):
        """
        Three consecutive identical physical readings (v_i == v_{i-1} == v_{i-2})
        flag sensor freeze/logger hold and convert v_i to None.
        """
        s3 = [50.0, 50.0, 50.0]
        c3, _ = temporal_qc_clean(s3, ref_limit=35.0, pollutant="PM2.5")
        assert c3 == [50.0, 50.0, None]

        s_interrupted = [50.0, 50.0, 50.1, 50.0]
        c_int, _ = temporal_qc_clean(s_interrupted, ref_limit=35.0, pollutant="PM2.5")
        assert c_int == [50.0, 50.0, 50.1, 50.0]

    def test_sustained_logger_hold_purging_adversarial(self):
        """
        Adversarial Test: When a sensor freeze lasts 5 consecutive hours:
        [150.0, 150.0, 150.0, 150.0, 150.0]
        All hours after the first two (i.e. indices 2, 3, 4) must be purged to None.
        A defect where in-place mutation sets index 2 to None, breaking the chain for
        indices 3 and 4 and allowing frozen values through, must be caught.
        """
        series = [150.0, 150.0, 150.0, 150.0, 150.0]
        cleaned, _ = temporal_qc_clean(series, ref_limit=35.0, pollutant="PM2.5")
        assert cleaned == [150.0, 150.0, None, None, None], (
            f"Sustained logger hold leaked frozen data: got {cleaned}"
        )

    def test_aqi_exempt_from_hold_filter(self):
        """
        Composite AQI is strictly exempt from logger hold filtering
        as integer sub-index values genuinely remain constant over time.
        """
        aqi_series = [150.0, 150.0, 150.0, 150.0, 150.0]
        cleaned_aqi, _ = temporal_qc_clean(aqi_series, ref_limit=100.0, pollutant="AQI")
        assert cleaned_aqi == [150.0, 150.0, 150.0, 150.0, 150.0]

    def test_temporal_completeness_75_percent_rule(self):
        """Verifies 75% completeness rule: round(0.75 * H) valid samples required."""
        s_17 = [50.0] * 17 + [None] * 7
        assert check_completeness(s_17) is None

        s_18 = [50.0] * 18 + [None] * 6
        assert check_completeness(s_18) == 50.0


# ==============================================================================
# Suite 8: Transboundary & Spatial Projection Adversarial Edge Cases
# ==============================================================================
class TestTransboundaryAndProjectionAdversarial:
    """Stress-tests transboundary border-belt limits and equirectangular projection."""

    def test_transboundary_120km_corridor_cutoff(self):
        """Districts with centroid > 120.0 km from border receive TBVal = 0.0."""
        val_in = calculate_district_transboundary_flux(
            border_distance_km=120.0,
            india_sectors=[4, 5, 6],
            concentration=100.0,
            u_wind=-3.0,
            v_wind=0.0,
        )
        assert val_in > 0.0

        val_out = calculate_district_transboundary_flux(
            border_distance_km=120.01,
            india_sectors=[4, 5, 6],
            concentration=100.0,
            u_wind=-3.0,
            v_wind=0.0,
        )
        assert val_out == 0.0

    def test_transboundary_calm_winds_yield_zero(self):
        """Calm winds (< 0.5 m/s) yield zero transboundary flux."""
        val_calm = calculate_district_transboundary_flux(
            border_distance_km=50.0,
            india_sectors=[4, 5, 6],
            concentration=200.0,
            u_wind=-0.49,
            v_wind=0.0,
        )
        assert val_calm == 0.0

    def test_equirectangular_projection_roundtrip(self):
        """Coordinate projection and unprojection roundtrip has zero drift (< 1e-5 deg)."""
        lat, lon = 31.5497, 74.3436
        x, y = equirectangular_project(lat, lon, width_px=1200.0, height_px=900.0)
        r_lat, r_lon = equirectangular_unproject(x, y, width_px=1200.0, height_px=900.0)
        assert abs(r_lat - lat) < 1e-5
        assert abs(r_lon - lon) < 1e-5

    def test_greedy_label_placement_multi_district_offsets(self):
        """Places 6 neighboring district labels and confirms 0 collisions between bounding boxes."""
        # 6 neighboring districts with realistic anchor separation
        labels = [
            {"district_id": "lahore", "text": "Lahore", "x": 600.0, "y": 450.0, "width": 50.0, "height": 16.0},
            {"district_id": "kasur", "text": "Kasur", "x": 610.0, "y": 470.0, "width": 50.0, "height": 16.0},
            {"district_id": "sheikhupura", "text": "Sheikhupura", "x": 585.0, "y": 440.0, "width": 70.0, "height": 16.0},
            {"district_id": "nankana", "text": "Nankana Sahib", "x": 570.0, "y": 460.0, "width": 80.0, "height": 16.0},
            {"district_id": "okara", "text": "Okara", "x": 550.0, "y": 490.0, "width": 50.0, "height": 16.0},
            {"district_id": "gujranwala", "text": "Gujranwala", "x": 605.0, "y": 415.0, "width": 65.0, "height": 16.0},
        ]

        placed = greedy_label_placement(labels)
        assert len(placed) == 6

        boxes = [p["bounding_box"] for p in placed]
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                assert not check_aabb_collision(boxes[i], boxes[j]), (
                    f"Collision between {labels[i]['district_id']} and {labels[j]['district_id']}"
                )
