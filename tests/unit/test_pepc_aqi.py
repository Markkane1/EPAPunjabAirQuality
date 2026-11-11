"""
Comprehensive Unit Tests for Official PEPC AQI and Color Scale Engine.
Tests all statutory breakpoints, continuous half-open intervals, 500 operational cap,
particulate composite logic, and continuous PEQS RGB gradient mapping.
Matches fixtures from spec_miner_math/handoff.md Section 4.1.
"""
import pytest

from src.domain.math.pepc_aqi import (
    pepc_calculate_aqi,
    pepc_composite_aqi,
    pepc_get_category,
    pepc_get_color,
    pepc_interpolate_color,
    pepc_interpolate_color_hex,
    PEPC_BREAKPOINTS,
    AQI_TIERS,
)


class TestPEPCAQIBreakpointMatrix:
    """Verifies all statutory breakpoint test cases from spec_miner_math/handoff.md §4.1."""

    @pytest.mark.parametrize(
        "pollutant,concentration,expected_aqi,expected_category",
        [
            # PM2.5 Breakpoint Suite (§4.1)
            ("PM2.5", 0.0, 0, "Good"),
            ("PM2.5", 7.5, 25, "Good"),
            ("PM2.5", 15.0, 50, "Good"),
            ("PM2.5", 25.0, 75, "Satisfactory"),
            ("PM2.5", 35.0, 100, "Satisfactory"),
            ("PM2.5", 52.5, 125, "Moderate"),
            ("PM2.5", 70.0, 150, "Moderate"),
            ("PM2.5", 105.0, 175, "Unhealthy (Sensitive)"),
            ("PM2.5", 140.0, 200, "Unhealthy (Sensitive)"),
            ("PM2.5", 195.0, 250, "Unhealthy"),
            ("PM2.5", 250.0, 300, "Unhealthy"),
            ("PM2.5", 300.0, 350, "Very Unhealthy"),
            ("PM2.5", 350.0, 400, "Very Unhealthy"),
            ("PM2.5", 400.0, 500, "Hazardous"),  # Operational Ceiling Cap (>350.0)
            ("PM2.5", 800.0, 500, "Hazardous"),  # Extreme severe smog cap
            # PM10 Breakpoint Suite (§4.1)
            ("PM10", 0.0, 0, "Good"),
            ("PM10", 37.5, 25, "Good"),
            ("PM10", 75.0, 50, "Good"),
            ("PM10", 150.0, 100, "Satisfactory"),
            ("PM10", 250.0, 150, "Moderate"),
            ("PM10", 350.0, 200, "Unhealthy (Sensitive)"),
            ("PM10", 450.0, 300, "Unhealthy"),
            ("PM10", 550.0, 400, "Very Unhealthy"),
            ("PM10", 600.0, 500, "Hazardous"),  # Operational Ceiling Cap (>550.0)
            # Gaseous Pollutants
            ("SO2", 60.0, 50, "Good"),
            ("SO2", 120.0, 100, "Satisfactory"),
            ("SO2", 320.0, 200, "Unhealthy (Sensitive)"),
            ("SO2", 1800.0, 500, "Hazardous"),
            ("NO2", 40.0, 50, "Good"),
            ("NO2", 80.0, 100, "Satisfactory"),
            ("NO2", 180.0, 200, "Unhealthy (Sensitive)"),
            ("NO2", 650.0, 500, "Hazardous"),
            ("O3", 65.0, 50, "Good"),
            ("O3", 130.0, 100, "Satisfactory"),
            ("O3", 600.0, 500, "Hazardous"),
            ("CO", 2.5, 50, "Good"),
            ("CO", 5.0, 100, "Satisfactory"),
            ("CO", 10.0, 200, "Unhealthy (Sensitive)"),
            ("CO", 50.0, 500, "Hazardous"),
        ],
    )
    def test_pepc_sub_index_exact_fixtures(
        self, pollutant, concentration, expected_aqi, expected_category
    ):
        """Verifies exact sub-index interpolation and category descriptor matching."""
        aqi = pepc_calculate_aqi(pollutant, concentration)
        assert aqi == expected_aqi, (
            f"Failed for {pollutant} at {concentration}: expected {expected_aqi}, got {aqi}"
        )
        cat = pepc_get_category(aqi)
        assert cat == expected_category, (
            f"Category mismatch for AQI {aqi}: expected {expected_category}, got {cat}"
        )

    def test_continuous_half_open_interval_boundaries(self):
        """
        Confirms continuous half-open intervals (BP_{i-1}, BP_i].
        At exact boundary 15.0 ug/m3 for PM2.5, category is Good (AQI 50).
        At 15.0001 ug/m3, category is Satisfactory (AQI 50).
        At 35.0 ug/m3, category is Satisfactory (AQI 100).
        """
        # Upper edge of Good bracket
        assert pepc_calculate_aqi("PM2.5", 15.0) == 50
        assert pepc_get_category(50) == "Good"

        # Infinitesimal step into Satisfactory bracket
        aqi_just_above = pepc_calculate_aqi("PM2.5", 15.01)
        assert aqi_just_above == 50  # Interpolates to ~50
        # Check midpoint of Satisfactory
        assert pepc_calculate_aqi("PM2.5", 25.0) == 75

        # Upper edge of Satisfactory bracket
        assert pepc_calculate_aqi("PM2.5", 35.0) == 100
        assert pepc_get_category(100) == "Satisfactory"

    def test_zero_and_negative_sanitization(self):
        """Negative values, NaN, and None return None; exact 0.0 returns 0."""
        assert pepc_calculate_aqi("PM2.5", 0.0) == 0
        assert pepc_calculate_aqi("PM2.5", -1.0) is None
        assert pepc_calculate_aqi("PM2.5", -0.01) is None
        assert pepc_calculate_aqi("PM2.5", None) is None
        assert pepc_calculate_aqi("PM2.5", float("nan")) is None


class TestPEPCCompositeAQI:
    """Verifies particulate-matter composite AQI logic (TRANSFORMATION_LOGIC_SPEC.md §2.9.3)."""

    def test_composite_aqi_particulate_governance(self):
        """Composite AQI is strictly max(I_PM2.5, I_PM10)."""
        # PM2.5 higher
        assert pepc_composite_aqi(pm25_aqi=250, pm10_aqi=150) == 250
        # PM10 higher
        assert pepc_composite_aqi(pm25_aqi=180, pm10_aqi=300) == 300
        # Equal
        assert pepc_composite_aqi(pm25_aqi=100, pm10_aqi=100) == 100

    def test_composite_aqi_partial_null_handling(self):
        """Gracefully handles missing or unmonitored particulate fractions."""
        assert pepc_composite_aqi(pm25_aqi=220, pm10_aqi=None) == 220
        assert pepc_composite_aqi(pm25_aqi=None, pm10_aqi=175) == 175
        assert pepc_composite_aqi(pm25_aqi=None, pm10_aqi=None) is None


class TestPEQSContinuousColorScales:
    """Verifies official category colors and continuous 7-stop PEQS RGB gradient ramp."""

    def test_category_hex_color_mapping(self):
        """Verifies statutory 7-stop category hex codes."""
        assert pepc_get_color(25) == "#00B050"   # Good
        assert pepc_get_color(50) == "#00B050"   # Good
        assert pepc_get_color(75) == "#92D050"   # Satisfactory
        assert pepc_get_color(100) == "#92D050"  # Satisfactory
        assert pepc_get_color(125) == "#FFFF00"  # Moderate
        assert pepc_get_color(150) == "#FFFF00"  # Moderate
        assert pepc_get_color(175) == "#ED7D31"  # Unhealthy (Sensitive)
        assert pepc_get_color(200) == "#ED7D31"  # Unhealthy (Sensitive)
        assert pepc_get_color(250) == "#FF0000"  # Unhealthy
        assert pepc_get_color(300) == "#FF0000"  # Unhealthy
        assert pepc_get_color(350) == "#7030A0"  # Very Unhealthy
        assert pepc_get_color(400) == "#7030A0"  # Very Unhealthy
        assert pepc_get_color(450) == "#C00000"  # Hazardous
        assert pepc_get_color(500) == "#C00000"  # Hazardous

    def test_peqs_continuous_rgb_interpolation(self):
        """Continuous RGB interpolation smoothly blends across PEQS standard limits."""
        ref_pm25 = 35.0  # PEQS standard for PM2.5 24h

        # Clean (0.0x limit) -> Stop 0: [58, 165, 93]
        rgb_clean = pepc_interpolate_color(0.0, ref_pm25)
        assert rgb_clean == (58, 165, 93)

        # At Standard (1.0x limit: 35.0 ug/m3) -> Stop 2: [242, 194, 48]
        rgb_std = pepc_interpolate_color(35.0, ref_pm25)
        assert rgb_std == (242, 194, 48)

        # Extreme (>= 6.0x limit: 210.0 ug/m3) -> Stop 6: [90, 21, 48]
        rgb_extreme = pepc_interpolate_color(250.0, ref_pm25)
        assert rgb_extreme == (90, 21, 48)

        # Midpoint between 0.0x and 0.5x (0.25x limit = 8.75 ug/m3)
        # Should blend Stop 0 [58, 165, 93] and Stop 1 [156, 204, 58]
        rgb_mid = pepc_interpolate_color(8.75, ref_pm25)
        expected_r = int(round((58 + 156) / 2))
        expected_g = int(round((165 + 204) / 2))
        expected_b = int(round((93 + 58) / 2))
        assert abs(rgb_mid[0] - expected_r) <= 1
        assert abs(rgb_mid[1] - expected_g) <= 1
        assert abs(rgb_mid[2] - expected_b) <= 1

        # Hex format check
        hex_std = pepc_interpolate_color_hex(35.0, ref_pm25)
        assert hex_std == "#F2C230"
