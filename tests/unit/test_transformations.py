"""
Deterministic Unit Tests for Scientific Transformation Engine.
Tests all mathematical transformation modules against exact specifications and test fixtures:
- Geodesy (Haversine distance, forward bearing, angular divergence, 16-sector mapping)
- Wind Kinematics (Polar-to-Cartesian, Cartesian-to-Polar, bounds, Wazirabad blacklist)
- Geodesic IDW (T1) and Anisotropic continuous IDW (T2)
- CPF Polar Rose (T5) with calm exclusion and Nk < 6 suppression
- Physical Advection Flux (T6) with AQI physical dimension guard and Receptor Coupling (T7)
- Transboundary Inflow/Outflow Index (T8) with border belt and normal vectors
- Equirectangular Projection & Greedy AABB Label Placement (T11)
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
    polar_to_cartesian_wind,
    cartesian_to_polar_wind,
    wind_direction_to_bearing,
    is_anemometer_valid,
    is_calm_wind,
    is_station_blacklisted,
    blend_winds,
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
)
from src.domain.math.flux import (
    calculate_advection_flux,
    calculate_receptor_coupling,
    calculate_net_transport_balance,
)
from src.domain.math.transboundary import (
    calculate_district_transboundary_flux,
    calculate_border_normal_flux,
    calculate_transboundary_index,
)
from src.domain.math.projection import (
    equirectangular_project,
    equirectangular_unproject,
    check_aabb_collision,
    greedy_label_placement,
)


class TestGeodesyTransformations:
    """Tests Haversine distance, bearings, divergence, and 16-sector mappings."""

    def test_lahore_to_sheikhupura_distance_fixture(self):
        """Spec Miner Fixture §4.2: Lahore to Sheikhupura = 22.3583 km."""
        lhr_lat, lhr_lon = 31.549, 74.364
        skp_lat, skp_lon = 31.692, 74.198

        dist_km = haversine_distance(lhr_lat, lhr_lon, skp_lat, skp_lon)
        assert abs(dist_km - 22.3583) < 0.001, f"Expected 22.3583 km, got {dist_km}"

    def test_lahore_to_kasur_fixture(self):
        """Authoritative reference fixture: Lahore to Kasur = 45.51775 km."""
        dist_km = haversine_distance(31.5204, 74.3587, 31.1179, 74.4460)
        assert abs(dist_km - 45.51775) < 0.05, f"Expected ~45.52 km, got {dist_km}"

    def test_coincident_points_zero_distance(self):
        """Distance between identical coordinates must be exactly 0.0."""
        assert haversine_distance(31.549, 74.364, 31.549, 74.364) == 0.0

    def test_lahore_to_sheikhupura_bearing_fixture(self):
        """Spec Miner Fixture §4.2: Forward bearing Lahore -> Sheikhupura = 315.3748 deg."""
        lhr_lat, lhr_lon = 31.549, 74.364
        skp_lat, skp_lon = 31.692, 74.198

        brg = forward_bearing(lhr_lat, lhr_lon, skp_lat, skp_lon)
        assert abs(brg - 315.3748) < 0.01, f"Expected 315.3748 deg, got {brg}"

    def test_back_bearing_calculation(self):
        """Reciprocal arrival bearing calculation."""
        lhr_lat, lhr_lon = 31.549, 74.364
        skp_lat, skp_lon = 31.692, 74.198

        b_brg = back_bearing(lhr_lat, lhr_lon, skp_lat, skp_lon)
        f_brg_rev = forward_bearing(skp_lat, skp_lon, lhr_lat, lhr_lon)
        assert abs(b_brg - f_brg_rev) < 1e-6

    def test_angular_divergence_shortest_arc(self):
        """Angular divergence calculation across 0/360 wrap-around."""
        # Collinear: 0 deg
        assert angular_divergence(90.0, 90.0) == 0.0
        # Normal acute angle
        assert angular_divergence(105.0, 90.0) == 15.0
        # Wraparound across North meridian (350 deg and 10 deg -> 20 deg)
        assert angular_divergence(350.0, 10.0) == 20.0
        assert angular_divergence(10.0, 350.0) == 20.0
        # Exactly opposite: 180 deg
        assert angular_divergence(0.0, 180.0) == 180.0

    def test_16_sector_polar_mapping(self):
        """16 compass sectors (22.5 deg width) centering on cardinal directions."""
        # North (Sector 0)
        assert degrees_to_sector_16(0.0) == 0
        assert degrees_to_sector_16(355.0) == 0
        assert degrees_to_sector_16(11.24) == 0

        # NNE (Sector 1) starts at 11.25
        assert degrees_to_sector_16(11.25) == 1
        assert degrees_to_sector_16(22.5) == 1

        # East (Sector 4: 90 deg)
        assert degrees_to_sector_16(90.0) == 4

        # South (Sector 8: 180 deg)
        assert degrees_to_sector_16(180.0) == 8

        # West (Sector 12: 270 deg)
        assert degrees_to_sector_16(270.0) == 12

        # Sector to degrees center
        assert sector_16_to_degrees(0) == 0.0
        assert sector_16_to_degrees(4) == 90.0
        assert sector_16_to_degrees(8) == 180.0
        assert sector_16_to_degrees(12) == 270.0


class TestWindKinematicsAndQC:
    """Tests polar/cartesian conversions, anemometer bounds, and blacklist."""

    def test_polar_to_cartesian_cardinal_directions(self):
        """Verifies (u, v) kinematic flow vectors for 4 cardinal directions."""
        # Wind FROM East (90 deg) blows TO West (u = -10, v = 0)
        u, v = polar_to_cartesian_wind(10.0, 90.0)
        assert abs(u - (-10.0)) < 1e-6
        assert abs(v - 0.0) < 1e-6

        # Wind FROM South (180 deg) blows TO North (u = 0, v = 10)
        u, v = polar_to_cartesian_wind(10.0, 180.0)
        assert abs(u - 0.0) < 1e-6
        assert abs(v - 10.0) < 1e-6

        # Wind FROM West (270 deg) blows TO East (u = 10, v = 0)
        u, v = polar_to_cartesian_wind(10.0, 270.0)
        assert abs(u - 10.0) < 1e-6
        assert abs(v - 0.0) < 1e-6

        # Wind FROM North (0 deg) blows TO South (u = 0, v = -10)
        u, v = polar_to_cartesian_wind(10.0, 0.0)
        assert abs(u - 0.0) < 1e-6
        assert abs(v - (-10.0)) < 1e-6

    def test_cartesian_to_polar_roundtrip(self):
        """Roundtrip conversion preserves speed and direction."""
        speeds = [0.5, 3.2, 10.0, 25.0]
        directions = [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0]

        for spd in speeds:
            for dr in directions:
                u, v = polar_to_cartesian_wind(spd, dr)
                rec_spd, rec_dr = cartesian_to_polar_wind(u, v)
                assert abs(rec_spd - spd) < 1e-4
                assert abs(rec_dr - dr) < 1e-4

    def test_anemometer_bounds_quality_control(self):
        """Enforces [0, 30 m/s] speed and [0, 360 deg] direction bounds."""
        assert is_anemometer_valid(15.0, 180.0) is True
        assert is_anemometer_valid(0.0, 0.0) is True
        assert is_anemometer_valid(30.0, 360.0) is True

        # Unphysical speed (negative or extreme error codes like 99.9)
        assert is_anemometer_valid(-1.0, 180.0) is False
        assert is_anemometer_valid(30.1, 180.0) is False
        assert is_anemometer_valid(99.9, 180.0) is False
        assert is_anemometer_valid(None, 180.0) is False
        assert is_anemometer_valid(10.0, -5.0) is False
        assert is_anemometer_valid(10.0, 361.0) is False

    def test_wazirabad_station_blacklist(self):
        """Station 'Wazirabad' must be blacklisted due to persistent 140 deg physical offset."""
        assert is_station_blacklisted("Wazirabad") is True
        assert is_station_blacklisted("wazirabad aqms") is True
        assert is_station_blacklisted("PK_WAZ_001") is True
        assert is_station_blacklisted("Lahore Town Hall") is False

        # Anemometer validation returns False for blacklisted station
        assert is_anemometer_valid(5.0, 120.0, station_name="Wazirabad") is False
        assert polar_to_cartesian_wind(5.0, 120.0, station_name="Wazirabad") is None

    def test_calm_wind_classification(self):
        """Wind speeds < 0.5 m/s classified as calm."""
        assert is_calm_wind(0.0) is True
        assert is_calm_wind(0.49) is True
        assert is_calm_wind(0.5) is False
        assert is_calm_wind(1.0) is False
        assert is_calm_wind(None) is True


class TestSpatialIDWTransformations:
    """Tests Discrete Geodesic IDW (T1) and Anisotropic Continuous IDW (T2)."""

    def test_discrete_geodesic_idw_reference_fixture(self):
        """
        Spec Miner Fixture §4.2:
        Target: (31.600, 74.300)
        St1: (31.549, 74.364), val=200.0 (d=8.3017 km, w=0.014510)
        St2: (31.692, 74.198), val=150.0 (d=14.0669 km, w=0.005054)
        St3: (31.436, 73.102), val=100.0 (d=115.0139 km, w=0.000076)
        Expected interpolated value = 186.7488
        """
        target = (31.600, 74.300)
        stations = [
            {"coords": (31.549, 74.364), "value": 200.0},
            {"coords": (31.692, 74.198), "value": 150.0},
            {"coords": (31.436, 73.102), "value": 100.0},
        ]
        val = discrete_geodesic_idw(target, stations, power=2.0, d0=5.0)
        assert val is not None
        assert abs(val - 186.7488) < 0.01, f"Expected 186.7488, got {val}"

    def test_idw_zero_distance_singularity_clamping(self):
        """
        Coincident point (d = 0) is clamped to d0 = 5.0 km,
        yielding finite weight w = 1 / (5^2) = 0.04 (TRANSFORMATION_LOGIC_SPEC.md §2.1.2).
        """
        target = (31.500, 74.300)
        stations = [
            {"coords": (31.500, 74.300), "value": 100.0},
        ]
        val = discrete_geodesic_idw(target, stations, power=2.0, d0=5.0)
        assert val == 100.0

    def test_idw_empty_or_all_null_returns_none(self):
        """If no valid monitored stations exist, IDW returns None gracefully."""
        target = (31.5, 74.3)
        assert discrete_geodesic_idw(target, []) is None
        assert discrete_geodesic_idw(target, [{"coords": (31.5, 74.3), "value": None}]) is None

    def test_anisotropic_wind_steered_idw_downwind_vs_upwind(self):
        """
        T2: Anisotropic continuous IDW amplifies downwind kernel and attenuates upwind kernel.
        Station at (100, 100) with wind blowing towards East (+x, u=5.0, v=0.0).
        Downwind point at (120, 100) should have higher weight than upwind point at (80, 100).
        """
        station = [{"coords_px": (100.0, 100.0), "value": 200.0, "u": 5.0, "v": 0.0}]

        # Downwind point (x = 120, y = 100, dx = +20): cos(alpha) = +1.0
        val_down, km_down, alpha_down = anisotropic_idw(
            (120.0, 100.0), station, scale=1.0, epsilon_sq=16.0
        )
        assert val_down == 200.0

        # Multi-station test: 1 reporting high downwind, 1 reporting low upwind
        stations = [
            {"coords_px": (100.0, 100.0), "value": 300.0, "u": 3.0, "v": 0.0},
            {"coords_px": (140.0, 100.0), "value": 100.0, "u": 3.0, "v": 0.0},
        ]
        # Query at (120, 100):
        # Station 1 (100, 100) blows towards query (downwind, amplified)
        # Station 2 (140, 100) blows away from query (upwind, attenuated to 0.3)
        val, _, _ = anisotropic_idw((120.0, 100.0), stations, scale=1.0)
        # Therefore interpolated value at midpoint should be heavily skewed towards station 1 (>200)
        assert val > 200.0, f"Expected >200 due to wind steering, got {val}"

    def test_distance_opacity_taper(self):
        """Distance opacity decays from 235 (<45 km) to 95 (>140 km)."""
        assert calculate_distance_opacity(30.0) == 235
        assert calculate_distance_opacity(44.9) == 235
        assert calculate_distance_opacity(150.0) == 95
        # Midpoint: (45 + 140) / 2 = 92.5 km -> 235 - 70 = 165
        mid_alpha = calculate_distance_opacity(92.5)
        assert 164 <= mid_alpha <= 166


class TestCPFWindRoseTransformations:
    """Tests 16-sector CPF rose, calm exclusion, and small-sample suppression."""

    def test_attock_cpf_fixture_with_small_sample_suppression(self):
        """
        Spec Miner Fixture §4.4: Attock PM2.5
        tau = 95.8, calm fraction = 0.898
        Sector 9 (202.5 deg): N=6, m=2 -> CPF = 2/6 = 0.3333
        Sector 10 (225.0 deg): N=6, m=1 -> CPF = 1/6 = 0.1667
        Sector 12 (270.0 deg): N=7, m=0 -> CPF = 0.0
        Sector 13 (292.5 deg): N=5, m=0 -> CPF = None (suppressed N < 6)
        Sector 4 (90.0 deg): N=4 -> CPF = None
        Sector 5 (112.5 deg): N=3 -> CPF = None
        """
        observations = []
        tau = 95.8

        # Sector 9 (202.5 deg): 6 obs (2 exceedances, 4 non-exceedances)
        for _ in range(2):
            observations.append({"value": 120.0, "wind_speed": 3.0, "wind_direction": 202.5})
        for _ in range(4):
            observations.append({"value": 60.0, "wind_speed": 3.0, "wind_direction": 202.5})

        # Sector 10 (225.0 deg): 6 obs (1 exceedance, 5 non-exceedances)
        observations.append({"value": 110.0, "wind_speed": 2.5, "wind_direction": 225.0})
        for _ in range(5):
            observations.append({"value": 50.0, "wind_speed": 2.5, "wind_direction": 225.0})

        # Sector 12 (270.0 deg): 7 obs (0 exceedances)
        for _ in range(7):
            observations.append({"value": 40.0, "wind_speed": 4.0, "wind_direction": 270.0})

        # Sector 13 (292.5 deg): 5 obs (0 exceedances, suppressed N < 6)
        for _ in range(5):
            observations.append({"value": 45.0, "wind_speed": 3.5, "wind_direction": 292.5})

        # Sector 4 (90.0 deg): 4 obs (suppressed)
        for _ in range(4):
            observations.append({"value": 50.0, "wind_speed": 2.0, "wind_direction": 90.0})

        # Sector 5 (112.5 deg): 3 obs (1 exceedance, suppressed N < 6)
        observations.append({"value": 105.0, "wind_speed": 2.0, "wind_direction": 112.5})
        for _ in range(2):
            observations.append({"value": 50.0, "wind_speed": 2.0, "wind_direction": 112.5})

        # Add calm observations to verify calm ratio
        # Non-calm total = 6 + 6 + 7 + 5 + 4 + 3 = 31
        # To get calm_ratio ~ 0.898, total obs ~ 304, calm obs ~ 273
        for _ in range(273):
            observations.append({"value": 30.0, "wind_speed": 0.2, "wind_direction": 180.0})

        rose = calculate_cpf_rose(observations, threshold_p75=tau, calm_threshold=0.5)

        # Assert calm ratio
        assert 0.89 <= rose["calm_ratio"] <= 0.91

        # Assert Sector 9: 2/6 = 0.3333
        assert rose["sectors"][9] is not None
        assert abs(rose["sectors"][9] - 0.3333) < 0.005

        # Assert Sector 10: 1/6 = 0.1667
        assert rose["sectors"][10] is not None
        assert abs(rose["sectors"][10] - 0.1667) < 0.005

        # Assert Sector 12: 0/7 = 0.0
        assert rose["sectors"][12] == 0.0

        # Assert Sector 13: Suppressed (None)
        assert rose["sectors"][13] is None

        # Assert Sectors 4 and 5: Suppressed (None)
        assert rose["sectors"][4] is None
        assert rose["sectors"][5] is None

    def test_cpf_empty_observations(self):
        """Empty observation series returns 16 None sectors."""
        res = calculate_cpf_rose([])
        assert len(res["sectors"]) == 16
        assert all(s is None for s in res["sectors"])
        assert res["calm_ratio"] == 0.0


class TestAdvectionFluxTransformations:
    """Tests Physical Advection Flux (T6) and Receptor Coupling (T7)."""

    def test_advection_flux_reference_fixture(self):
        """
        Spec Miner Fixture §4.3:
        Source: C_a = 250.0 ug/m3, w_a = 4.0 m/s
        Trajectory: d_ab = 50.0 km, bearing = 90.0 deg (East)
        Wind Direction TO: 105.0 deg -> divergence = 15.0 deg
        cos(15 deg) = 0.965926
        exp(-50 / 100) = 0.606531
        Expected flux = 250.0 * 4.0 * 0.965926 * 0.606531 = 585.864 ug/(m^2*s)
        """
        # Source at (31.500, 74.000)
        # Receptor at same latitude, east longitude to achieve 90 deg bearing and 50 km dist
        # Wind: theta_to = 105 deg, speed = 4.0 m/s
        # u = 4.0 * sin(105 deg), v = 4.0 * cos(105 deg)
        rad105 = math.radians(105.0)
        u_wind = 4.0 * math.sin(rad105)
        v_wind = 4.0 * math.cos(rad105)

        # Using direct formula parameters:
        # Source (31.5, 74.0), Receptor 50km East
        # In Pakistan (lat ~31.5 deg), 1 deg lon is ~95 km, so 50km is ~0.526 deg lon
        r_lon = 74.0 + (50.0 / (R_EARTH_KM * math.cos(math.radians(31.5)) * (math.pi / 180.0)))
        src_coords = (31.5, 74.0)
        rcv_coords = (31.5, r_lon)

        res = calculate_advection_flux(
            source_station=src_coords,
            receptor_coords=rcv_coords,
            pollutant="PM2.5",
            concentration=250.0,
            u_wind=u_wind,
            v_wind=v_wind,
            residence_km=100.0,
        )

        assert res is not None
        # Verify distance is ~50 km and flux is ~585.864
        assert abs(res["distance_km"] - 50.0) < 0.5
        assert abs(res["flux"] - 585.864) < 1.0, f"Expected ~585.864, got {res['flux']}"

    def test_advection_flux_physical_dimension_guard_for_aqi(self):
        """
        CRITICAL MANDATORY REQUIREMENT:
        Advection flux MUST be disabled for dimensionless ordinal index 'AQI'.
        Must return None.
        """
        src = (31.5, 74.0)
        rcv = (31.5, 74.5)
        # Valid physical parameters, but pollutant is AQI
        res = calculate_advection_flux(
            source_station=src,
            receptor_coords=rcv,
            pollutant="AQI",
            concentration=200.0,
            u_wind=5.0,
            v_wind=0.0,
        )
        assert res is None, "Physical advection flux must be strictly disabled for AQI!"

        # Also case-insensitive checks
        assert calculate_advection_flux(src, rcv, "aqi", 200.0, 5.0, 0.0) is None
        assert calculate_advection_flux(src, rcv, " Aqi ", 200.0, 5.0, 0.0) is None

    def test_advection_flux_cone_and_distance_limits(self):
        """Enforces 35 deg cone limit, 180 km distance limit, and calm wind cutoff."""
        src = (31.5, 74.0)
        rcv = (31.5, 74.5)

        # 1. Divergence > 35 deg -> None
        # Wind blowing West (theta_to = 270 deg) while receptor is East (90 deg) -> div = 180 deg
        res_div = calculate_advection_flux(src, rcv, "PM2.5", 100.0, -5.0, 0.0)
        assert res_div is None

        # 2. Distance > 180 km -> None
        # Lahore to Rawalpindi is ~268 km
        res_dist = calculate_advection_flux((31.5, 74.3), (33.6, 73.0), "PM2.5", 100.0, 5.0, 5.0)
        assert res_dist is None

        # 3. Calm wind (<0.5 m/s) -> None
        res_calm = calculate_advection_flux(src, rcv, "PM2.5", 100.0, 0.2, 0.2)
        assert res_calm is None

    def test_receptor_coupling_and_top_60_truncation(self):
        """T7: Top 60 pathway ranking with receptor CPF coupling feedback."""
        flux_series = []
        for i in range(100):
            flux_series.append({
                "source_district": f"District_{i}",
                "receptor_district": "Lahore",
                "mean_flux": float(i + 1),
                "bearing_deg": 90.0,
                "distance_km": 50.0,
            })

        receptor_cpfs = {
            "Lahore": {"sectors": [0.35] * 16}
        }

        ranked = calculate_receptor_coupling(flux_series, receptor_cpfs, max_links=60)
        # Must be strictly truncated to 60 links
        assert len(ranked) == 60
        # Highest score should be first (i=99: 100 * 0.35 = 35.0)
        assert ranked[0]["score"] == 35.0
        assert ranked[0]["source_district"] == "District_99"

    def test_net_transport_balance_export_import(self):
        """T7: Net export/import balance summation."""
        links = [
            {"source_district": "Lahore", "receptor_district": "Kasur", "score": 20.0},
            {"source_district": "Sheikhupura", "receptor_district": "Lahore", "score": 15.0},
        ]
        bal = calculate_net_transport_balance(links)
        # Lahore: +20 (out) - 15 (in) = +5.0 (net exporter)
        assert bal["Lahore"] == 5.0
        # Kasur: -20.0 (net importer)
        assert bal["Kasur"] == -20.0
        # Sheikhupura: +15.0 (net exporter)
        assert bal["Sheikhupura"] == 15.0


class TestTransboundaryTransformations:
    """Tests Transboundary Cross-Border Index (T8)."""

    def test_border_district_inflow_outflow(self):
        """Within 120km, Indian wind sector yields inflow; opposite yields outflow."""
        # Kasur is ~15 km from border; India sectors are typically [4, 5, 6, 7] (Easterly/South-Easterly)
        india_sectors = [4, 5, 6, 7]

        # Wind from Sector 4 (East, 90 deg -> u=-5, v=0) -> Inflow (+)
        inflow = calculate_district_transboundary_flux(
            border_distance_km=15.0,
            india_sectors=india_sectors,
            concentration=100.0,
            u_wind=-5.0,
            v_wind=0.0,
        )
        assert inflow > 0.0

        # Wind from Sector 12 (West, 270 deg -> (4 + 8) % 16 = 12) -> Outflow (-)
        outflow = calculate_district_transboundary_flux(
            border_distance_km=15.0,
            india_sectors=india_sectors,
            concentration=100.0,
            u_wind=5.0,
            v_wind=0.0,
        )
        assert outflow < 0.0
        assert abs(inflow - abs(outflow)) < 1e-4

        # Wind from Sector 0 (North, parallel) -> 0.0
        parallel = calculate_district_transboundary_flux(
            border_distance_km=15.0,
            india_sectors=india_sectors,
            concentration=100.0,
            u_wind=0.0,
            v_wind=-5.0,
        )
        assert parallel == 0.0

    def test_transboundary_corridor_limit_120km(self):
        """Districts beyond 120km from border return 0.0."""
        flux = calculate_district_transboundary_flux(
            border_distance_km=125.0,
            india_sectors=[4],
            concentration=200.0,
            u_wind=-5.0,
            v_wind=0.0,
        )
        assert flux == 0.0


class TestEquirectangularProjectionAndLabelPlacement:
    """Tests Plate Carree projection (31 deg N) and greedy label placement (T11)."""

    def test_equirectangular_projection_roundtrip(self):
        """Forward and inverse projection roundtrip preserves coordinates."""
        test_coords = [
            (31.549, 74.364),  # Lahore
            (30.157, 71.524),  # Multan
            (33.565, 73.016),  # Rawalpindi
        ]
        for lat, lon in test_coords:
            x, y = equirectangular_project(lat, lon, width_px=1200.0, height_px=900.0)
            rec_lat, rec_lon = equirectangular_unproject(x, y, width_px=1200.0, height_px=900.0)
            assert abs(rec_lat - lat) < 1e-4
            assert abs(rec_lon - lon) < 1e-4

    def test_greedy_label_placement_collision_resolution(self):
        """Greedy label placement resolves overlapping labels and flags leader lines."""
        labels = [
            {"id": "LHR1", "text": "Lahore Main", "x": 500.0, "y": 400.0, "w": 60.0, "h": 20.0},
            {"id": "LHR2", "text": "Lahore Sub", "x": 505.0, "y": 402.0, "w": 60.0, "h": 20.0},
        ]
        placed = greedy_label_placement(labels)
        assert len(placed) == 2
        # First label placed at [0, 0] offset
        assert placed[0]["offset_x"] == 0.0 and placed[0]["offset_y"] == 0.0
        # Second label must be displaced to resolve collision
        assert placed[1]["offset_x"] != 0.0 or placed[1]["offset_y"] != 0.0
        # No overlapping bounding boxes
        box1 = placed[0]["bounding_box"]
        box2 = placed[1]["bounding_box"]
        assert not check_aabb_collision(box1, box2)
