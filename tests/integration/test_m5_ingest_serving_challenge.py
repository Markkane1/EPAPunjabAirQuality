"""
Empirical Challenger Test Suite for Milestone M5: Ingestion & Serving Integration
Validates:
1. CSVIngestModal contract and Quarantine Table DOM element #csvQuarantineArea
2. Backend CSV ingestion multipart validation, error rejection, and quarantine logging
3. Airshed re-interpolation hook triggering on merged observations
4. Static assets and workstation delivery in src/api/main.py (/assets, /static, /)
"""
from pathlib import Path
import pytest
import httpx
from httpx import ASGITransport

from src.api.main import create_application

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
DIST_ASSETS = DIST_DIR / "assets"
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"
SRC_MODAL = PROJECT_ROOT / "src" / "components" / "command" / "CSVIngestModal.tsx"
COMMAND_BAR = PROJECT_ROOT / "src" / "components" / "command" / "CommandBar.tsx"


@pytest.fixture(scope="module")
def app():
    return create_application()


@pytest.fixture
def anyio_backend():
    return "asyncio"


# =============================================================================
# 1. SERVING INTEGRATION IN src/api/main.py
# =============================================================================

@pytest.mark.anyio
async def test_fastapi_serves_dist_workstation_at_root(app):
    """
    Verify src/api/main.py serves dist/workstation.html at GET / and GET /index.html with HTTP 200.
    """
    assert DIST_DIR.exists(), "dist/ directory must exist"
    dist_html = DIST_DIR / "workstation.html"
    assert dist_html.exists(), "dist/workstation.html must exist"
    expected_content = dist_html.read_text(encoding="utf-8")

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # 1. GET /
        resp_root = await client.get("/")
        assert resp_root.status_code == 200, f"Expected 200 for GET /, got {resp_root.status_code}"
        assert "text/html" in resp_root.headers.get("content-type", "")
        assert resp_root.text == expected_content, "GET / must serve dist/workstation.html verbatim"

        # 2. GET /index.html
        resp_index = await client.get("/index.html")
        assert resp_index.status_code == 200
        assert "text/html" in resp_index.headers.get("content-type", "")
        assert resp_index.text == expected_content, "GET /index.html must match GET /"


@pytest.mark.anyio
async def test_fastapi_mounts_compiled_assets_under_assets_path(app):
    """
    Verify src/api/main.py mounts dist/assets at /assets with HTTP 200.
    """
    assert DIST_ASSETS.exists(), "dist/assets directory must exist"
    asset_files = [f for f in DIST_ASSETS.iterdir() if f.is_file()]
    assert len(asset_files) > 0, "dist/assets must contain emitted bundle chunks"

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        for asset in asset_files:
            if asset.suffix in [".js", ".css"]:
                resp = await client.get(f"/assets/{asset.name}")
                assert resp.status_code == 200, f"Failed to retrieve /assets/{asset.name}: {resp.status_code}"
                assert len(resp.content) > 0


@pytest.mark.anyio
async def test_fastapi_preserves_static_mount(app):
    """
    Verify /static mount is preserved for legacy test fixtures and backwards compatibility.
    """
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        for legacy_asset in ["api.js", "tokens.css", "canvas.js"]:
            sub = "css" if legacy_asset.endswith(".css") else "js"
            resp = await client.get(f"/static/{sub}/{legacy_asset}")
            assert resp.status_code == 200, f"Legacy asset /static/{sub}/{legacy_asset} missing: {resp.status_code}"


# =============================================================================
# 2. CSVIngestModal CONTRACT & DOM INSPECTION
# =============================================================================

def test_csv_ingest_modal_component_contract():
    """
    Direct code inspection of CSVIngestModal.tsx:
    1. Contains #csvQuarantineArea element
    2. Validates .csv file extension
    3. Validates non-zero file size (selected.size === 0)
    4. Renders quarantine inspection table with Row, Station ID, Error Code, Error Message
    5. Calls onSuccessMerged hook when valid_rows > 0 and status !== 'failed'
    """
    modal_src = SRC_MODAL.read_text(encoding="utf-8")

    assert 'id="csvQuarantineArea"' in modal_src, "CSVIngestModal must render #csvQuarantineArea container"
    assert "endsWith('.csv')" in modal_src, "CSVIngestModal must enforce .csv file extension"
    assert "selected.size === 0" in modal_src, "CSVIngestModal must reject 0-byte empty files"

    # Quarantine table columns
    assert "<th className=\"p-2 border-r border-border\">Row</th>" in modal_src or "Row" in modal_src
    assert "Station ID" in modal_src
    assert "Error Code" in modal_src
    assert "Error Message" in modal_src

    # Re-interpolation hook contract
    assert "onSuccessMerged" in modal_src
    assert "res.valid_rows > 0 && res.status !== 'failed'" in modal_src


# =============================================================================
# 3. CSV BACKEND INGESTION & AIRSHED RE-INTERPOLATION
# =============================================================================

@pytest.mark.anyio
async def test_backend_csv_ingestion_and_quarantine_flow(app):
    """
    Simulate full ingestion lifecycle:
    1. Ingest valid CSV -> valid_rows > 0, merged_observations_count > 0
    2. Ingest invalid CSV -> status: failed, quarantined_rows > 0, quarantined_records list
    """
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Case 1: Valid CSV using fixture
        valid_file = FIXTURES_DIR / "valid_station_observations.csv"
        files = {"file": (valid_file.name, valid_file.read_bytes(), "text/csv")}
        resp = await client.post("/api/v1/ingest/csv", files=files, data={"allow_missing_coords": "true"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ["success", "partial_quarantine"]
        assert data["valid_rows"] == 15
        assert data["quarantined_rows"] == 0
        assert data["merged_observations_count"] == 14

        # Case 2: Out-of-bounds quarantine CSV using fixture
        bad_file = FIXTURES_DIR / "invalid_out_of_bounds.csv"
        bad_files = {"file": (bad_file.name, bad_file.read_bytes(), "text/csv")}
        resp_bad = await client.post("/api/v1/ingest/csv", files=bad_files, data={"allow_missing_coords": "false"})
        assert resp_bad.status_code == 200
        bad_data = resp_bad.json()
        assert bad_data["status"] == "failed"
        assert bad_data["valid_rows"] == 0
        assert bad_data["quarantined_rows"] == 6
        assert len(bad_data["quarantined_records"]) == 6
        assert bad_data["quarantined_records"][0]["error_type"] == "COORDINATES_MISSING_OR_UNRESOLVABLE"
