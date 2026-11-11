"""
Comprehensive Unit Tests for Temporal QC Cleaning, Outlier Scrubbing, and Aggregation Filters.
Tests:
- Step 0 zero/negative purge
- 7-hour rolling median spike filter (>4M and >3ref)
- 3-hour logger hold (sensor freeze) filter with i >= 2 index guard
- Dimensional exemption: logger hold filter strictly disabled for 'AQI'
- Regulatory 75% completeness temporal aggregation rule
- Continuous sub-hourly linear animation lerp (60 FPS scrubber)
"""
import math
import pytest

from src.domain.math.qc import (
    check_completeness,
    subhourly_lerp,
    temporal_qc_clean,
)


class TestStep0ZeroSanitization:
    """Verifies that non-positive, NaN, and None values are purged prior to filtering."""

    def test_zero_and_negative_purge(self):
        raw = [10.0, 0.0, -5.0, None, float("nan"), 25.0]
        cleaned, spikes = temporal_qc_clean(raw, ref_limit=35.0, pollutant="PM2.5")

        assert cleaned[0] == 10.0
        assert cleaned[1] is None  # 0.0 purged
        assert cleaned[2] is None  # -5.0 purged
        assert cleaned[3] is None  # None purged
        assert cleaned[4] is None  # NaN purged
        assert cleaned[5] == 25.0
        assert spikes == 0


class TestSevenHourMedianSpikeFilter:
    """Verifies the 7-hour rolling window median spike filter (>4M and >3ref)."""

    def test_spike_filtered_when_exceeding_both_thresholds(self):
        """
        Spike condition: v_i > 4.0 * M_i AND v_i > 3.0 * ref_p.
        Let ref_p = 35.0 ug/m3. 3.0 * ref_p = 105.0.
        Window baseline ~ 30.0 (M_i = 30.0). 4.0 * M_i = 120.0.
        A transient surge of 500.0 ug/m3 (>120 and >105) must be flagged and set to None.
        """
        series = [30.0, 31.0, 30.0, 500.0, 31.0, 30.0, 32.0]
        cleaned, spikes = temporal_qc_clean(series, ref_limit=35.0, pollutant="PM2.5")

        assert cleaned[3] is None
        assert spikes == 1
        # Surrounding baseline values remain intact
        assert cleaned[0] == 30.0
        assert cleaned[6] == 32.0

    def test_spike_retained_if_not_exceeding_ref_limit_threshold(self):
        """
        If a value is > 4.0 * M_i but <= 3.0 * ref_limit, it is a valid low-level fluctuation.
        Let ref_limit = 35.0 (3.0 * ref = 105.0).
        Window baseline ~ 5.0 (M_i = 5.0). 4.0 * M_i = 20.0.
        Reading = 50.0 (>20.0, but < 105.0) -> must be RETAINED!
        """
        series = [5.0, 5.0, 5.0, 50.0, 5.0, 5.0, 5.0]
        cleaned, spikes = temporal_qc_clean(series, ref_limit=35.0, pollutant="PM2.5")

        assert cleaned[3] == 50.0
        assert spikes == 0

    def test_spike_retained_if_not_exceeding_median_multiplier(self):
        """
        If a sustained high-pollution event occurs (severe smog), multiple hours are elevated.
        M_i is high, so v_i <= 4.0 * M_i even though v_i > 3.0 * ref.
        Values must be preserved (not falsely flagged as single-hour electrical spikes).
        """
        series = [250.0, 260.0, 255.0, 270.0, 265.0, 250.0, 255.0]
        cleaned, spikes = temporal_qc_clean(series, ref_limit=35.0, pollutant="PM2.5")

        assert cleaned[3] == 270.0
        assert spikes == 0


class TestThreeHourLoggerHoldFilter:
    """Verifies the 3-hour logger hold (sensor freeze) filter with i >= 2 guard."""

    def test_three_consecutive_identical_readings_purged_for_physical_pollutant(self):
        """
        For physical pollutants (PM2.5, PM10, etc.), 3 consecutive identical values
        indicate ADC or digital logger freeze. The 3rd reading must be set to None.
        """
        series = [45.0, 50.0, 50.0, 50.0, 60.0]
        cleaned, _ = temporal_qc_clean(series, ref_limit=35.0, pollutant="PM2.5")

        assert cleaned[0] == 45.0
        assert cleaned[1] == 50.0
        assert cleaned[2] == 50.0
        assert cleaned[3] is None  # 3rd identical reading purged
        assert cleaned[4] == 60.0

    def test_logger_hold_index_guard_prevents_negative_wraparound(self):
        """
        Ensures index i starts at 2 (guard i >= 2), preventing Python array wraparound (-1, -2).
        Even if series[0] == series[-1] == series[-2], series[0] must not be purged!
        """
        series = [50.0, 60.0, 70.0, 50.0, 50.0]
        cleaned, _ = temporal_qc_clean(series, ref_limit=35.0, pollutant="PM2.5")

        assert cleaned[0] == 50.0  # Not purged by negative index wraparound
        assert cleaned[1] == 60.0

    def test_aqi_exempt_from_logger_hold_filter(self):
        """
        CRITICAL DOMAIN RULE:
        Dimensionless ordinal index 'AQI' is EXEMPT from logger hold filtering.
        Integer AQI values frequently remain constant across multiple hours (e.g. 500 during smog).
        """
        series = [500.0, 500.0, 500.0, 500.0, 500.0]
        cleaned, _ = temporal_qc_clean(series, ref_limit=35.0, pollutant="AQI")

        # None of the 500 values should be purged
        assert all(v == 500.0 for v in cleaned)

        # Also case-insensitive check
        cleaned_lower, _ = temporal_qc_clean(series, ref_limit=35.0, pollutant="aqi")
        assert all(v == 500.0 for v in cleaned_lower)

    def test_sustained_four_hour_logger_hold_purged(self):
        """
        Verifies that a 4-hour freeze purges all values from index 2 onward.
        Both standalone [50, 50, 50, 50] and embedded [40, 50, 50, 50, 50, 60].
        """
        standalone = [50.0, 50.0, 50.0, 50.0]
        cleaned_standalone, _ = temporal_qc_clean(standalone, ref_limit=35.0, pollutant="PM2.5")
        assert cleaned_standalone == [50.0, 50.0, None, None]

        embedded = [40.0, 50.0, 50.0, 50.0, 50.0, 60.0]
        cleaned_embedded, _ = temporal_qc_clean(embedded, ref_limit=35.0, pollutant="PM2.5")
        assert cleaned_embedded == [40.0, 50.0, 50.0, None, None, 60.0]

    def test_sustained_five_hour_logger_hold_purged(self):
        """
        Verifies that a 5-hour freeze purges all values from index 2 onward:
        [150.0, 150.0, 150.0, 150.0, 150.0] -> [150.0, 150.0, None, None, None].
        """
        series = [150.0, 150.0, 150.0, 150.0, 150.0]
        cleaned, _ = temporal_qc_clean(series, ref_limit=35.0, pollutant="PM2.5")
        assert cleaned == [150.0, 150.0, None, None, None]

    def test_sustained_twelve_hour_logger_hold_purged(self):
        """
        Verifies that a sustained 12-hour freeze (e.g. overnight logger failure)
        purges all 10 hours from index 2 onward to None, keeping only the first 2.
        """
        series = [80.0] * 12
        cleaned, _ = temporal_qc_clean(series, ref_limit=35.0, pollutant="PM2.5")
        expected = [80.0, 80.0] + [None] * 10
        assert cleaned == expected


class TestCompletenessRule:
    """Verifies regulatory 75% completeness rule for temporal aggregation."""

    def test_twenty_four_hour_completeness_threshold(self):
        """
        For 24-hour daily rollup: round(0.75 * 24) = 18 hours required.
        18 valid hours -> arithmetic mean computed.
        17 valid hours -> returns None.
        """
        # Exactly 18 valid hours
        series_18 = [10.0] * 18 + [None] * 6
        assert check_completeness(series_18, required_ratio=0.75) == 10.0

        # 17 valid hours (below 75%)
        series_17 = [10.0] * 17 + [None] * 7
        assert check_completeness(series_17, required_ratio=0.75) is None

        # Full 24 hours
        series_24 = [20.0] * 24
        assert check_completeness(series_24, required_ratio=0.75) == 20.0

    def test_short_duration_completeness(self):
        """Short intervals enforce max(1, round(0.75 * H))."""
        # 4-hour window: round(0.75 * 4) = 3 hours required
        assert check_completeness([10.0, 20.0, 30.0, None], 0.75) == 20.0
        assert check_completeness([10.0, 20.0, None, None], 0.75) is None


class TestSubHourlyAnimationLerp:
    """Verifies sub-hourly linear interpolation for smooth 60 FPS animation scrubbing."""

    def test_continuous_lerp_between_valid_points(self):
        series = [100.0, 200.0, 300.0]
        # At keyframe 0: 100.0
        assert subhourly_lerp(series, 0.0) == 100.0
        # Halfway between 0 and 1: 150.0
        assert subhourly_lerp(series, 0.5) == 150.0
        # At keyframe 1: 200.0
        assert subhourly_lerp(series, 1.0) == 200.0
        # 3/4 between 1 and 2: 275.0
        assert subhourly_lerp(series, 1.75) == 275.0
        # At keyframe 2: 300.0
        assert subhourly_lerp(series, 2.0) == 300.0

    def test_lerp_partial_null_fallback(self):
        """When one bounding endpoint is null, gracefully fall back to the other."""
        series = [100.0, None, 300.0]
        # Between 0 (100) and 1 (None) -> falls back to 100.0
        assert subhourly_lerp(series, 0.5) == 100.0
        # Between 1 (None) and 2 (300) -> falls back to 300.0
        assert subhourly_lerp(series, 1.5) == 300.0

    def test_lerp_boundary_clamping(self):
        """fp outside [0, N-1] is safely clamped."""
        series = [100.0, 200.0]
        assert subhourly_lerp(series, -1.5) == 100.0
        assert subhourly_lerp(series, 5.0) == 200.0
