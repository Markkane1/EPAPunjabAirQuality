"""
Integration tests for advanced analytics routes:
1. GET /api/v1/analytics/forecast (Transformation 10: 24h Diurnal Persistence Forecast)
2. GET /api/v1/analytics/ventilation (Transformation 11: Atmospheric Ventilation Index & Risk Classification)
3. GET /api/v1/analytics/emergency-actions (Domain 1 GAP-REG-01: Graded Emergency Action Policy Engine)
"""
import pytest
import httpx
from httpx import ASGITransport

from src.api.main import create_application


@pytest.fixture(scope="module")
def app():
    return create_application()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_forecast_endpoint(app):
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Default district (Lahore)
        resp = await client.get("/api/v1/analytics/forecast")
        assert resp.status_code == 200
        data = resp.json()
        assert data["district"] == "Lahore"
        assert data["pollutant"] == "PM2.5"
        assert len(data["forecast_24h"]) == 24
        assert data["recent_mean"] > 0
        assert data["projected_peak"] > 0
        assert len(data["multi_district_forecast"]) > 0

        # Custom district
        resp_faisalabad = await client.get("/api/v1/analytics/forecast?district=Faisalabad&pollutant=PM10")
        assert resp_faisalabad.status_code == 200
        data_f = resp_faisalabad.json()
        assert data_f["district"] == "Faisalabad"
        assert data_f["pollutant"] == "PM10"
        assert len(data_f["forecast_24h"]) == 24


@pytest.mark.anyio
async def test_ventilation_endpoint(app):
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        resp = await client.get("/api/v1/analytics/ventilation?district=Lahore")
        assert resp.status_code == 200
        data = resp.json()
        assert data["district"] == "Lahore"
        assert "pbl_height_m" in data
        assert "surface_wind_speed_ms" in data
        assert "ventilation_index" in data
        assert "dispersion_category" in data
        assert "is_critical_trap" in data
        assert len(data["districts"]) > 0


@pytest.mark.anyio
async def test_emergency_actions_endpoint(app):
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Provincial status
        resp = await client.get("/api/v1/analytics/emergency-actions")
        assert resp.status_code == 200
        data = resp.json()
        assert "provincial_mean_aqi" in data
        assert "overall_alert_level" in data
        assert "overall_alert_name" in data
        assert len(data["all_evaluations"]) > 0

        # Targeted district query
        resp_dist = await client.get("/api/v1/analytics/emergency-actions?district=Lahore")
        assert resp_dist.status_code == 200
        data_d = resp_dist.json()
        assert data_d["district_evaluation"] is not None
        d_eval = data_d["district_evaluation"]
        assert d_eval["district"] == "Lahore"
        assert "alert_level" in d_eval
        assert "mandatory_actions" in d_eval
        assert len(d_eval["mandatory_actions"]) > 0


@pytest.mark.anyio
async def test_spatial_surface_and_labels_endpoints(app):
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Spatial surface with anisotropic plume weighting
        resp_surf = await client.get("/api/v1/spatial/surface?pollutant=PM2.5&resolution=10&anisotropic=true")
        assert resp_surf.status_code == 200
        data_s = resp_surf.json()
        assert data_s["pollutant"] == "PM2.5"
        assert data_s["resolution"] == 10
        assert data_s["grid_width"] > 0
        assert data_s["grid_height"] > 0
        assert len(data_s["grid_matrix"]) == data_s["grid_height"]
        assert len(data_s["opacity_matrix"]) == data_s["grid_height"]

        # Spatial district collision-free label placements
        resp_lbl = await client.get("/api/v1/spatial/labels?width_px=1200&height_px=900")
        assert resp_lbl.status_code == 200
        labels = resp_lbl.json()
        assert isinstance(labels, list)
        assert len(labels) == 41
        lhr = next(item for item in labels if item["text"] == "Lahore")
        assert "anchor_x" in lhr
        assert "placed_x" in lhr
        assert "has_leader_line" in lhr
