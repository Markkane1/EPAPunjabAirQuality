"""
Unit Tests for NASA FIRMS VIIRS Active Fire Anomalies & Historical Archive.
Verifies:
1. Live fires & 24-hour active hotspot detection queries.
2. Complete historical archive queries across 12 months.
3. Monthly breakdown trends and Kharif/Rabi seasonal peaks.
4. Custom date duration filtering and regional distribution.
5. FastAPI REST endpoints for fire telemetry.
"""
from fastapi.testclient import TestClient
import pytest
from src.api.main import app
from src.pipelines.firms import FirmsIngestionWorker


class TestFireAnomaliesPipeline:
    """Verifies FirmsIngestionWorker historical archive loading and filtering."""

    @pytest.fixture(autouse=True)
    def setup_worker(self):
        self.worker = FirmsIngestionWorker()

    def test_live_and_24h_fire_detections(self):
        """Verifies live fires and 24h detections exist and have valid coordinates and FRP."""
        fires = self.worker.get_active_fires(hours=24)
        assert len(fires) > 0, "Expected non-empty active fires within 24h"

        for f in fires:
            assert 27.0 <= f.latitude <= 35.0, f"Latitude {f.latitude} out of airshed range"
            assert 69.0 <= f.longitude <= 78.0, f"Longitude {f.longitude} out of airshed range"
            assert f.frp >= 0.0, f"FRP {f.frp} must be non-negative"
            assert f.confidence in ("low", "nominal", "high")
            assert f.satellite in ("NOAA-20", "NOAA-21", "Suomi-NPP")

    def test_fire_summary_and_monthly_trends(self):
        """Verifies 12-month historical monthly trends and seasonal peaks."""
        summary_res = self.worker.get_fire_summary()
        assert summary_res["status"] == "success"
        summary = summary_res["summary"]

        assert summary["live_fires_count"] > 0
        assert summary["fires_24h_count"] >= summary["live_fires_count"]
        assert summary["total_historical_records"] > 1000

        trends = summary_res["monthly_trends"]
        assert len(trends) == 12, f"Expected 12 monthly trend buckets, got {len(trends)}"

        # Verify Kharif peak (October/November) has significantly higher fires than off-season (July/August)
        oct_trend = next((t for t in trends if t["month_num"] == 10), None)
        jul_trend = next((t for t in trends if t["month_num"] == 7), None)
        assert oct_trend is not None
        assert jul_trend is not None
        assert oct_trend["total_estimated_fires"] > jul_trend["total_estimated_fires"] * 10

    def test_query_history_by_month(self):
        """Verifies querying fires for a specific historical month."""
        oct_res = self.worker.query_history(month="2026-10", limit=1000)
        assert oct_res["status"] == "success"
        assert oct_res["count"] > 0
        for f in oct_res["fires"]:
            assert f["acq_date"].startswith("2026-10")

    def test_query_history_by_custom_date_range(self):
        """Verifies querying fires for a specific date duration."""
        start_date = "2026-10-15"
        end_date = "2026-11-05"
        res = self.worker.query_history(start_date=start_date, end_date=end_date, limit=1000)
        assert res["status"] == "success"
        assert res["count"] > 0
        for f in res["fires"]:
            assert start_date <= f["acq_date"] <= end_date

    def test_query_history_by_duration_preset(self):
        """Verifies duration presets: 24h, 7d, 30d, 1y."""
        res_24h = self.worker.query_history(duration="24h")
        res_7d = self.worker.query_history(duration="7d")
        res_30d = self.worker.query_history(duration="30d")
        res_1y = self.worker.query_history(duration="1y")

        assert res_24h["status"] == "success"
        assert res_7d["status"] == "success"
        assert res_30d["status"] == "success"
        assert res_1y["status"] == "success"

        assert res_1y["summary"]["total_fires"] >= res_30d["summary"]["total_fires"]
        assert res_30d["summary"]["total_fires"] >= res_7d["summary"]["total_fires"]


class TestFireAnomaliesApiEndpoints:
    """Verifies FastAPI REST endpoints under /api/v1/observations/fires*."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = TestClient(app)

    def test_api_get_active_fires(self):
        resp = self.client.get("/api/v1/observations/fires?hours=24")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "count" in data
        assert "live_fires" in data
        assert "fires_24h" in data
        assert isinstance(data["fires"], list)
        assert data["count"] > 0

    def test_api_get_fire_summary(self):
        resp = self.client.get("/api/v1/observations/fires/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "summary" in data
        assert "monthly_trends" in data
        assert len(data["monthly_trends"]) == 12

    def test_api_get_historic_fires_month(self):
        resp = self.client.get("/api/v1/observations/fires/history?month=2026-10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["count"] > 0
        assert "summary" in data
        assert data["summary"]["total_fires"] > 0

    def test_api_get_historic_fires_custom_duration(self):
        resp = self.client.get("/api/v1/observations/fires/history?start_date=2026-10-01&end_date=2026-10-31&min_frp=20.0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        for f in data["fires"]:
            assert f["frp"] >= 20.0
            assert "2026-10-01" <= f["acq_date"] <= "2026-10-31"
