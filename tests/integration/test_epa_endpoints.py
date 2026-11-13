"""
Integration test suite for EPA Punjab Live API endpoints (/api/v1/epa/*).
"""
import pytest
from fastapi.testclient import TestClient
import httpx

from src.api.main import app
from src.api.routes.epa import get_epa_worker
from src.pipelines.epa_punjab import EPAPunjabIngestionWorker


@pytest.fixture
def client():
    return TestClient(app)


class TestEPAEndpoints:
    """Verifies /api/v1/epa routes and response serialization."""

    def test_get_epa_stations(self, client):
        resp = client.get("/api/v1/epa/stations")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 38
        ids = {s["api_id"] for s in data}
        assert "Safari Park-LHR" in ids
        assert "UET-LHR" in ids
        assert "Mobile 1" in ids
        assert "Mobile 5" in ids
        assert "DC Office Rawalpindi" in ids

    def test_get_epa_status_live_or_mocked(self, client):
        resp = client.get("/api/v1/epa/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "upstream_url" in data
        assert "latency_ms" in data

    def test_get_epa_latest_mocked(self, client, monkeypatch):
        mock_latest_payload = {
            "UET-LHR": {
                "Date_Time": "2026-11-13 13:00:00",
                "AQI": 117,
                "AQI_category": "Moderate",
                "Dominant_Pollutant": "PM25",
                "PM25": 46.39,
                "PM10": 157.35,
                "O3": 35.33,
                "NO2": 15.56,
                "SO2": 113.97,
                "CO": 0.37,
                "WS": 1.48,
                "WD": 285.77,
                "Temp": 21.21,
                "RH": 73.0,
            },
            "Safari Park-LHR": {
                "Date_Time": "2026-11-13 13:00:00",
                "AQI": 304,
                "PM25": 253.48,
                "PM10": 336.71,
                "Status_PM25": "Incomplete",
            },
        }

        async def mock_fetch_latest():
            return mock_latest_payload

        worker = get_epa_worker()
        monkeypatch.setattr(worker, "fetch_latest_hour", mock_fetch_latest)

        resp = client.get("/api/v1/epa/latest?force_refresh=true")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["total_stations"] == 38

        # Find UET
        uet = next(s for s in data["stations"] if s["station_id"] == "UET-LHR")
        assert uet["pm25"] == 46.39
        assert uet["district"] == "Lahore"
        assert uet["aqi"] == 117.0

        # Find Safari Park with Status_PM25: Incomplete
        safari = next(s for s in data["stations"] if s["station_id"] == "Safari Park-LHR")
        assert safari["pm25"] is None  # Status_PM25: Incomplete filtered to None
        assert safari["pm10"] == 336.71

    def test_get_epa_daily_mocked(self, client, monkeypatch):
        async def mock_fetch_daily(station_id=None):
            return {
                "UET-LHR": [
                    {"Date_Time": "2026-11-13 00:00:00", "AQI": 110, "PM25": 40.0},
                    {"Date_Time": "2026-11-13 01:00:00", "AQI": 115, "PM25": 45.0},
                ]
            }

        worker = get_epa_worker()
        monkeypatch.setattr(worker, "fetch_daily", mock_fetch_daily)

        resp = client.get("/api/v1/epa/daily?station_id=UET-LHR")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert len(data["data"]["UET-LHR"]) == 2

    def test_get_epa_periodic_validation(self, client):
        # Invalid interval must return 400
        resp = client.get("/api/v1/epa/periodic?station_id=UET-LHR&start_datetime=2026-11-13%2000:00:00&end_datetime=2026-11-13%2012:00:00&interval=45")
        assert resp.status_code == 400
        assert "Invalid interval" in resp.json()["detail"]

    def test_get_epa_alerts_mocked(self, client, monkeypatch):
        mock_alerts = [
            {"Alert": "E04.3: No Data from Station DC Office Rahim Yar Khan for: 2026-11-13 13:00:00+05:00", "Date_Time": "2026-11-13 13:00:00"},
            {"Alert": "E08: Choking/Sticking for NOX at FMDRC-LHR for 2026-11-13 11:00:00 to 2026-11-13 13:00:00", "Date_Time": "2026-11-13 13:00:00"},
            {"Alert": "E07: Spike/Abrupt Changes for SO2 at Safari Park-LHR at 2026-11-13 13:00:00", "Date_Time": "2026-11-13 13:00:00"},
        ]

        async def mock_fetch_alerts():
            return mock_alerts

        worker = get_epa_worker()
        monkeypatch.setattr(worker, "fetch_alerts_last_two_days", mock_fetch_alerts)

        # Unfiltered
        resp = client.get("/api/v1/epa/alerts?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 3
        assert data["alerts"][0]["code"] == "E04.3"
        assert data["alerts"][1]["code"] == "E08"
        assert data["alerts"][2]["code"] == "E07"

        # Filtered by code
        resp_filtered = client.get("/api/v1/epa/alerts?code=E08")
        assert resp_filtered.status_code == 200
        data_filtered = resp_filtered.json()
        assert data_filtered["count"] == 1
        assert data_filtered["alerts"][0]["code"] == "E08"
