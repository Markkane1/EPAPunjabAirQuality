"""
Unit tests for Transformation 10 (24-Hour Diurnal Persistence Forecast),
Transformation 11 (Atmospheric Ventilation Index), and Stream 8 (PBL Ingestion Worker).
"""
import pytest
from datetime import datetime, timezone

from src.domain.math.forecast import (
    calculate_24h_persistence_forecast,
    calculate_multi_district_forecast,
)
from src.domain.math.pbl import (
    calculate_ventilation_index,
    classify_ventilation_index,
    calculate_and_classify_vi,
    VI_CRITICAL_TRAP_THRESHOLD,
    VI_POOR_THRESHOLD,
    VI_MODERATE_THRESHOLD,
    DISPERSION_CRITICAL_TRAP,
    DISPERSION_POOR,
    DISPERSION_MODERATE,
    DISPERSION_GOOD,
)
from src.domain.schemas.pbl import PBLObservation, DistrictPBLSummary
from src.pipelines.pbl import PBLIngestionWorker, NOVEMBER_CLIMATOLOGICAL_PBL_PKT
from src.pipelines.fallback_engine import FallbackTemplateEngine


class TestDiurnalPersistenceForecast:
    """Tests Transformation 10: 24h Diurnal Persistence Forecast Engine."""

    def test_forecast_identity_when_series_equal(self):
        """When recent == historical, ratio is 1.0 and forecast exactly mirrors recent series."""
        recent = [100.0 + i * 2 for i in range(24)]
        forecast = calculate_24h_persistence_forecast(recent, recent)
        assert len(forecast) == 24
        assert forecast == [round(v, 2) for v in recent]

    def test_forecast_upward_scaling(self):
        """When recent is 1.5x historical, forecast scales recent diurnal shape by 1.5."""
        historical = [100.0] * 24
        recent = [150.0] * 24
        forecast = calculate_24h_persistence_forecast(recent, historical)
        assert len(forecast) == 24
        # 150 * (150/100) = 225.0
        assert forecast == [225.0] * 24

    def test_forecast_downward_scaling(self):
        """When recent is 0.5x historical, forecast scales down by 0.5."""
        historical = [200.0] * 24
        recent = [100.0] * 24
        forecast = calculate_24h_persistence_forecast(recent, historical)
        assert forecast == [50.0] * 24

    def test_forecast_diurnal_curve_shape_preserved(self):
        """Diurnal peak in morning and evening is preserved during scaling."""
        recent = [50.0, 60.0, 80.0, 120.0, 90.0, 70.0] + [50.0] * 18
        forecast = calculate_24h_persistence_forecast(recent)
        # Without historical, ratio is 1.0
        assert forecast[:6] == [50.0, 60.0, 80.0, 120.0, 90.0, 70.0]

    def test_forecast_handles_short_series_padding(self):
        """Pads short inputs to full 24-hour cycle."""
        short_series = [100.0, 110.0, 120.0]
        forecast = calculate_24h_persistence_forecast(short_series)
        assert len(forecast) == 24
        assert forecast[0] == 100.0
        assert forecast[-1] == 120.0

    def test_forecast_scale_clamps(self):
        """Asserts ratio does not exceed min/max bounds."""
        historical = [10.0] * 24
        recent = [1000.0] * 24  # 100x jump
        forecast = calculate_24h_persistence_forecast(recent, historical, max_scale_factor=5.0)
        # Should be clamped to 5.0 * 1000 = 5000.0
        assert forecast[0] == 5000.0

    def test_multi_district_forecast(self):
        """Calculates forecasts across multiple districts."""
        data = {
            "Lahore": [250.0] * 24,
            "Faisalabad": [180.0] * 24,
        }
        res = calculate_multi_district_forecast(data)
        assert "Lahore" in res
        assert "Faisalabad" in res
        assert len(res["Lahore"]) == 24


class TestVentilationIndexAndPBL:
    """Tests Transformation 11: Atmospheric Ventilation Index & Risk Classification."""

    def test_vi_formula(self):
        """VI = h_PBL * w_sfc."""
        # 500m * 2.0 m/s = 1000.0 m^2/s
        assert calculate_ventilation_index(500.0, 2.0) == 1000.0
        # 1200m * 5.5 m/s = 6600.0 m^2/s
        assert calculate_ventilation_index(1200.0, 5.5) == 6600.0

    def test_vi_statutory_dispersion_bands(self):
        """Asserts exact statutory thresholds."""
        # Critical Trap: < 2000
        assert classify_ventilation_index(1500.0) == DISPERSION_CRITICAL_TRAP
        assert classify_ventilation_index(1999.9) == DISPERSION_CRITICAL_TRAP

        # Poor: 2000 <= VI < 4000
        assert classify_ventilation_index(2000.0) == DISPERSION_POOR
        assert classify_ventilation_index(3999.0) == DISPERSION_POOR

        # Moderate: 4000 <= VI < 6000
        assert classify_ventilation_index(4000.0) == DISPERSION_MODERATE
        assert classify_ventilation_index(5999.0) == DISPERSION_MODERATE

        # Good: >= 6000
        assert classify_ventilation_index(6000.0) == DISPERSION_GOOD
        assert classify_ventilation_index(10000.0) == DISPERSION_GOOD

    def test_calculate_and_classify_vi(self):
        """Verifies combined function returns (vi, category, color)."""
        # Nocturnal inversion: 150m, 1.2 m/s -> VI = 180.0 -> Critical Trap, #C00000
        vi, cat, color = calculate_and_classify_vi(150.0, 1.2)
        assert vi == 180.0
        assert cat == DISPERSION_CRITICAL_TRAP
        assert color == "#C00000"

    def test_pbl_observation_schema(self):
        """Verifies Pydantic v2 schema validation."""
        obs = PBLObservation(
            district="Lahore",
            timestamp=datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc),
            boundary_layer_height=850.0,
            surface_wind_speed=2.5,
            ventilation_index=2125.0,
            dispersion_category=DISPERSION_POOR,
            is_estimated=False,
        )
        assert obs.district == "Lahore"
        assert obs.ventilation_index == 2125.0


class TestPBLIngestionWorker:
    """Tests Stream 8 (STR-08-PBL) Ingestion Worker."""

    def test_worker_initialization(self):
        worker = PBLIngestionWorker()
        assert worker.stream_id == "STR-08-PBL"
        assert worker.polling_cadence == "0 * * * *"

    def test_parse_and_validate_open_meteo_payload(self):
        worker = PBLIngestionWorker()
        mock_payload = {
            "hourly": {
                "time": ["2026-11-10T00:00", "2026-11-10T01:00"],
                "boundary_layer_height": [180.0, 150.0],
                "wind_speed_10m": [1.5, 1.2],
            }
        }
        res = worker.parse_and_validate(mock_payload, district_names=["Lahore"], hour_index=0)
        assert len(res) == 1
        lahore = res[0]
        assert lahore["district"] == "Lahore"
        assert lahore["boundary_layer_height"] == 180.0
        assert lahore["surface_wind_speed"] == 1.5
        assert lahore["ventilation_index"] == 270.0
        assert lahore["is_critical_trap"] is True
        assert lahore["dispersion_category"] == DISPERSION_CRITICAL_TRAP

    def test_fallback_generates_41_districts_with_climatology(self):
        engine = FallbackTemplateEngine()
        worker = PBLIngestionWorker(fallback_engine=engine)
        # Nighttime 03:00 PKT -> severe inversion (120m)
        fallback = worker.get_fallback(hour_pkt=3)
        assert len(fallback) == 41
        for item in fallback:
            assert item["is_estimated"] is True
            assert item["boundary_layer_height"] == 120.0
            assert item["is_critical_trap"] is True
