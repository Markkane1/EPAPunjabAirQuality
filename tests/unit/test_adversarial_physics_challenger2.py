"""
Empirical Adversarial Physics and Mathematical Invariant Stress-Test Suite.
Challenger 2 Verification Gate.
Covers:
1. Station 172 Blacklist Stress-Test (Python)
2. T1 Singularity Clamp (d = 0)
3. T6 Physical Dimension Guard (pollutant = 'AQI')
4. T9 Scale Boundaries (PM2.5 @ 350.0, 350.1, 500.0, 5000.0)
5. T10 Temporal QC (3h hold at indices 0, 1, 2 and AQI exemption)
"""
import math
import pytest

from src.domain.math.wind import (
    is_station_blacklisted,
    is_anemometer_valid,
    polar_to_cartesian_wind,
    blend_winds,
)
from src.domain.normalizer.normalizer import (
    is_blacklisted_station,
    blacklist_banner_text,
    normalize_wind,
)
from src.domain.math.geodesy import haversine_distance
from src.domain.math.idw import (
    discrete_geodesic_idw,
    discrete_geodesic_idw_vector,
)
from src.domain.math.flux import calculate_advection_flux
from src.domain.math.pepc_aqi import (
    pepc_calculate_aqi,
    pepc_composite_aqi,
)
from src.domain.math.qc import temporal_qc_clean


class TestStation172BlacklistPython:
    @pytest.mark.parametrize(
        "station_id",
        [
            172,
            "172",
            " 172 ",
            "wazirabad",
            "WAZIRABAD",
            "Wazirabad",
            "Wazirabad AQMS",
            "WAZIRABAD AQMS",
            "pk_waz_001",
            "PK_WAZ_001",
            "Pk_Waz_001",
            "wazirabad station",
            "WAZIRABAD STATION",
        ],
    )
    def test_station_172_blacklisted_queries(self, station_id):
        # 1. is_station_blacklisted
        assert is_station_blacklisted(station_id) is True, f"Failed for {station_id}"
        assert is_blacklisted_station(station_id) is True, f"Failed normalizer for {station_id}"

        # 2. is_anemometer_valid
        assert is_anemometer_valid(5.0, 180.0, station_name=station_id) is False

        # 3. polar_to_cartesian_wind returns None
        assert polar_to_cartesian_wind(5.0, 180.0, station_name=station_id) is None

        # 4. normalize_wind returns blacklisted state
        norm = normalize_wind(5.0, 180.0, station_id_or_name=station_id)
        assert norm["state"] == "blacklisted"
        assert norm["blacklisted"] is True
        assert norm["speed"] is None
        assert norm["direction"] is None
        assert norm["u"] is None
        assert norm["v"] is None
        assert "BLACKLISTED" in norm["blacklist_reason"]

        # 5. blacklist_banner_text
        banner = blacklist_banner_text(station_id)
        assert banner == "ANEMOMETER BLACKLISTED (VANE OFFSET)"
        banner_dict = blacklist_banner_text({"id": station_id, "name": "Some station"})
        assert banner_dict == "ANEMOMETER BLACKLISTED (VANE OFFSET)"

    def test_station_172_wind_blending_exclusion(self):
        # When blending winds, station 172 must be excluded and never corrupt wind field
        target = (32.0, 74.0)
        # Station 172 has extreme wind (25 m/s, 90 deg)
        # Clean station has (5 m/s, 180 deg)
        sources = [
            {"station_name": 172, "speed": 25.0, "direction": 90.0, "coords": (32.0, 74.0)},
            {"station_name": "clean_station", "speed": 5.0, "direction": 180.0, "coords": (32.0, 74.0)},
        ]
        result = blend_winds(target, sources)
        assert result is not None
        u, v = result
        # Clean station at (5 m/s, 180 deg): theta=180 deg, u = -5*sin(180)=0, v = -5*cos(180)=5.0
        # If 172 were blended, u would be ~ -25.0!
        assert abs(u) < 1e-6, f"Station 172 was not excluded from wind blending! u={u}"
        assert abs(v - 5.0) < 1e-4, f"Blended v={v} should be 5.0"


class TestT1SingularityClampPython:
    def test_haversine_identical_coords(self):
        d = haversine_distance(31.5204, 74.3587, 31.5204, 74.3587)
        assert d == 0.0

    def test_discrete_idw_zero_distance_clamped(self):
        # Target exactly coincides with reporting monitor
        target = (31.5204, 74.3587)
        stations = [{"coords": (31.5204, 74.3587), "value": 142.5}]
        # Distance is clamped to d0 = 5.0 km -> weight = 1 / (5^2) = 0.04
        # Value should return exactly 142.5 without ZeroDivisionError or NaN
        val = discrete_geodesic_idw(target, stations, power=2.0, d0=5.0)
        assert val is not None
        assert not math.isnan(val)
        assert not math.isinf(val)
        assert abs(val - 142.5) < 1e-6

    def test_discrete_idw_two_stations_one_coincident(self):
        target = (31.5204, 74.3587)
        # Station 1 at d=0 (clamped to 5.0 km, weight = 1/25 = 0.04), value = 100.0
        # Station 2 at ~5.0 km (weight = 1/25 = 0.04), value = 200.0
        # To place station 2 at exactly ~5.0 km north: 5.0 / 111.0 = ~0.045045 degrees lat
        st2_lat = 31.5204 + (5.0 / 111.195)
        d2 = haversine_distance(target[0], target[1], st2_lat, target[1])
        assert abs(d2 - 5.0) < 0.05

        stations = [
            {"coords": (31.5204, 74.3587), "value": 100.0},
            {"coords": (st2_lat, 74.3587), "value": 200.0},
        ]
        val = discrete_geodesic_idw(target, stations, power=2.0, d0=5.0)
        assert val is not None
        # Both stations should have almost equal weights of 0.04, yielding ~150.0
        assert 145.0 < val < 155.0

    def test_discrete_idw_vector_zero_distance_clamped(self):
        target = (31.5204, 74.3587)
        stations = [{"coords": (31.5204, 74.3587), "u": 2.5, "v": -3.5}]
        vec = discrete_geodesic_idw_vector(target, stations, power=2.0, d0=5.0)
        assert vec is not None
        u, v = vec
        assert abs(u - 2.5) < 1e-6
        assert abs(v - (-3.5)) < 1e-6


class TestT6PhysicalDimensionGuardPython:
    @pytest.mark.parametrize("pollutant", ["AQI", "aqi", " AQI ", "Aqi", "aQi"])
    def test_flux_strictly_disabled_for_aqi(self, pollutant):
        # Advection flux must return None for AQI
        source = (31.5204, 74.3587)
        receptor = (31.9000, 74.3587)  # Directly North (~42 km)
        # Wind blowing directly North: theta_to = 0 deg, u = 0, v = 5.0
        result = calculate_advection_flux(
            source_station=source,
            receptor_coords=receptor,
            pollutant=pollutant,
            concentration=150.0,
            u_wind=0.0,
            v_wind=5.0,
        )
        assert result is None, f"Advection flux must be None for {pollutant}"

    def test_flux_active_for_physical_species(self):
        source = (31.5204, 74.3587)
        receptor = (31.9000, 74.3587)  # North
        for p in ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]:
            result = calculate_advection_flux(
                source_station=source,
                receptor_coords=receptor,
                pollutant=p,
                concentration=100.0,
                u_wind=0.0,
                v_wind=5.0,
            )
            assert result is not None, f"Failed for physical species {p}"
            assert result["flux"] > 0.0
            assert result["divergence_deg"] < 35.0


class TestT9ScaleBoundariesPython:
    def test_pm25_boundary_and_ceiling(self):
        # Test PM2.5 concentrations at 350.0, 350.1, 500.0, 5000.0
        # 350.0 is the exact statutory ceiling breakpoint for category 5 -> AQI 400 (Very Unhealthy)
        assert pepc_calculate_aqi("PM2.5", 350.0) == 400
        # 350.1 exceeds statutory top breakpoint (350.0) -> strictly clamped to 500 (Hazardous)
        assert pepc_calculate_aqi("PM2.5", 350.1) == 500
        # 500.0 -> strictly clamped to 500
        assert pepc_calculate_aqi("PM2.5", 500.0) == 500
        # 5000.0 -> strictly clamped to 500
        assert pepc_calculate_aqi("PM2.5", 5000.0) == 500

    def test_pm25_continuous_half_open_intervals(self):
        # Test continuous breakpoints
        # (0, 15] -> (0, 50]
        assert pepc_calculate_aqi("PM2.5", 0.0) == 0
        assert pepc_calculate_aqi("PM2.5", 15.0) == 50
        # (15, 35] -> (50, 100]
        assert pepc_calculate_aqi("PM2.5", 15.0001) == 50
        assert pepc_calculate_aqi("PM2.5", 25.0) == 75
        assert pepc_calculate_aqi("PM2.5", 35.0) == 100
        # (35, 70] -> (100, 150]
        assert pepc_calculate_aqi("PM2.5", 35.0001) == 100
        assert pepc_calculate_aqi("PM2.5", 70.0) == 150
        # (70, 140] -> (150, 200]
        assert pepc_calculate_aqi("PM2.5", 70.0001) == 150
        assert pepc_calculate_aqi("PM2.5", 140.0) == 200
        # (140, 250] -> (200, 300]
        assert pepc_calculate_aqi("PM2.5", 140.0001) == 200
        assert pepc_calculate_aqi("PM2.5", 250.0) == 300
        # (250, 350] -> (300, 400]
        assert pepc_calculate_aqi("PM2.5", 250.0001) == 300
        assert pepc_calculate_aqi("PM2.5", 300.0) == 350
        assert pepc_calculate_aqi("PM2.5", 350.0) == 400

    def test_pm10_ceiling(self):
        assert pepc_calculate_aqi("PM10", 550.0) == 400
        assert pepc_calculate_aqi("PM10", 550.1) == 500
        assert pepc_calculate_aqi("PM10", 1000.0) == 500

    def test_composite_aqi(self):
        assert pepc_composite_aqi(300, 200) == 300
        assert pepc_composite_aqi(150, 400) == 400
        assert pepc_composite_aqi(500, 500) == 500
        assert pepc_composite_aqi(None, 200) == 200
        assert pepc_composite_aqi(300, None) == 300
        assert pepc_composite_aqi(None, None) is None


class TestT10TemporalQCPython:
    def test_hold_filter_indices_0_1_2(self):
        # Duplicate values across initial indices: [80.0, 80.0, 80.0, 80.0, 90.0]
        # For PM2.5 (physical pollutant):
        # i=0: 80.0 (kept)
        # i=1: 80.0 (kept)
        # i=2: suppressed to None (hold detected)
        # i=3: suppressed to None (pre-hold was 80.0)
        # i=4: 90.0 (kept)
        raw = [80.0, 80.0, 80.0, 80.0, 90.0]
        cleaned, spikes = temporal_qc_clean(raw, ref_limit=35.0, pollutant="PM2.5")
        assert cleaned[0] == 80.0
        assert cleaned[1] == 80.0
        assert cleaned[2] is None
        assert cleaned[3] is None
        assert cleaned[4] == 90.0

    def test_aqi_exempt_from_hold_filter(self):
        # For AQI, duplicate values across hours are genuinely possible and MUST NOT be suppressed
        raw_aqi = [150.0, 150.0, 150.0, 150.0, 150.0]
        cleaned, spikes = temporal_qc_clean(raw_aqi, ref_limit=35.0, pollutant="AQI")
        assert cleaned == [150.0, 150.0, 150.0, 150.0, 150.0]
        # Also test lower case "aqi"
        cleaned_lower, _ = temporal_qc_clean(raw_aqi, ref_limit=35.0, pollutant="aqi")
        assert cleaned_lower == [150.0, 150.0, 150.0, 150.0, 150.0]

    def test_hold_filter_short_series_no_wraparound(self):
        # Array with length 2: must not crash or trigger negative indexing
        raw = [50.0, 50.0]
        cleaned, _ = temporal_qc_clean(raw, ref_limit=35.0, pollutant="PM2.5")
        assert cleaned == [50.0, 50.0]

        # Array with length 1
        raw1 = [50.0]
        cleaned1, _ = temporal_qc_clean(raw1, ref_limit=35.0, pollutant="PM2.5")
        assert cleaned1 == [50.0]
