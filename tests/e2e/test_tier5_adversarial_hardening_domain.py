"""
Tier 5: Adversarial Coverage Hardening — Mathematical Transformations & Ingestion Pipelines
Exclusively owned and authored by challenger_m6_tier5_1.

Executes white-box empirical challenge testing against:
1. IDW Distance Singularities (d -> 0, d > 500 km), Wind Velocities (>= 30 m/s, calm < 0.5 m/s).
2. Wind Rose CPF Small Sample Thresholds (Nk < 6), Missing Sectors, Single-Valued Distributions.
3. Advection Mass Flux Dimensionless AQI Guard Rejection & Top-60 Link Truncation.
4. PEPC AQI Breakpoint Interpolation at Exact Boundaries & Negative Value Sanitization.
5. Temporal QC Filter Hold-Filter States, Spike Detections, 75% Completeness, & Uniform Series.
6. Equirectangular Projection Precision & Collision-Free Greedy Labeling Under Anchor Collisions.
7. User CSV Ingestion Pipeline Ragged Rows, Multi-Encoding, Corrupt Timestamps, & Dead-Letter Quarantine.
8. Transboundary Atmospheric Border Corridor Distance & Sector Inflow/Outflow Boundaries.
"""
import io
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pytest
from pydantic import ValidationError

# Direct Domain Math Imports
from src.domain.math.idw import (
    anisotropic_idw,
    calculate_distance_opacity,
    discrete_geodesic_idw,
    discrete_geodesic_idw_vector,
)
from src.domain.math.wind import (
    CALM_WIND_THRESHOLD_MS,
    MAX_WIND_SPEED_MS,
    MIN_WIND_SPEED_MS,
    cartesian_to_polar_wind,
    is_anemometer_valid,
    is_calm_wind,
    is_station_blacklisted,
    polar_to_cartesian_wind,
    wind_direction_to_bearing,
)
from src.domain.math.cpf import (
    calculate_cpf_rose,
    calculate_pooled_p75,
    calculate_rose_geometry,
)
from src.domain.math.flux import (
    calculate_advection_flux,
    calculate_net_transport_balance,
    calculate_receptor_coupling,
)
from src.domain.math.pepc_aqi import (
    normalize_pollutant_key,
    pepc_calculate_aqi,
    pepc_composite_aqi,
    pepc_get_category,
    pepc_get_color,
    pepc_interpolate_color,
    pepc_interpolate_color_hex,
)
from src.domain.math.qc import (
    check_completeness,
    subhourly_lerp,
    temporal_qc_clean,
)
from src.domain.math.projection import (
    check_aabb_collision,
    equirectangular_project,
    equirectangular_unproject,
    greedy_label_placement,
)
from src.domain.math.transboundary import (
    calculate_border_normal_flux,
    calculate_district_transboundary_flux,
    calculate_transboundary_index,
)
from src.domain.schemas.csv_schema import UserCSVRow
from src.domain.schemas.measurement import NormalizedObservation, RawStationMeasurement
from src.pipelines.csv_adapter import CSVIngestionResult, UserCSVIngestionAdapter
from src.pipelines.fallback_engine import FallbackTemplateEngine


# =============================================================================
# 1. IDW Distance Singularities & Extreme Wind Dynamics
# =============================================================================
class TestTier5IDWGeodesicAndAnisotropicSingularities:
    """Stress-tests IDW mathematical transformations for singularities and boundary limits."""

    def test_idw_exact_coincident_target_singularity_clamp(self):
        """
        Target coincides exactly with reporting station (d = 0.0 km).
        Must clamp d_eff to d0 (5.0 km), computing finite weight w = 1 / 25 = 0.04.
        """
        target = (31.5204, 74.3587)
        stations = [
            {"coords": (31.5204, 74.3587), "value": 280.0},
            {"coords": (31.1179, 74.4460), "value": 50.0},
        ]
        val = discrete_geodesic_idw(target, stations, power=2.0, d0=5.0)
        assert val is not None
        # Coincident station at d0=5km (w=0.04) heavily dominates station ~45km away (w~0.00049)
        assert 275.0 <= val <= 280.0

    def test_idw_sub_millimeter_distance_numerical_stability(self):
        """
        Target is separated by 1e-7 degrees (~1 cm).
        Distance is below d0 clamp and must evaluate stably without floating underflow.
        """
        target = (31.5204, 74.3587)
        stations = [{"coords": (31.520400001, 74.358700001), "value": 175.5}]
        val = discrete_geodesic_idw(target, stations, power=2.0, d0=5.0)
        assert val is not None
        assert math.isclose(val, 175.5, rel_tol=1e-5)

    def test_idw_extreme_transprovincial_distance_exceeding_500km(self):
        """
        Two monitors at extreme provincial extremities > 500 km apart:
        Rahim Yar Khan (28.4212, 70.2989) to Rawalpindi (33.5973, 73.0479) is ~635 km.
        Validates mathematical stability with large geodesic separations.
        """
        target_faisalabad = (31.4187, 73.0791)  # Central Punjab
        stations = [
            {"coords": (28.4212, 70.2989), "value": 100.0},  # ~430 km from Faisalabad
            {"coords": (33.5973, 73.0479), "value": 400.0},  # ~240 km from Faisalabad
        ]
        val = discrete_geodesic_idw(target_faisalabad, stations, power=2.0, d0=5.0)
        assert val is not None
        # Rawalpindi is closer (~240 km) than Rahim Yar Khan (~430 km), so val > 250
        assert 250.0 < val < 360.0

    def test_idw_vector_components_interpolation_with_nans(self):
        """Discrete vector IDW must gracefully drop NaN/corrupt components and interpolate valid vectors."""
        target = (31.5, 74.3)
        stations = [
            {"coords": (31.4, 74.2), "u": 2.5, "v": -1.5},
            {"coords": (31.6, 74.4), "u": float("nan"), "v": 4.0},  # Must be skipped
            {"coords": (31.5, 74.5), "u": 3.0, "v": -2.0},
        ]
        res = discrete_geodesic_idw_vector(target, stations)
        assert res is not None
        u_interp, v_interp = res
        assert not math.isnan(u_interp) and not math.isnan(v_interp)
        assert 2.5 <= u_interp <= 3.0
        assert -2.0 <= v_interp <= -1.5

    def test_anisotropic_idw_extreme_velocity_saturation_and_multiplier_clamp(self):
        """
        Wind speed >= 30 m/s (extreme gale / dust storm).
        Velocity saturation min(1.0, s / 1.5) must cap at 1.0.
        Plume multiplier must be bounded in [0.30, 1.70].
        """
        # Monitor at (50, 100) with severe 30 m/s eastward wind (+u)
        st_severe = [{"coords_px": (50.0, 100.0), "value": 100.0, "u": 30.0, "v": 0.0}]

        # Direct downwind target at (100, 100)
        val_down, km_down, alpha_down = anisotropic_idw((100.0, 100.0), st_severe)
        assert val_down == 100.0
        assert km_down > 0.0
        assert 95 <= alpha_down <= 235

        # Pairwise comparison: downwind vs upwind directional weighting
        st1_upwind = {"coords_px": (50.0, 100.0), "value": 100.0, "u": 25.0, "v": 0.0}
        st2_downwind = {"coords_px": (150.0, 100.0), "value": 200.0, "u": 25.0, "v": 0.0}
        # Air from st1 blows toward target at (100, 100); air from st2 blows away
        val_mid, _, _ = anisotropic_idw((100.0, 100.0), [st1_upwind, st2_downwind])
        # Under isotropic IDW, result is 150.0; anisotropic steering weights st1 much higher
        assert math.isclose(val_mid, 115.0, abs_tol=1e-2)

    def test_anisotropic_idw_calm_wind_fallback_and_zero_pixel_distance(self):
        """
        Anisotropic IDW with wind < 0.5 m/s or d_px <= 2.0 px must bypass anisotropic steering
        and fallback to isotropic softened kernel (epsilon^2 = 16.0 px^2).
        """
        st_calm = [{"coords_px": (100.0, 100.0), "value": 120.0, "u": 0.2, "v": 0.1}]  # speed ~0.22 m/s < 0.5

        # Query at exact station pixel coordinate (d_px = 0.0 <= 2.0)
        val, km, alpha = anisotropic_idw((100.0, 100.0), st_calm, epsilon_sq=16.0)
        assert val == 120.0
        assert km == 0.0
        assert alpha == 235  # Maximum confidence opacity for collocated monitor

    def test_distance_opacity_taper_thresholds(self):
        """Tests continuous alpha opacity ramp across distance thresholds (45 km to 140 km)."""
        assert calculate_distance_opacity(0.0) == 235
        assert calculate_distance_opacity(44.9) == 235
        assert calculate_distance_opacity(140.0) == 95
        assert calculate_distance_opacity(500.0) == 95

        # Intermediate distance (92.5 km, exact midpoint between 45 and 140)
        alpha_mid = calculate_distance_opacity(92.5)
        expected_mid = int(round(235.0 - 140.0 * 0.5))
        assert alpha_mid == expected_mid


# =============================================================================
# 2. Wind Kinematics & CPF Small-Sample / Edge Distributions
# =============================================================================
class TestTier5WindRoseCPFSmallSampleAndDistributions:
    """Stress-tests Wind Kinematics and CPF Directional Modeling."""

    def test_anemometer_physical_bounds_and_calm_cutoff(self):
        """Wind speed bounds [0.0, 30.0] m/s, direction [0.0, 360.0] deg, calm threshold 0.5 m/s."""
        # Boundary pass
        assert is_anemometer_valid(0.0, 0.0) is True
        assert is_anemometer_valid(30.0, 360.0) is True
        assert is_anemometer_valid(15.0, 180.0) is True

        # Boundary fail: speed > 30.0 m/s
        assert is_anemometer_valid(30.001, 180.0) is False
        assert is_anemometer_valid(-0.01, 180.0) is False

        # Boundary fail: direction outside [0, 360]
        assert is_anemometer_valid(10.0, -0.1) is False
        assert is_anemometer_valid(10.0, 360.01) is False

        # Calm classification
        assert is_calm_wind(0.0) is True
        assert is_calm_wind(0.499) is True
        assert is_calm_wind(0.500) is False

    def test_wazirabad_hardware_vane_offset_blacklist(self):
        """Wazirabad AQMS vane has 140 degree hardware offset and must be blacklisted."""
        assert is_station_blacklisted("Wazirabad") is True
        assert is_station_blacklisted("wazirabad aqms") is True
        assert is_station_blacklisted("PK_WAZ_001") is True
        assert is_station_blacklisted("Wazirabad Station") is True
        assert is_station_blacklisted("Lahore Core") is False

        # is_anemometer_valid and polar conversion must return None for blacklisted station
        assert is_anemometer_valid(5.0, 180.0, "Wazirabad") is False
        assert polar_to_cartesian_wind(5.0, 180.0, "Wazirabad") is None

    def test_wind_polar_cartesian_roundtrip_kinematic_invariants(self):
        """Polar to Cartesian and Cartesian to Polar roundtrip precision across all 16 cardinal sectors."""
        for sector_idx in range(16):
            deg = sector_idx * 22.5
            speed = 8.5
            uv = polar_to_cartesian_wind(speed, deg)
            assert uv is not None
            u, v = uv
            reconstructed_speed, reconstructed_deg = cartesian_to_polar_wind(u, v)
            assert math.isclose(reconstructed_speed, speed, abs_tol=1e-9)
            assert math.isclose(reconstructed_deg, deg, abs_tol=1e-5)

    def test_cpf_small_sample_suppression_strictly_enforced(self):
        """
        Sectors with Nk in [0, 5] valid hours must be suppressed (CPF = None).
        Sectors with Nk >= 6 must evaluate to valid probability.
        """
        obs: List[Dict[str, Any]] = []
        # Sector 0 (North, 0 deg): 5 observations (all exceeding tau) -> must be None
        for _ in range(5):
            obs.append({"wind_speed": 2.0, "wind_direction": 0.0, "value": 200.0})

        # Sector 4 (East, 90 deg): exactly 6 observations (3 exceeding tau) -> must be 0.5000
        for i in range(6):
            val = 200.0 if i < 3 else 50.0
            obs.append({"wind_speed": 2.0, "wind_direction": 90.0, "value": val})

        res = calculate_cpf_rose(obs, threshold_p75=100.0)
        assert res["sectors"][0] is None  # Suppressed (Nk = 5 < 6)
        assert res["sectors"][4] == 0.5000  # Evaluated (Nk = 6 >= 6, mk = 3)
        assert res["sectors"][8] is None  # Missing sector (Nk = 0 < 6)

    def test_cpf_single_valued_distribution_prevents_division_by_zero(self):
        """
        When all observations have identical non-zero values (e.g. 50.0 ug/m3),
        P75 threshold is 50.0. Exceedances c > tau is 0 for all sectors.
        CPF must evaluate to 0.0 without division by zero or NaN.
        """
        obs = [{"wind_speed": 2.0, "wind_direction": 90.0, "value": 50.0} for _ in range(12)]
        res = calculate_cpf_rose(obs)
        assert res["threshold"] == 50.0
        assert res["sectors"][4] == 0.0  # 0 exceedances out of 12 valid hours

    def test_cpf_complete_calm_episode(self):
        """When all observations are calm (<0.5 m/s), calm_ratio must be 1.0 and all sectors suppressed."""
        obs = [{"wind_speed": 0.3, "wind_direction": 180.0, "value": 150.0} for _ in range(20)]
        res = calculate_cpf_rose(obs)
        assert res["calm_ratio"] == 1.0
        assert all(s is None for s in res["sectors"])

    def test_cpf_rose_geometry_canvas_wedge_properties(self):
        """Verifies polygon wedge geometry generation: suppressed sectors get 10px muted stubs."""
        sectors: List[Optional[float]] = [None] * 16
        sectors[4] = 0.80  # Full radius (CPF 0.80)
        sectors[8] = 0.40  # Half radius (CPF 0.40)

        geom = calculate_rose_geometry(sectors, radius=100.0, muted_stub_px=10.0)
        assert len(geom) == 16
        # Suppressed sector
        assert geom[0]["is_suppressed"] is True
        assert geom[0]["radius_px"] == 10.0

        # Full sector
        assert geom[4]["is_suppressed"] is False
        assert geom[4]["radius_px"] == 100.0

        # Half sector
        assert geom[8]["is_suppressed"] is False
        assert geom[8]["radius_px"] == 50.0


# =============================================================================
# 3. Advection Mass Flux Dimensional Integrity & Pathway Truncation
# =============================================================================
class TestTier5AdvectionMassFluxPhysicalGuardAndPathways:
    """Stress-tests atmospheric advection flux and pathway coupling algorithms."""

    def test_advection_flux_strict_dimensionless_aqi_guard(self):
        """
        CRITICAL GUARD: Advection mass flux is strictly disallowed for 'AQI'.
        Must return None for any string variation of AQI.
        """
        for aqi_str in ["AQI", "aqi", " AQI ", "Aqi", ""]:
            flux = calculate_advection_flux(
                source_station=(31.5204, 74.3587),
                receptor_coords=(31.1179, 74.4460),
                pollutant=aqi_str,
                concentration=250.0,
                u_wind=2.0,
                v_wind=-2.0,
            )
            assert flux is None, f"Expected None for pollutant='{aqi_str}'"

    def test_advection_flux_physical_pollutant_valid(self):
        """Conserved physical species ('PM2.5', 'PM10', 'NO2', 'SO2') evaluate to valid mass flux."""
        for pol in ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]:
            # Lahore (31.5204, 74.3587) to Kasur (31.1179, 74.4460) ~45.5 km, bearing ~168 deg (SSE)
            # Wind vector blowing SSE: u = 2.0, v = -5.0 -> speed ~5.38 m/s, bearing ~158 deg
            res = calculate_advection_flux(
                source_station=(31.5204, 74.3587),
                receptor_coords=(31.1179, 74.4460),
                pollutant=pol,
                concentration=150.0,
                u_wind=2.0,
                v_wind=-5.0,
            )
            assert res is not None
            assert res["flux"] > 0.0
            assert math.isclose(res["distance_km"], 45.52, abs_tol=0.1)
            assert res["divergence_deg"] <= 35.0

    def test_advection_flux_boundary_limits_distance_cone_calm(self):
        """Rejects when distance > 180 km, plume divergence > 35 deg, or calm wind < 0.5 m/s."""
        source = (31.5204, 74.3587)
        receptor = (31.1179, 74.4460)

        # 1. Calm wind (< 0.5 m/s)
        assert calculate_advection_flux(source, receptor, "PM2.5", 100.0, 0.2, 0.2) is None

        # 2. Distance > 180 km
        far_receptor = (33.5973, 73.0479)  # Rawalpindi ~268 km
        assert calculate_advection_flux(source, far_receptor, "PM2.5", 100.0, 5.0, -5.0, max_dist_km=180.0) is None

        # 3. Divergence > 35 degrees (wind blowing North while receptor is South)
        assert calculate_advection_flux(source, receptor, "PM2.5", 100.0, 0.0, 5.0, max_cone_deg=35.0) is None

        # 4. Collocated source and receptor (distance = 0.0 km)
        assert calculate_advection_flux(source, source, "PM2.5", 100.0, 2.0, -2.0) is None

    def test_receptor_coupling_truncation_to_top_60_links(self):
        """
        When hundreds of candidate pathways exist, calculate_receptor_coupling
        strictly truncates to top 60 links sorted descending by score.
        """
        candidate_fluxes: List[Dict[str, Any]] = []
        for i in range(120):
            candidate_fluxes.append({
                "source_district": f"District_{i}",
                "receptor_district": "Lahore",
                "mean_flux": float(i + 1),  # Scores 1 to 120
                "bearing_deg": 180.0,
                "distance_km": 50.0,
            })

        # Receptor with isotropic fallback
        ranked = calculate_receptor_coupling(candidate_fluxes, receptor_cpfs={}, max_links=60)
        assert len(ranked) == 60
        # Sorted descending: top link score corresponds to highest mean_flux (120 * 0.25 = 30.0)
        assert ranked[0]["score"] == 30.0
        assert ranked[-1]["score"] == 15.25  # Rank 60 (mean_flux 61 * 0.25)

    def test_net_transport_balance_conservative_accounting(self):
        """Net district transport balance: sum of exporter and importer balances in closed network is 0.0."""
        pathways = [
            {"source_district": "Sheikhupura", "receptor_district": "Lahore", "score": 25.5},
            {"source_district": "Kasur", "receptor_district": "Lahore", "score": 14.5},
            {"source_district": "Lahore", "receptor_district": "Sialkot", "score": 10.0},
        ]
        balances = calculate_net_transport_balance(pathways)
        assert balances["Sheikhupura"] == 25.5  # Exporter
        assert balances["Kasur"] == 14.5        # Exporter
        assert balances["Sialkot"] == -10.0     # Importer
        # Lahore: exported 10.0, imported (25.5 + 14.5 = 40.0) -> net = -30.0
        assert balances["Lahore"] == -30.0
        # Total network balance conserved
        assert math.isclose(sum(balances.values()), 0.0, abs_tol=1e-9)


# =============================================================================
# 4. PEPC AQI Statutory Piecewise Linear Breakpoint Interpolation
# =============================================================================
class TestTier5PEPCAQIBreakpointsAndColorGradients:
    """Stress-tests statutory PEPC piecewise linear AQI interpolation and color scales."""

    def test_pepc_pm25_exact_breakpoint_boundaries(self):
        """
        Statutory PEPC PM2.5 Breakpoints: [0.0, 15.0, 35.0, 70.0, 140.0, 250.0, 350.0]
        Tiers: [0, 50, 100, 150, 200, 300, 400, 500].
        """
        # Exact zero
        assert pepc_calculate_aqi("PM2.5", 0.0) == 0

        # Negative & NaN sanitize to None
        assert pepc_calculate_aqi("PM2.5", -5.0) is None
        assert pepc_calculate_aqi("PM2.5", -0.0001) is None
        assert pepc_calculate_aqi("PM2.5", float("nan")) is None
        assert pepc_calculate_aqi("PM2.5", None) is None

        # Continuous half-open interval checks (BP_low, BP_high]
        assert pepc_calculate_aqi("PM2.5", 15.0) == 50
        assert pepc_calculate_aqi("PM2.5", 15.001) == 50
        assert pepc_calculate_aqi("PM2.5", 35.0) == 100
        assert pepc_calculate_aqi("PM2.5", 70.0) == 150
        assert pepc_calculate_aqi("PM2.5", 140.0) == 200
        assert pepc_calculate_aqi("PM2.5", 250.0) == 300
        assert pepc_calculate_aqi("PM2.5", 350.0) == 400

        # Operational ceiling cap at 500 when concentration > 350.0
        assert pepc_calculate_aqi("PM2.5", 350.001) == 500
        assert pepc_calculate_aqi("PM2.5", 500.0) == 500
        assert pepc_calculate_aqi("PM2.5", 5000.0) == 500

    def test_pepc_us_epa_comparison_points_deterministic_evaluation(self):
        """Verifies deterministic PEPC evaluation at points commonly referenced in EPA US standards."""
        # 12.0 and 12.1 fall in PEPC tier 1 (0 to 15 ug/m3 -> 0 to 50 AQI)
        # val = (50 / 15) * 12.0 = 40; val = (50 / 15) * 12.1 = 40.33 -> 40
        assert pepc_calculate_aqi("PM2.5", 12.0) == 40
        assert pepc_calculate_aqi("PM2.5", 12.1) == 40

        # 35.4 and 35.5 fall in PEPC tier 3 (35 to 70 ug/m3 -> 100 to 150 AQI)
        # val = 100 + (50 / 35) * 0.4 = 100.57 -> 101
        # val = 100 + (50 / 35) * 0.5 = 100.71 -> 101
        assert pepc_calculate_aqi("PM2.5", 35.4) == 101
        assert pepc_calculate_aqi("PM2.5", 35.5) == 101

    def test_pepc_all_six_criteria_pollutants_breakpoint_limits(self):
        """Verifies zero, mid-bracket, and ceiling clamp for all 6 statutory pollutants."""
        pollutants = {
            "PM10": (550.0, 75.0, 50),
            "SO2": (1600.0, 60.0, 50),
            "NO2": (580.0, 40.0, 50),
            "O3": (550.0, 65.0, 50),
            "CO": (40.0, 2.5, 50),
        }
        for pol, (ceiling, mid_c, mid_aqi) in pollutants.items():
            assert pepc_calculate_aqi(pol, 0.0) == 0
            assert pepc_calculate_aqi(pol, -1.0) is None
            assert pepc_calculate_aqi(pol, mid_c) == mid_aqi
            assert pepc_calculate_aqi(pol, ceiling + 10.0) == 500

    def test_pepc_composite_aqi_particulate_governance(self):
        """Statutory composite AQI rule: composite = max(I_PM2.5, I_PM10)."""
        assert pepc_composite_aqi(120, 80) == 120
        assert pepc_composite_aqi(70, 150) == 150
        assert pepc_composite_aqi(None, 95) == 95
        assert pepc_composite_aqi(110, None) == 110
        assert pepc_composite_aqi(None, None) is None

    def test_pepc_color_palette_and_continuous_gradient_stops(self):
        """Verifies 7 discrete category colors and continuous 7-stop PEQS RGB gradient ramp."""
        # Category descriptors and hex codes
        assert pepc_get_color(45) == "#00B050"    # Good
        assert pepc_get_color(80) == "#92D050"    # Satisfactory
        assert pepc_get_color(130) == "#FFFF00"   # Moderate
        assert pepc_get_color(180) == "#ED7D31"   # Unhealthy (Sensitive)
        assert pepc_get_color(250) == "#FF0000"   # Unhealthy
        assert pepc_get_color(350) == "#7030A0"   # Very Unhealthy
        assert pepc_get_color(450) == "#C00000"   # Hazardous
        assert pepc_get_color(None) == "#808080"  # Neutral Gray

        # Continuous PEQS RGB stops relative to reference limit (35 ug/m3 for PM2.5)
        ref = 35.0
        # Stop 0 (0.0x ref): Clean Green (58, 165, 93)
        assert pepc_interpolate_color(0.0, ref) == (58, 165, 93)
        # Stop 2 (1.0x ref): Yellow (242, 194, 48)
        assert pepc_interpolate_color(35.0, ref) == (242, 194, 48)
        # Stop 6 (6.0x ref): Deep Maroon (90, 21, 48)
        assert pepc_interpolate_color(210.0, ref) == (90, 21, 48)
        assert pepc_interpolate_color(500.0, ref) == (90, 21, 48)


# =============================================================================
# 5. Temporal QC Cleaning, Logger Holds, & 75% Completeness
# =============================================================================
class TestTier5TemporalQCHoldFiltersAndCompleteness:
    """Stress-tests temporal quality control filters, sensor freezes, and aggregation completeness."""

    def test_temporal_qc_empty_and_short_series_edge_cases(self):
        """Empty series and 1-2 element series must not crash or trigger logger hold filter."""
        # Empty array
        cleaned_empty, spikes_empty = temporal_qc_clean([], 35.0, "PM2.5")
        assert cleaned_empty == []
        assert spikes_empty == 0
        assert check_completeness([]) is None
        assert subhourly_lerp([], 0.5) is None

        # 1-element and 2-element series (i < 2 index guard prevents hold filter)
        cleaned_short, _ = temporal_qc_clean([50.0, 50.0], 35.0, "PM2.5")
        assert cleaned_short == [50.0, 50.0]

    def test_temporal_qc_step0_negative_zero_nan_purge(self):
        """Step 0 converts non-positive values, NaNs, and infinities to None."""
        series = [0.0, -15.0, float("nan"), float("inf"), float("-inf"), 45.0, None]
        cleaned, _ = temporal_qc_clean(series, 35.0, "PM2.5")
        assert cleaned == [None, None, None, None, None, 45.0, None]

    def test_temporal_qc_3h_logger_hold_extended_freeze_and_aqi_exemption(self):
        """
        Physical pollutants: identical values for 3+ consecutive hours nulled starting at i=2.
        For 5-hour freeze [50, 50, 50, 50, 50], indices 2, 3, 4 are nulled.
        AQI pollutant: integer index is legitimately allowed to hold and strictly exempt.
        """
        freeze_series = [50.0, 50.0, 50.0, 50.0, 50.0, 60.0]

        # 1. Physical PM2.5: indices 2, 3, 4 nulled
        cleaned_pm, _ = temporal_qc_clean(freeze_series, 35.0, "PM2.5")
        assert cleaned_pm[0] == 50.0
        assert cleaned_pm[1] == 50.0
        assert cleaned_pm[2] is None
        assert cleaned_pm[3] is None
        assert cleaned_pm[4] is None
        assert cleaned_pm[5] == 60.0

        # 2. AQI pollutant: exempt from hold filter
        cleaned_aqi, _ = temporal_qc_clean(freeze_series, 100.0, "AQI")
        assert cleaned_aqi == freeze_series

    def test_temporal_qc_uniform_series_fails_75_percent_completeness(self):
        """
        24-hour uniform series of 50.0 ug/m3.
        Hold filter nulls all hours except indices 0 and 1 (leaving 2 valid hours out of 24).
        Valid ratio = 2 / 24 = 8.3% < 75%, so check_completeness must return None!
        """
        uniform_24h = [50.0] * 24
        cleaned, _ = temporal_qc_clean(uniform_24h, 35.0, "PM2.5")
        valid_count = sum(1 for v in cleaned if v is not None)
        assert valid_count == 2
        # Fails 75% regulatory requirement (needs >= 18 hours)
        assert check_completeness(cleaned) is None

    def test_temporal_qc_spike_filter_edge_and_center_activation(self):
        """
        7-Hour rolling median spike filter requires window size >= 3,
        v > 4.0 * M_i, and v > 3.0 * ref_limit.
        """
        ref = 35.0
        # Median is 50.0. Spike is 500.0 (> 4*50=200 and > 3*35=105).
        series = [50.0, 50.0, 50.0, 500.0, 50.0, 50.0, 50.0]
        cleaned, spikes = temporal_qc_clean(series, ref, "PM2.5")
        assert spikes == 1
        assert cleaned[3] is None  # Spike nulled!

    def test_subhourly_animation_lerp_endpoints_and_clamping(self):
        """Subhourly lerp smoothly interpolates between hours, handles None endpoints, and clamps bounds."""
        series = [10.0, 20.0, None, 40.0]

        # Valid interpolation between hours 0 and 1
        assert subhourly_lerp(series, 0.0) == 10.0
        assert subhourly_lerp(series, 0.5) == 15.0
        assert subhourly_lerp(series, 1.0) == 20.0

        # One endpoint is None
        assert subhourly_lerp(series, 1.5) == 20.0  # a=20, b=None -> returns a
        assert subhourly_lerp(series, 2.5) == 40.0  # a=None, b=40 -> returns b

        # Clamping out-of-bounds positions
        assert subhourly_lerp(series, -10.0) == 10.0
        assert subhourly_lerp(series, 100.0) == 40.0


# =============================================================================
# 6. Equirectangular Projection & Greedy Labeling Boundary Collisions
# =============================================================================
class TestTier5EquirectangularProjectionAndGreedyLabeling:
    """Stress-tests geographic projection mathematics and collision-free label placements."""

    def test_equirectangular_forward_and_inverse_roundtrip_precision(self):
        """
        Tests forward and inverse projection across provincial corners and centroid.
        Roundtrip error |lat - rev_lat| and |lon - rev_lon| must be exact machine precision zero (<1e-9).
        """
        test_coords = [
            (27.55, 69.10),   # South-West provincial boundary
            (34.30, 75.75),   # North-East provincial boundary
            (31.00, 72.50),   # Standard parallel center
            (31.5204, 74.3587), # Lahore urban core
        ]
        for lat, lon in test_coords:
            px, py = equirectangular_project(lat, lon, width_px=1200.0, height_px=900.0)
            rev_lat, rev_lon = equirectangular_unproject(px, py, width_px=1200.0, height_px=900.0)
            assert math.isclose(lat, rev_lat, abs_tol=1e-9)
            assert math.isclose(lon, rev_lon, abs_tol=1e-9)

    def test_aabb_collision_detection_matrix(self):
        """AABB collision logic: overlapping boxes collide, touching boxes do NOT collide."""
        b1 = (10.0, 10.0, 20.0, 20.0)  # [10, 30] x [10, 30]

        # Overlapping box
        b_overlap = (20.0, 20.0, 20.0, 20.0)
        assert check_aabb_collision(b1, b_overlap) is True

        # Touching boundary (adjacent edge at x=30.0) - should NOT collide
        b_touching = (30.0, 10.0, 20.0, 20.0)
        assert check_aabb_collision(b1, b_touching) is False

        # Disjoint box
        b_disjoint = (50.0, 50.0, 20.0, 20.0)
        assert check_aabb_collision(b1, b_disjoint) is False

    def test_greedy_label_placement_coincident_anchors_and_leader_lines(self):
        """
        Multiple district labels requested at identical anchor point (500, 500).
        Labels must displace through the 12 candidate offsets without crashing,
        activating leader lines once displacement exceeds 20.0 px.
        """
        labels = [
            {"district_id": f"D_{i}", "text": f"District {i}", "anchor_x": 500.0, "anchor_y": 500.0, "width": 50.0, "height": 15.0}
            for i in range(15)
        ]
        placed = greedy_label_placement(labels)
        assert len(placed) == 15

        # First label placed at zero offset (0.0, 0.0)
        assert placed[0]["offset_x"] == 0.0
        assert placed[0]["offset_y"] == 0.0
        assert placed[0]["has_leader_line"] is False

        # Later labels displace to avoid collision and trigger leader lines
        displaced_leaders = [p for p in placed if p["has_leader_line"]]
        assert len(displaced_leaders) > 0
        for p in displaced_leaders:
            disp = math.hypot(p["offset_x"], p["offset_y"])
            assert disp > 20.0


# =============================================================================
# 7. User CSV Ingestion Pipeline Ragged Rows & Dead-Letter Quarantine
# =============================================================================
class TestTier5CSVIngestionResilienceAndDeadLetterQuarantine:
    """Stress-tests CSV Ingestion Pipeline against corrupt, ragged, and adversarial payloads."""

    @pytest.fixture
    def adapter(self) -> UserCSVIngestionAdapter:
        return UserCSVIngestionAdapter()

    def test_csv_ingestion_empty_and_missing_mandatory_headers(self, adapter: UserCSVIngestionAdapter):
        """Empty CSV or missing mandatory columns returns failed status and descriptive file error."""
        # Completely empty
        res_empty = adapter.ingest_csv("")
        assert res_empty.status == "failed"
        assert len(res_empty.file_errors) > 0

        # Missing 'pollutant' and 'value' columns
        csv_missing = (
            "timestamp,station_id,station_name,district,latitude,longitude\n"
            "2026-11-10 12:00,S1,Gulberg,Lahore,31.5097,74.3478\n"
        )
        res_missing = adapter.ingest_csv(csv_missing)
        assert res_missing.status == "failed"
        assert any("pollutant" in err and "value" in err for err in res_missing.file_errors)

    def test_csv_ingestion_ragged_rows_and_dead_letter_quarantine(self, adapter: UserCSVIngestionAdapter):
        """
        Adversarial CSV containing:
        - Negative value (-10.0) -> quarantined (VALIDATION_ERROR)
        - Zero value (0.0) -> quarantined (QC_PURGED)
        - Concentration > 5000.0 (5001.0) -> quarantined (VALIDATION_ERROR)
        - Excluded station (OneNetwork Station 25) -> quarantined (STATION_EXCLUDED)
        - Missing coordinates -> quarantined (COORDINATES_MISSING_OR_UNRESOLVABLE)
        - Valid crisis concentration (1200.0) -> valid with QC_EXCEEDANCE_EXTREME tag
        - Empty row -> cleanly skipped
        """
        adversarial_csv = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            "2026-11-10 12:00,S1,Gulberg III,Lahore,31.5097,74.3478,pm25,120.0\n"
            "2026-11-10 12:00,S2,Bad Negative,Lahore,31.5097,74.3478,pm25,-10.0\n"
            "2026-11-10 12:00,S3,Zero Value,Lahore,31.5097,74.3478,pm25,0.0\n"
            "2026-11-10 12:00,S4,Extreme Exceed,Lahore,31.5097,74.3478,pm25,5001.0\n"
            "2026-11-10 12:00,S5,OneNetwork Station 25,Lahore,31.5,74.3,pm25,50.0\n"
            "2026-11-10 12:00,S6,Unresolvable Station,Unknown,99.0,99.0,pm25,50.0\n"
            "\n"  # Ragged empty line
            "2026-11-10 12:00,S7,Severe Smog Peak,Lahore,31.5097,74.3478,pm25,1200.0\n"
        )
        res = adapter.ingest_csv(adversarial_csv)
        assert res.valid_count == 2  # S1 and S7
        assert res.quarantine_count == 5  # S2, S3, S4, S5, S6
        assert res.status == "partial_quarantine"

        # Verify specific quarantine error types
        error_types = [q.error_type for q in res.quarantine_records]
        assert "VALIDATION_ERROR" in error_types  # S2 and S4
        assert "QC_PURGED" in error_types        # S3
        assert "STATION_EXCLUDED" in error_types # S5
        assert "COORDINATES_MISSING_OR_UNRESOLVABLE" in error_types # S6

        # Verify S7 received QC_EXCEEDANCE_EXTREME tag
        s7_obs = next(o for o in res.observations if o.station_id == "S7")
        assert "QC_EXCEEDANCE_EXTREME" in s7_obs.qc_flags

    def test_csv_ingestion_canonical_gps_coordinate_repair(self, adapter: UserCSVIngestionAdapter):
        """
        Sahiwal station telemetry with corrupt (0, 0) GPS coordinates
        must be automatically repaired to canonical coordinates (30.6682, 73.1114).
        """
        csv_sahiwal = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            "2026-11-10 12:00,PK_SWL_001,Sahiwal City AQMS,Sahiwal,0.0,0.0,pm25,95.0\n"
        )
        res = adapter.ingest_csv(csv_sahiwal)
        assert res.valid_count == 1
        obs = res.observations[0]
        assert math.isclose(obs.latitude, 30.6682, rel_tol=1e-4)
        assert math.isclose(obs.longitude, 73.1114, rel_tol=1e-4)

    def test_csv_ingestion_wazirabad_anemometer_blacklisting(self, adapter: UserCSVIngestionAdapter):
        """Wazirabad wind readings in CSV must be nulled and tagged with WIND_BLACKLIST_WAZIRABAD."""
        csv_wazirabad = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value,wind_speed,wind_direction\n"
            "2026-11-10 12:00,PK_WAZ_001,Wazirabad Station,Gujranwala,32.4428,74.1197,pm25,85.0,5.5,180.0\n"
        )
        res = adapter.ingest_csv(csv_wazirabad)
        assert res.valid_count == 1
        obs = res.observations[0]
        assert obs.wind_speed_ms is None
        assert obs.wind_direction_deg is None
        assert "WIND_BLACKLIST_WAZIRABAD" in obs.qc_flags

    def test_csv_ingestion_multi_encoding_byte_streams(self, adapter: UserCSVIngestionAdapter):
        """
        Tests ingestion against raw byte streams encoded with:
        1. UTF-8 with BOM (utf-8-sig)
        2. Latin-1 with accented characters
        """
        # 1. UTF-8 with BOM
        utf8_sig_content = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            "2026-11-10 12:00,S1,Gulberg III,Lahore,31.5097,74.3478,pm25,110.0\n"
        ).encode("utf-8-sig")
        res_bom = adapter.ingest_csv(utf8_sig_content)
        assert res_bom.valid_count == 1

        # 2. Latin-1 bytes with accent (Café Station)
        latin1_content = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            "2026-11-10 12:00,S2,Café Gulberg,Lahore,31.5097,74.3478,pm25,80.0\n"
        ).encode("latin-1")
        res_latin = adapter.ingest_csv(latin1_content)
        assert res_latin.valid_count == 1
        assert "Gulberg" in res_latin.observations[0].station_name

    def test_csv_ingestion_corrupt_and_empty_timestamp_handling(self, adapter: UserCSVIngestionAdapter):
        """
        Corrupt timestamp strings fall back to valid UTC datetime without crash;
        empty timestamp strings fail schema validation and are quarantined.
        """
        # Corrupt date string -> falls back to current UTC
        csv_corrupt = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            "NOT_A_DATE_STRING,S1,Gulberg,Lahore,31.5,74.3,pm25,50.0\n"
        )
        res_corrupt = adapter.ingest_csv(csv_corrupt)
        assert res_corrupt.valid_count == 1
        assert res_corrupt.observations[0].timestamp.tzinfo == timezone.utc

        # Empty timestamp -> fails Pydantic validation
        csv_empty = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            ",S2,Gulberg,Lahore,31.5,74.3,pm25,50.0\n"
        )
        res_empty = adapter.ingest_csv(csv_empty)
        assert res_empty.quarantine_count == 1
        assert res_empty.quarantine_records[0].error_type == "VALIDATION_ERROR"

    def test_csv_ingestion_multi_pollutant_merging_composite_aqi(self, adapter: UserCSVIngestionAdapter):
        """
        Merges single-pollutant rows sharing station_id and timestamp
        into consolidated composite observations with composite PEPC AQI.
        """
        csv_multi = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            "2026-11-10 12:00,S1,Gulberg III,Lahore,31.5097,74.3478,pm25,35.0\n"
            "2026-11-10 12:00,S1,Gulberg III,Lahore,31.5097,74.3478,pm10,150.0\n"
            "2026-11-10 12:00,S1,Gulberg III,Lahore,31.5097,74.3478,no2,40.0\n"
        )
        res = adapter.ingest_csv(csv_multi)
        assert res.valid_count == 3
        merged = res.get_merged_observations()
        assert len(merged) == 1
        m = merged[0]
        assert m.pm25_qc == 35.0
        assert m.pm10_qc == 150.0
        assert m.no2_qc == 40.0
        # PM2.5 at 35.0 -> AQI 100; PM10 at 150.0 -> AQI 100; composite = 100
        assert m.pepc_aqi == 100


# =============================================================================
# 8. Transboundary Atmospheric Inflow/Outflow Boundaries
# =============================================================================
class TestTier5TransboundaryAtmosphericBoundaryLimits:
    """Stress-tests transboundary atmospheric corridor limits and border node normal projections."""

    def test_transboundary_district_flux_corridor_and_calm_limits(self):
        """
        Districts outside 120 km border corridor or experiencing calm winds (<0.5 m/s)
        evaluate to exactly 0.0 flux.
        """
        india_sectors = [4, 5, 6]  # E, ESE, SE

        # 1. Beyond 120 km corridor (e.g. 125 km)
        flux_far = calculate_district_transboundary_flux(
            border_distance_km=125.0,
            india_sectors=india_sectors,
            concentration=300.0,
            u_wind=-3.0,
            v_wind=0.0,
        )
        assert flux_far == 0.0

        # 2. Calm wind (< 0.5 m/s)
        flux_calm = calculate_district_transboundary_flux(
            border_distance_km=25.0,
            india_sectors=india_sectors,
            concentration=300.0,
            u_wind=0.2,
            v_wind=0.1,
        )
        assert flux_calm == 0.0

    def test_transboundary_inflow_outflow_and_neutral_directional_states(self):
        """
        Wind blowing FROM India into Pakistan (sector in india_sectors) -> positive inflow (+).
        Wind blowing FROM Pakistan into India (opposite sector) -> negative outflow (-).
        Wind blowing parallel to border -> neutral 0.0.
        """
        india_sectors = [4]  # East (90 deg)
        border_km = 30.0
        c = 200.0
        decay = math.exp(-30.0 / 100.0)

        # Inflow: Easterly wind (FROM East, blowing West, u = -4.0, v = 0.0)
        inflow = calculate_district_transboundary_flux(
            border_distance_km=border_km,
            india_sectors=india_sectors,
            concentration=c,
            u_wind=-4.0,
            v_wind=0.0,
        )
        expected_mag = c * 4.0 * decay
        assert math.isclose(inflow, expected_mag, rel_tol=1e-3)

        # Outflow: Westerly wind (FROM West, blowing East, u = +4.0, v = 0.0)
        outflow = calculate_district_transboundary_flux(
            border_distance_km=border_km,
            india_sectors=india_sectors,
            concentration=c,
            u_wind=4.0,
            v_wind=0.0,
        )
        assert math.isclose(outflow, -expected_mag, rel_tol=1e-3)

        # Neutral: Northerly wind (FROM North, blowing South, u = 0.0, v = -4.0)
        neutral = calculate_district_transboundary_flux(
            border_distance_km=border_km,
            india_sectors=india_sectors,
            concentration=c,
            u_wind=0.0,
            v_wind=-4.0,
        )
        assert neutral == 0.0

    def test_transboundary_index_estimated_districts_excluded_from_provincial_totals(self):
        """
        Monitored districts contribute to provincial inflow/outflow totals;
        imputed/fallback districts (is_estimated = True) are excluded from totals.
        """
        districts = [
            # Monitored district with inflow
            {
                "district_id": "Lahore",
                "border_distance_km": 25.0,
                "india_sectors": [4],
                "concentration": 200.0,
                "u": -3.0,
                "v": 0.0,
                "is_estimated": False,
            },
            # Estimated district with inflow (must be excluded from inflow_total)
            {
                "district_id": "Kasur_Imputed",
                "border_distance_km": 20.0,
                "india_sectors": [4],
                "concentration": 250.0,
                "u": -3.0,
                "v": 0.0,
                "is_estimated": True,
            },
        ]
        res = calculate_transboundary_index(districts)
        # Lahore flux = 200 * 3.0 * exp(-25/100) = 600 * 0.7788 = 467.28
        lahore_val = res["district_values"]["Lahore"]
        assert lahore_val > 0.0
        # Provincial inflow total equals monitored Lahore only
        assert res["inflow_total"] == lahore_val
        assert res["outflow_total"] == 0.0
        assert res["net_flux"] == lahore_val
