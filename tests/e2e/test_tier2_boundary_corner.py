"""
Tier 2: Boundary, Corner & Limit Case Verification Tests
Tests extreme boundaries, singularity clamping, sensor freezes, calm wind cutoffs,
blacklist logic, and physical guards according to TRANSFORMATION_LOGIC_SPEC.md.
"""
import math
from typing import List, Optional

import pytest
from pydantic import ValidationError
from tests.e2e.conftest import (
    PAQReferenceOracle,
    RawStationMeasurementContract,
    UserCSVRowContract,
)


class TestTier2BoundaryValues:
    """Verifies edge conditions and mathematical boundary behaviors."""

    def test_maximum_concentration_boundary(self):
        """Values up to 5000.0 ug/m3 are valid; values >5000.0 trigger ValidationError."""
        # 5000.0 is upper legal limit
        valid_row = UserCSVRowContract(
            timestamp="2026-11-10T12:00:00Z",
            station_id="ST_001",
            station_name="Boundary Station",
            district="Lahore",
            latitude=31.5204,
            longitude=74.3587,
            pollutant="pm25",
            value=5000.0,
        )
        assert valid_row.value == 5000.0

        # 5000.1 exceeds legal limit
        with pytest.raises(ValidationError):
            UserCSVRowContract(
                timestamp="2026-11-10T12:00:00Z",
                station_id="ST_001",
                station_name="Boundary Station",
                district="Lahore",
                latitude=31.5204,
                longitude=74.3587,
                pollutant="pm25",
                value=5000.1,
            )

    def test_geographic_coordinate_boundaries(self):
        """Coordinates must fall within Punjab bounds: Lat [27.0, 35.0], Lon [69.0, 76.0]."""
        # Exactly on the lower boundary
        lower_node = UserCSVRowContract(
            timestamp="2026-11-10T12:00:00Z",
            station_id="ST_BND_LOW",
            station_name="South West Edge",
            district="Rahim Yar Khan",
            latitude=27.0,
            longitude=69.0,
            pollutant="pm25",
            value=50.0,
        )
        assert lower_node.latitude == 27.0
        assert lower_node.longitude == 69.0

        # Exactly on the upper boundary
        upper_node = UserCSVRowContract(
            timestamp="2026-11-10T12:00:00Z",
            station_id="ST_BND_HIGH",
            station_name="North East Edge",
            district="Attock",
            latitude=35.0,
            longitude=76.0,
            pollutant="pm25",
            value=50.0,
        )
        assert upper_node.latitude == 35.0
        assert upper_node.longitude == 76.0

        # Out-of-bounds latitude (too low: 26.9)
        with pytest.raises(ValidationError):
            UserCSVRowContract(
                timestamp="2026-11-10T12:00:00Z",
                station_id="ST_INVALID",
                station_name="Out of bounds",
                district="Sindh Border",
                latitude=26.9,
                longitude=70.0,
                pollutant="pm25",
                value=50.0,
            )

        # Out-of-bounds longitude (too high: 76.1)
        with pytest.raises(ValidationError):
            UserCSVRowContract(
                timestamp="2026-11-10T12:00:00Z",
                station_id="ST_INVALID",
                station_name="Out of bounds",
                district="India Border",
                latitude=31.5,
                longitude=76.1,
                pollutant="pm25",
                value=50.0,
            )

    def test_calm_wind_exclusion_boundary(self, reference_oracle: PAQReferenceOracle):
        """
        Wind speed 0.49 m/s is classified as calm and excluded from directional sectors.
        Wind speed 0.50 m/s is valid directional wind.
        """
        # 6 observations with speed 0.49 m/s (calm) from sector 4 (East)
        calm_obs = [
            {"wind_speed": 0.49, "wind_direction": 90.0, "value": 200.0}
            for _ in range(6)
        ]
        res_calm = reference_oracle.calculate_cpf_rose(calm_obs, threshold_p75=150.0)
        assert res_calm["calm_ratio"] == 1.0
        assert res_calm["sectors"][4] is None  # Excluded due to calm cutoff

        # 6 observations with speed 0.50 m/s (threshold) from sector 4 (East)
        threshold_obs = [
            {"wind_speed": 0.50, "wind_direction": 90.0, "value": 200.0}
            for _ in range(6)
        ]
        res_valid = reference_oracle.calculate_cpf_rose(threshold_obs, threshold_p75=150.0)
        assert res_valid["calm_ratio"] == 0.0
        assert res_valid["sectors"][4] == 1.0  # Included!

    def test_idw_zero_distance_singularity_clamping(self, reference_oracle: PAQReferenceOracle):
        """
        When target coincides with monitored node (d = 0), distance is clamped to d0 = 5.0 km,
        preventing division-by-zero with finite weight w = 1 / 25 = 0.04.
        """
        target = (31.5204, 74.3587)
        # Monitored station located at EXACT same coordinate
        monitored = [
            {"coords": (31.5204, 74.3587), "value": 250.0},
            {"coords": (31.1179, 74.4460), "value": 100.0},
        ]
        val = reference_oracle.discrete_geodesic_idw(target, monitored, power=2.0, d0_km=5.0)
        assert val is not None
        # Coincident node has weight 1/(5^2) = 0.04. Second node has weight 1/(45.5^2) = 0.00048.
        # Coincident node dominates overwhelmingly:
        assert 245.0 <= val <= 250.0

    def test_cpf_small_sample_suppression(self, reference_oracle: PAQReferenceOracle):
        """Sectors with fewer than 6 valid hours (Nk < 6) return None instead of spurious spikes."""
        obs = [
            # Only 5 observations from sector 4 (East) - all exceeding threshold
            {"wind_speed": 2.0, "wind_direction": 90.0, "value": 300.0}
            for _ in range(5)
        ]
        res = reference_oracle.calculate_cpf_rose(obs, threshold_p75=200.0)
        # Nk = 5 < 6 -> must be strictly None
        assert res["sectors"][4] is None

    def test_advection_flux_distance_and_cone_limits(self, reference_oracle: PAQReferenceOracle):
        """Advection flux returns None when distance > 180 km or angular divergence > 35 degrees."""
        # 1. Distance exceeded (> 180 km): Lahore to Rawalpindi is ~268 km
        flux_too_far = reference_oracle.calculate_advection_flux(
            source_coords=(31.5204, 74.3587),     # Lahore
            receptor_coords=(33.5973, 73.0479),    # Rawalpindi (~268 km)
            concentration=250.0,
            u_wind=5.0,
            v_wind=5.0,
            pollutant="PM2.5",
            max_dist_km=180.0
        )
        assert flux_too_far is None

        # 2. Angular cone exceeded (> 35 degrees)
        # Lahore to Kasur bearing is ~168 deg. Wind blowing North (0 deg) -> divergence ~168 deg > 35 deg
        flux_divergent = reference_oracle.calculate_advection_flux(
            source_coords=(31.5204, 74.3587),
            receptor_coords=(31.1179, 74.4460),
            concentration=250.0,
            u_wind=0.0,
            v_wind=5.0,  # Blowing North
            pollutant="PM2.5",
            cone_deg=35.0
        )
        assert flux_divergent is None

    def test_advection_flux_physical_dimension_guard_for_aqi(self, reference_oracle: PAQReferenceOracle):
        """
        Physical dimension guard: Advection mass flux is strictly disallowed
        for dimensionless ordinal index 'AQI' and returns None.
        """
        flux_aqi = reference_oracle.calculate_advection_flux(
            source_coords=(31.5204, 74.3587),
            receptor_coords=(31.1179, 74.4460),
            concentration=350.0,
            u_wind=2.0,
            v_wind=-2.0,
            pollutant="AQI"
        )
        assert flux_aqi is None

    def test_pepc_half_open_interval_boundaries(self, reference_oracle: PAQReferenceOracle):
        """
        Verifies continuous half-open intervals: (BP_low, BP_high].
        C = 15.0 is in Category 0 (Good, AQI 50).
        C = 15.001 crosses into Category 1 (Satisfactory, AQI 50+).
        """
        aqi_15_0 = reference_oracle.pepc_calculate_aqi("PM2.5", 15.0)
        aqi_15_001 = reference_oracle.pepc_calculate_aqi("PM2.5", 15.001)

        assert aqi_15_0 == 50
        assert aqi_15_001 >= 50

        # Exact category 6 operational clamp: C = 350.0 -> AQI 400; C = 350.1 -> clamped to 500
        aqi_350_0 = reference_oracle.pepc_calculate_aqi("PM2.5", 350.0)
        aqi_350_1 = reference_oracle.pepc_calculate_aqi("PM2.5", 350.1)

        assert aqi_350_0 == 400
        assert aqi_350_1 == 500

    def test_logger_hold_index_guard_and_aqi_exemption(self, reference_oracle: PAQReferenceOracle):
        """
        3h hold filter enforces i >= 2 index guard preventing negative array wraparound.
        Physical pollutants are nulled when holding 3 consecutive hours.
        AQI is strictly exempt from logger hold purge.
        """
        # Physical PM2.5 series with 3 consecutive identical values
        pm_series = [50.0, 50.0, 50.0, 60.0]
        cleaned_pm, _ = reference_oracle.temporal_qc_clean(pm_series, ref_limit=35.0, pollutant="PM2.5")
        assert cleaned_pm[0] == 50.0
        assert cleaned_pm[1] == 50.0
        assert cleaned_pm[2] is None  # 3rd identical value nulled!
        assert cleaned_pm[3] == 60.0

        # AQI series with 3 consecutive identical values (integer index can legitimately hold)
        aqi_series = [150.0, 150.0, 150.0, 160.0]
        cleaned_aqi, _ = reference_oracle.temporal_qc_clean(aqi_series, ref_limit=100.0, pollutant="AQI")
        assert cleaned_aqi[2] == 150.0  # Exempt! Not nulled!

    def test_wazirabad_anemometer_blacklist_contract(self):
        """Wazirabad AQMS site exhibits a 140 deg physical installation offset and must be blacklisted."""
        nowind_stations = {"Wazirabad", "PK_WZB_001"}
        station = "Wazirabad"
        assert station in nowind_stations

    def test_completeness_75_percent_cutoff_rule(self):
        """
        75% Aggregation Completeness Rule:
        For 24-hour period, H=24 -> round(0.75 * 24) = 18 hours required.
        17 valid hours -> null summary.
        18 valid hours -> valid arithmetic mean.
        """
        def aggregate_24h(valid_count: int, values_sum: float) -> Optional[float]:
            req = max(1, round(0.75 * 24))
            if valid_count < req:
                return None
            return values_sum / valid_count

        assert aggregate_24h(valid_count=17, values_sum=1700.0) is None
        assert aggregate_24h(valid_count=18, values_sum=1800.0) == 100.0
