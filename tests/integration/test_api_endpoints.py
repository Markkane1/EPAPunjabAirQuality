"""
Comprehensive Integration Test Suite for Punjab Air Quality API Gateway.
Verifies all 10 M4 API endpoints across metadata, observations, spatial grid,
analytics, CSV ingestion, and SSE live telemetry push.
Uses httpx.AsyncClient with ASGITransport(app=app) via anyio.
"""
from pathlib import Path
import pytest
import httpx
from httpx import ASGITransport

from src.api.main import create_application

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"


@pytest.fixture(scope="module")
def app():
    """Create and initialize FastAPI application for test suite."""
    return create_application()


@pytest.fixture
def anyio_backend():
    """Specify anyio backend engine."""
    return "asyncio"


# -------------------------------------------------------------------------
# Health and App Initialization Tests
# -------------------------------------------------------------------------

@pytest.mark.anyio
async def test_health_check_endpoint(app):
    """GET /health should return 200 with service health info and station/district counts."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "punjab-air-quality-api"


# -------------------------------------------------------------------------
# Endpoint 1 & 2: Metadata Endpoints
# -------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_districts_metadata(app):
    """GET /api/v1/meta/districts should return all 41 Punjab districts."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/meta/districts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 41

        lahore = next((d for d in data if d["name"] == "Lahore"), None)
        assert lahore is not None
        assert lahore["division"] == "Lahore"
        assert 31.0 < lahore["latitude"] < 32.0
        assert 74.0 < lahore["longitude"] < 75.0
        assert "border_distance_km" in lahore
        assert "is_monitored" in lahore


@pytest.mark.anyio
async def test_get_stations_metadata(app):
    """GET /api/v1/meta/stations should return all stations and support district filtering."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Unfiltered
        response = await client.get("/api/v1/meta/stations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 85

        first_station = data[0]
        assert "id" in first_station
        assert "name" in first_station
        assert "district" in first_station
        assert "latitude" in first_station
        assert "longitude" in first_station
        assert "station_type" in first_station

        # Filtered by district
        lahore_resp = await client.get("/api/v1/meta/stations?district=Lahore")
        assert lahore_resp.status_code == 200
        lahore_stations = lahore_resp.json()
        assert len(lahore_stations) > 0
        assert all(s["district"] == "Lahore" for s in lahore_stations)


# -------------------------------------------------------------------------
# Endpoint 3 & 4: Observation Endpoints
# -------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_current_observations(app):
    """GET /api/v1/observations/current returns latest provincial snapshot and district metrics."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/observations/current")
        assert response.status_code == 200
        data = response.json()

        assert "provincial_summary" in data
        summary = data["provincial_summary"]
        assert "mean_aqi" in summary
        assert "peak_district" in summary
        assert "peak_aqi" in summary
        assert summary["reporting_districts_count"] > 0
        assert summary["total_districts"] == 41

        assert "districts" in data
        assert isinstance(data["districts"], dict)
        assert len(data["districts"]) == 41

        assert "Lahore" in data["districts"]
        lahore_reading = data["districts"]["Lahore"]
        assert "aqi" in lahore_reading
        assert "district" in lahore_reading


@pytest.mark.anyio
async def test_get_hourly_observations(app):
    """GET /api/v1/observations/hourly returns hourly time-series vectors."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/observations/hourly")
        assert response.status_code == 200
        data = response.json()

        assert "hours" in data
        assert isinstance(data["hours"], list)
        assert len(data["hours"]) > 0
        assert data["total_hours"] == len(data["hours"])

        assert "districts" in data
        assert "Lahore" in data["districts"]
        lahore_series = data["districts"]["Lahore"]
        assert "concentrations" in lahore_series
        assert len(lahore_series["concentrations"]) == len(data["hours"])


# -------------------------------------------------------------------------
# Endpoint 5: Spatial Surface Matrix
# -------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_spatial_surface(app):
    """GET /api/v1/spatial/surface returns 2D continuous IDW surface grid raster."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/spatial/surface?pollutant=PM2.5&resolution=5")
        assert response.status_code == 200
        data = response.json()

        assert data["pollutant"] == "PM2.5"
        assert "grid_matrix" in data
        assert "grid_width" in data
        assert "grid_height" in data
        assert len(data["grid_matrix"]) == data["grid_height"]
        assert len(data["grid_matrix"][0]) == data["grid_width"]
        assert "min_val" in data
        assert "max_val" in data
        assert data["max_val"] >= data["min_val"]


# -------------------------------------------------------------------------
# Endpoint 6: Analytics - CPF Wind Rose
# -------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_analytics_cpf(app):
    """GET /api/v1/analytics/cpf returns 16-sector Conditional Probability Function."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/analytics/cpf?district=Lahore&pollutant=PM2.5")
        assert response.status_code == 200
        data = response.json()

        assert data["district"] == "Lahore"
        assert data["pollutant"] == "PM2.5"
        assert "threshold_p75" in data
        assert "calm_fraction" in data
        assert "sectors" in data
        assert len(data["sectors"]) == 16

        # Verify sector structure
        sec = data["sectors"][0]
        assert "sector_index" in sec
        assert "azimuth_deg" in sec
        assert "direction_label" in sec
        assert "total_hours" in sec
        assert "exceedance_hours" in sec


# -------------------------------------------------------------------------
# Endpoint 7: Analytics - Advection Flux Mass Transport & AQI Guard
# -------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_analytics_flux_valid(app):
    """GET /api/v1/analytics/flux returns pairwise advection flux links for physical mass species."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/analytics/flux?pollutant=PM2.5")
        assert response.status_code == 200
        data = response.json()

        assert data["pollutant"] == "PM2.5"
        assert "top_pathways" in data
        assert isinstance(data["top_pathways"], list)
        # Enforces maximum 60 top pathways for UI visual clutter control
        assert len(data["top_pathways"]) <= 60

        if len(data["top_pathways"]) > 0:
            first_pw = data["top_pathways"][0]
            assert "source_district" in first_pw
            assert "receptor_district" in first_pw
            assert "flux" in first_pw
            assert "omega" in first_pw
            assert "score" in first_pw


@pytest.mark.anyio
async def test_get_analytics_flux_aqi_guard_rejected(app):
    """GET /api/v1/analytics/flux?pollutant=AQI must be strictly rejected with HTTP 400."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/analytics/flux?pollutant=AQI")
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "physically undefined" in data["detail"].lower() or "mass conservation" in data["detail"].lower()


# -------------------------------------------------------------------------
# Endpoint 8: Analytics - Transboundary Corridor Index
# -------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_analytics_transboundary(app):
    """GET /api/v1/analytics/transboundary returns 120km border normal mass balance."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/analytics/transboundary?pollutant=PM2.5")
        assert response.status_code == 200
        data = response.json()

        assert data["pollutant"] == "PM2.5"
        assert "inflow_total" in data
        assert "outflow_total" in data
        assert "net_transboundary_flux" in data
        assert "status" in data
        assert "border_samples" in data
        assert len(data["border_samples"]) == 39  # Exactly 39 boundary normal nodes


# -------------------------------------------------------------------------
# Endpoint 9: CSV Ingestion Pipeline & Dead-Letter Quarantine
# -------------------------------------------------------------------------

@pytest.mark.anyio
async def test_post_ingest_valid_csv(app):
    """POST /api/v1/ingest/csv ingests valid station observations fixture with 100% success."""
    fixture_path = FIXTURES_DIR / "valid_station_observations.csv"
    with open(fixture_path, "rb") as f:
        file_bytes = f.read()

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        files = {"file": ("valid_station_observations.csv", file_bytes, "text/csv")}
        response = await client.post("/api/v1/ingest/csv", files=files)
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["filename"] == "valid_station_observations.csv"
        assert data["total_rows"] == 15
        assert data["valid_rows"] == 15
        assert data["quarantined_rows"] == 0
        assert data["merged_observations_count"] > 0
        assert len(data["errors"]) == 0


@pytest.mark.anyio
async def test_post_ingest_quarantine_csv(app):
    """POST /api/v1/ingest/csv quarantines invalid/out-of-bounds rows without crashing."""
    fixture_path = FIXTURES_DIR / "invalid_out_of_bounds.csv"
    with open(fixture_path, "rb") as f:
        file_bytes = f.read()

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        files = {"file": ("invalid_out_of_bounds.csv", file_bytes, "text/csv")}
        response = await client.post("/api/v1/ingest/csv", files=files)
        assert response.status_code == 200
        data = response.json()

        assert data["quarantined_rows"] > 0
        assert len(data["quarantine_records"]) == data["quarantined_rows"]

        first_q = data["quarantine_records"][0]
        assert "row_number" in first_q
        assert "error_type" in first_q
        assert "error_message" in first_q
        assert "raw_record" in first_q


@pytest.mark.anyio
async def test_post_ingest_invalid_file_extension(app):
    """POST /api/v1/ingest/csv rejects non-CSV files with 400 Bad Request."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        files = {"file": ("dataset.txt", b"some text content", "text/plain")}
        response = await client.post("/api/v1/ingest/csv", files=files)
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]


@pytest.mark.anyio
async def test_post_ingest_empty_file(app):
    """POST /api/v1/ingest/csv rejects empty files with 400 Bad Request."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        files = {"file": ("empty.csv", b"", "text/csv")}
        response = await client.post("/api/v1/ingest/csv", files=files)
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()


# -------------------------------------------------------------------------
# Endpoint 10: Server-Sent Events (SSE) Live Feed
# -------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_stream_live_initial_frame(app):
    """GET /api/v1/stream/live should connect as text/event-stream and yield hourly_update frame."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/stream/live?max_events=1")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        text = response.text
        assert "event: hourly_update" in text
        assert "data: {" in text
