"""
Automated Integration Test Suite for Milestone M5: Component-Driven UI/UX Dashboard.
Verifies FastAPI frontend static mounting, SPA delivery at GET /, HTML 5-zone structure,
9 statutory pollutants, offline baseline data bundles, and physical invariant guards.
"""
from pathlib import Path
import json
import re
import pytest
import httpx
from httpx import ASGITransport

from src.api.main import create_application

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = PROJECT_ROOT / "src" / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"


@pytest.fixture(scope="module")
def app():
    """Create and initialize FastAPI application for test suite."""
    return create_application()


@pytest.fixture
def anyio_backend():
    """Specify anyio backend engine."""
    return "asyncio"


# -----------------------------------------------------------------------------
# 1. FastAPI Root Delivery & Static Asset Endpoints
# -----------------------------------------------------------------------------

@pytest.mark.anyio
async def test_frontend_root_endpoint_serves_html(app):
    """GET / and GET /index.html should return HTTP 200 with index.html."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Test Root /
        response = await client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert "Punjab Air Quality" in response.text
        assert "<!DOCTYPE html>" in response.text or "<!doctype html>" in response.text

        # Test Explicit /index.html
        resp_index = await client.get("/index.html")
        assert resp_index.status_code == 200
        assert resp_index.text == response.text


@pytest.mark.anyio
async def test_frontend_static_assets_delivery(app):
    """Static assets (CSS, JS, GeoJSON) under /static/ must be accessible with HTTP 200."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # CSS Tokens
        css_resp = await client.get("/static/css/tokens.css")
        assert css_resp.status_code == 200
        assert "--bg-canvas" in css_resp.text
        assert "--pepc-good" in css_resp.text

        # Core JS Modules
        for js_module in ["app.js", "canvas.js", "geo.js", "api.js", "ui.js"]:
            js_resp = await client.get(f"/static/js/{js_module}")
            assert js_resp.status_code == 200, f"Failed to retrieve /static/js/{js_module}"
            assert len(js_resp.text) > 100

        # Geo Boundaries JSON
        geo_resp = await client.get("/static/data/geo_boundaries.json")
        assert geo_resp.status_code == 200
        geo_data = geo_resp.json()
        assert "GEO" in geo_data
        assert "IND" in geo_data


# -----------------------------------------------------------------------------
# 2. HTML Structure & 5-Zone UI Hierarchy Verification
# -----------------------------------------------------------------------------

def test_frontend_html_contains_five_zones():
    """Verify that dashboard.html contains all 5 mandatory functional zones and required IDs."""
    html_path = FRONTEND_DIR / "dashboard.html"
    if not html_path.exists():
        html_path = FRONTEND_DIR / "index.html"
    assert html_path.exists(), "Frontend HTML entrypoint does not exist"

    content = html_path.read_text(encoding="utf-8")

    # Zone 1: Command Header & Navigation Strip
    assert 'role="banner"' in content or 'zone-1-header' in content
    assert 'id="liveSyncBadge"' in content
    assert 'id="liveSyncText"' in content
    assert 'id="provincialAqiBadge"' in content
    assert 'id="clockReadout"' in content
    assert 'id="themeToggleBtn"' in content
    assert 'id="csvUploadBtn"' in content
    assert 'id="csvModal"' in content
    assert 'data-view="console"' in content
    assert 'data-view="lahore"' in content
    assert 'data-view="heatmap"' in content
    assert 'data-view="transboundary"' in content
    assert 'data-view="grid"' in content

    # Zone 2: Primary Pollutant Switcher
    assert 'id="pollutantStrip"' in content
    assert 'role="radiogroup"' in content

    # Zone 3: Geographic Map Viewport Console
    assert 'id="mainMapCanvas"' in content
    assert 'id="hudDate"' in content
    assert 'id="hudTime"' in content
    assert 'id="hudPollutant"' in content
    assert 'id="legendTitle"' in content
    assert 'id="legendColorBar"' in content
    assert 'id="legendTicks"' in content
    assert 'id="playBtn"' in content
    assert 'id="scrubRange"' in content
    assert 'id="speedSelect"' in content
    assert 'name="mapMode"' in content
    assert 'id="toggleTransportLinks"' in content
    assert 'id="toggleRegionalWinds"' in content

    # Zone 4: Real-Time Telemetry Sidebar
    assert 'id="kpiMeanVal"' in content
    assert 'id="kpiExceedVal"' in content
    assert 'id="kpiPeakVal"' in content
    assert 'id="sparklineCanvas"' in content
    assert 'id="airportTableBody"' in content
    assert 'id="districtRankedList"' in content
    assert 'id="selectedDistrictTitle"' in content
    assert 'id="selectedDistrictTableBody"' in content
    assert 'id="districtSelectDropdown"' in content
    assert 'id="roseCanvas"' in content

    # Zone 5: Deep-Dive Panels
    assert 'id="panel-grid"' in content
    assert 'id="miniGridContainer"' in content
    assert 'id="panel-lahore"' in content
    assert 'id="lahoreMapCanvas"' in content
    assert 'id="lahoreTableBody"' in content
    assert 'id="panel-heatmap"' in content
    assert 'id="heatmapContainer"' in content
    assert 'id="heatmapTable"' in content
    assert 'id="panel-transboundary"' in content


# -----------------------------------------------------------------------------
# 3. Statutory Pollutants & Regulatory Standards Verification
# -----------------------------------------------------------------------------

def test_statutory_pollutants_and_peqs_definitions():
    """Verify that all 9 statutory species and regulatory limits are configured."""
    canvas_js = (STATIC_DIR / "js" / "canvas.js").read_text(encoding="utf-8")

    expected_species = ["AQI", "PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "NO", "NOx"]
    for species in expected_species:
        assert f"'{species}'" in canvas_js or f'"{species}"' in canvas_js or f"{species}:" in canvas_js, \
            f"Species {species} missing from canvas.js"

    # Verify PEQS statutory limits
    assert "ref: 35" in canvas_js   # PM2.5 24-h limit 35 µg/m³
    assert "ref: 150" in canvas_js  # PM10 24-h limit 150 µg/m³
    assert "ref: 80" in canvas_js   # NO2 24-h limit 80 µg/m³
    assert "ref: 120" in canvas_js  # SO2 24-h limit 120 µg/m³
    assert "ref: 5" in canvas_js    # CO 8-h limit 5 mg/m³
    assert "ref: 130" in canvas_js  # O3 1-h limit 130 µg/m³
    assert "ref: 40" in canvas_js   # NO limit 40 µg/m³

    # Verify PEPC 7-stop palette colors
    tokens_css = (STATIC_DIR / "css" / "tokens.css").read_text(encoding="utf-8")
    expected_pepc_stops = [
        "#2d7f5e",  # Good
        "#6aa84f",  # Moderate
        "#d49a3d",  # Unhealthy for Sensitive
        "#c94a29",  # Unhealthy
        "#7a325d",  # Very Unhealthy
        "#4a154b",  # Hazardous
        "#2a0845",  # Emergency / Extreme
    ]
    for stop in expected_pepc_stops:
        assert stop in tokens_css, f"PEPC color stop {stop} missing from tokens.css"


# -----------------------------------------------------------------------------
# 4. Design System & WCAG Atmospheric Tokens Verification
# -----------------------------------------------------------------------------

def test_atmospheric_theme_tokens():
    """Verify dual-mode dark/light atmospheric tokens and typography rules."""
    tokens_css = (STATIC_DIR / "css" / "tokens.css").read_text(encoding="utf-8")

    # Dark Theme Tokens
    assert "#0f1716" in tokens_css  # --bg-canvas
    assert "#152120" in tokens_css  # --bg-panel
    assert "#e3ece9" in tokens_css  # --ink-primary
    assert "#93a39e" in tokens_css  # --ink-secondary
    assert "#2a3a38" in tokens_css  # --border-subtle

    # Light Theme Tokens
    assert "#eef1ef" in tokens_css  # Light bg-canvas
    assert "#fbfcfb" in tokens_css  # Light bg-panel
    assert "#17221f" in tokens_css  # Light ink-primary
    assert "#5b6964" in tokens_css  # Light ink-secondary
    assert "#d3dad7" in tokens_css  # Light border-subtle

    # Required Typography
    assert "Barlow Condensed" in tokens_css
    assert "Source Sans 3" in tokens_css
    assert "JetBrains Mono" in tokens_css
    assert "tabular-nums" in tokens_css


# -----------------------------------------------------------------------------
# 5. Offline Fallback Data Bundles & Integrity
# -----------------------------------------------------------------------------

def test_offline_fallback_data_integrity():
    """Verify that all baseline fallback data bundles exist and match domain schema."""
    data_dir = STATIC_DIR / "data"

    # 1. Geo Boundaries
    geo_file = data_dir / "geo_boundaries.json"
    assert geo_file.exists(), "geo_boundaries.json does not exist in static/data"
    geo_data = json.loads(geo_file.read_text(encoding="utf-8"))
    assert "GEO" in geo_data
    assert "Punjab" in geo_data["GEO"]
    assert "Sind" in geo_data["GEO"]
    assert "IND" in geo_data
    assert len(geo_data["IND"]) >= 10

    # 2. Districts Catalog
    districts_file = data_dir / "districts.json"
    assert districts_file.exists()
    districts = json.loads(districts_file.read_text(encoding="utf-8"))
    assert len(districts) == 41, f"Expected 41 districts, got {len(districts)}"
    district_names = [d["name"] for d in districts]
    assert "Lahore" in district_names
    assert "Faisalabad" in district_names
    assert "Rawalpindi" in district_names

    # 3. Stations Catalog
    stations_file = data_dir / "stations.json"
    assert stations_file.exists()
    stations = json.loads(stations_file.read_text(encoding="utf-8"))
    assert len(stations) >= 70

    # 4. Airports Catalog
    airports_file = data_dir / "airports.json"
    assert airports_file.exists()
    airports = json.loads(airports_file.read_text(encoding="utf-8"))
    assert len(airports) >= 5

    # 5. Baseline 216-Hour Data
    baseline_file = data_dir / "baseline_data.json"
    assert baseline_file.exists()
    baseline = json.loads(baseline_file.read_text(encoding="utf-8"))
    assert len(baseline["hours"]) == 216
    assert "tbgeo" in baseline
    assert len(baseline["tbgeo"]["samples"]) == 39  # 39 border normal nodes
    assert len(baseline["tbgeo"]["border"]) == 440   # 440 international border coordinates


# -----------------------------------------------------------------------------
# 6. Physical Invariant Guard (AQI Mass Flux Blocking)
# -----------------------------------------------------------------------------

@pytest.mark.anyio
async def test_physical_invariant_aqi_flux_rejected(app):
    """GET /api/v1/analytics/flux?pollutant=AQI must be rejected with HTTP 400."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        resp = await client.get("/api/v1/analytics/flux?pollutant=AQI")
        assert resp.status_code == 400
        data = resp.json()
        assert "dimensionless ordinal index" in data.get("detail", "").lower()

    # Also check client-side api.js invariant guard
    api_js = (STATIC_DIR / "js" / "api.js").read_text(encoding="utf-8")
    assert "Physical Invariant Guard" in api_js
    assert "pollutant === 'AQI'" in api_js


# -----------------------------------------------------------------------------
# 7. 3x3 Grid District Zoom & Identification Verification
# -----------------------------------------------------------------------------

def test_grid_district_zoom_interaction():
    """Verify that 3x3 multi-pollutant grid includes district zoom, banner, and click logic."""
    html = (FRONTEND_DIR / "dashboard.html").read_text(encoding="utf-8")
    assert 'id="gridZoomBanner"' in html
    assert 'id="gridResetZoomBtn"' in html
    assert 'id="gridZoomDistrictName"' in html

    app_js = (STATIC_DIR / "js" / "app.js").read_text(encoding="utf-8")
    assert "computeDistrictBounds" in app_js
    assert "getGridActiveViewport" in app_js
    assert "toggleGridDistrictZoom" in app_js
    assert "hitTestMiniDistrict" in app_js
    assert "gridZoomDistrict" in app_js

    tokens_css = (STATIC_DIR / "css" / "tokens.css").read_text(encoding="utf-8")
    assert ".grid-zoom-banner" in tokens_css
    assert ".grid-reset-zoom-btn" in tokens_css

