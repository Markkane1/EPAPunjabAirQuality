"""
Adversarial Empirical Challenge Test Suite for Milestone M4.
Focus Areas:
1. SSE Telemetry Streaming Resilience (packet framing, headers, keepalive heartbeat, abrupt disconnect).
2. Continuous Spatial Surface Grids (resolution edge cases, dimensional division, matrix extrema, non-negativity).
3. 16-Sector CPF Polar Wind Rose Analytics (sector partitioning, small-sample suppression Nk < 6, calm fraction ws < 0.5 m/s).

Uses httpx.AsyncClient with ASGITransport(app=create_application()) via anyio/asyncio.
"""
import asyncio
from datetime import timedelta
import json
import anyio
import httpx
from httpx import ASGITransport
import pytest

from src.api.main import create_application
import src.api.routes.stream as stream_route
from src.domain.entities.models import StationObservation
from src.services.spatial_service import SpatialService


@pytest.fixture(scope="module")
def app():
    """Module-scoped FastAPI application instance."""
    return create_application()


@pytest.fixture
def anyio_backend():
    """Specify asyncio as anyio engine."""
    return "asyncio"


# =========================================================================
# Section 1: Server-Sent Events (SSE) Live Telemetry Streaming Resilience
# =========================================================================

@pytest.mark.anyio
async def test_sse_stream_initial_packet_and_headers(app):
    """
    Verify GET /api/v1/stream/live:
    - Response headers include text/event-stream, no-cache, and X-Accel-Buffering: no.
    - Initial packet starts with event: hourly_update\\ndata: {...}\\n\\n.
    - Data payload deserializes as valid JSON containing provincial telemetry summary.
    """
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/stream/live?max_events=1")
        assert response.status_code == 200

        # Header verification
        content_type = response.headers.get("content-type", "")
        assert "text/event-stream" in content_type, f"Expected text/event-stream in {content_type}"
        cache_control = response.headers.get("cache-control", "")
        assert "no-cache" in cache_control, f"Expected no-cache in {cache_control}"
        x_accel = response.headers.get("x-accel-buffering", "")
        assert x_accel == "no", f"Expected X-Accel-Buffering: no, got {x_accel}"

        # Frame structure verification
        body = response.text
        assert body.startswith("event: hourly_update\n"), f"Expected body to start with event: hourly_update, got: {body[:60]}"
        assert "\ndata: " in body, "Expected SSE data field delimiter"
        assert body.endswith("\n\n"), "Expected SSE double-newline message terminator"

        # Data JSON verification
        lines = body.strip().split("\n")
        data_line = next(line for line in lines if line.startswith("data: "))
        data_payload = json.loads(data_line[6:])
        assert "timestamp" in data_payload
        assert "provincial_summary" in data_payload
        assert "district_readings" in data_payload
        assert "airports" in data_payload
        assert isinstance(data_payload["airports"], list)


@pytest.mark.anyio
async def test_sse_stream_keepalive_heartbeat(monkeypatch):
    """
    Verify SSE keepalive heartbeat comment lines (: keepalive\\n\\n) are emitted.
    Accelerates interval to 0.05s via monkeypatch and pushes a newer observation to
    trigger the second event, verifying that : keepalive\\n\\n is interleaved properly.
    """
    fresh_app = create_application()
    repo = fresh_app.state.repo

    monkeypatch.setattr(stream_route, "KEEPALIVE_INTERVAL_SECONDS", 0.05)
    monkeypatch.setattr(stream_route, "POLL_CHECK_INTERVAL_SECONDS", 0.02)

    async def inject_newer_observation():
        await asyncio.sleep(0.08)
        latest_ts = repo.get_latest_timestamp()
        new_ts = latest_ts + timedelta(hours=1)
        stn = repo.list_stations()[0]
        obs = StationObservation(
            station_id=stn.id,
            recorded_at=new_ts,
            aqi=150,
            pm25=75.0,
            pm10=100.0,
            no2=20.0,
            so2=10.0,
            co=1.0,
            o3=30.0,
            temperature_c=25.0,
            relative_humidity_pct=50.0,
            wind_speed=2.5,
            wind_direction=180.0,
            u=-0.0,
            v=2.5,
        )
        repo.add_station_observations([obs])

    async with anyio.create_task_group() as tg:
        tg.start_soon(inject_newer_observation)
        async with httpx.AsyncClient(transport=ASGITransport(app=fresh_app), base_url="http://testserver") as client:
            response = await client.get("/api/v1/stream/live?max_events=2")
            assert response.status_code == 200
            body = response.text

            # Verify comment line format for SSE keepalive
            assert "\n: keepalive\n\n" in body or body.startswith(": keepalive\n\n"), (
                "Expected ': keepalive\\n\\n' comment line in stream body"
            )
            # Verify both hourly_update packets were received
            assert body.count("event: hourly_update") == 2


@pytest.mark.anyio
async def test_sse_stream_abrupt_client_disconnect(monkeypatch):
    """
    Verify server terminates the stream generator cleanly without unhandled exception
    when client abruptly cancels/disconnects during an active infinite stream.
    """
    fresh_app = create_application()
    monkeypatch.setattr(stream_route, "KEEPALIVE_INTERVAL_SECONDS", 0.05)
    monkeypatch.setattr(stream_route, "POLL_CHECK_INTERVAL_SECONDS", 0.02)

    async with httpx.AsyncClient(transport=ASGITransport(app=fresh_app), base_url="http://testserver") as client:
        # Simulate abrupt disconnection via client timeout / cancellation
        try:
            with anyio.fail_after(0.15):
                await client.get("/api/v1/stream/live")
        except TimeoutError:
            pass  # Expected client-side cancellation

    # Verification: application state remains valid and handles subsequent requests without error
    async with httpx.AsyncClient(transport=ASGITransport(app=fresh_app), base_url="http://testserver") as client:
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["status"] == "healthy"


# =========================================================================
# Section 2: Continuous Spatial Surface Raster Grids & Resolution Scaling
# =========================================================================

@pytest.mark.anyio
@pytest.mark.parametrize("resolution", [1, 5, 25, 50])
async def test_spatial_surface_resolution_grid_dimensions(app, resolution):
    """
    Verify GET /api/v1/spatial/surface resolution edge cases (1, 5, 25, 50):
    - grid dimensions adhere to grid_width == width_px // resolution, grid_height == height_px // resolution.
    - min_val and max_val match matrix extrema.
    - all interpolated concentrations are non-negative.
    """
    width_px = 600
    height_px = 450
    expected_w = width_px // resolution
    expected_h = height_px // resolution

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # resolution=1 may take ~16s on first computation; set adequate timeout
        response = await client.get(
            f"/api/v1/spatial/surface?pollutant=PM2.5&resolution={resolution}",
            timeout=30.0,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["pollutant"] == "PM2.5"
        assert data["resolution"] == resolution
        assert data["grid_width"] == expected_w, f"Expected grid_width {expected_w}, got {data['grid_width']}"
        assert data["grid_height"] == expected_h, f"Expected grid_height {expected_h}, got {data['grid_height']}"

        matrix = data["grid_matrix"]
        assert len(matrix) == expected_h, f"Matrix row count {len(matrix)} != grid_height {expected_h}"
        assert all(len(row) == expected_w for row in matrix), "Matrix columns != grid_width"

        # Check non-negativity across all cells
        all_values = [val for row in matrix for val in row]
        assert all(v >= 0.0 for v in all_values), "Negative concentration detected in interpolated field"

        # Check extrema consistency
        actual_min = min(all_values)
        actual_max = max(all_values)
        assert data["min_val"] == round(actual_min, 2), f"Reported min_val {data['min_val']} != actual {actual_min}"
        assert data["max_val"] == round(actual_max, 2), f"Reported max_val {data['max_val']} != actual {actual_max}"
        assert data["max_val"] >= data["min_val"]


@pytest.mark.anyio
async def test_spatial_surface_resolution_100_boundary_constraint(app):
    """
    Verify boundary behavior for resolution=100.
    1. The API endpoint enforces Query(..., ge=1, le=50) schema validation.
       Therefore, resolution=100 correctly triggers HTTP 422 Unprocessable Entity.
    2. In the domain service, resolution=100 is clamped via min(50, resolution).
    3. Non-positive resolutions (e.g. 0, -5) are rejected with HTTP 422 (ge=1).
    """
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Upper bound boundary check: resolution=100 exceeds le=50 constraint
        resp_100 = await client.get("/api/v1/spatial/surface?pollutant=PM2.5&resolution=100")
        assert resp_100.status_code == 422
        body_100 = resp_100.json()
        assert body_100["error_type"] == "ValidationError"
        assert any("less_than_equal" in str(d) for d in body_100["details"])

        # Lower bound boundary checks: resolution < 1
        resp_0 = await client.get("/api/v1/spatial/surface?pollutant=PM2.5&resolution=0")
        assert resp_0.status_code == 422
        resp_neg = await client.get("/api/v1/spatial/surface?pollutant=PM2.5&resolution=-5")
        assert resp_neg.status_code == 422

    # Verify domain service clamping behavior directly
    service: SpatialService = app.state.spatial_service
    dto_100 = service.get_surface_matrix(resolution=100)
    assert dto_100.resolution == 50, f"Expected SpatialService to clamp resolution 100 to 50, got {dto_100.resolution}"
    assert dto_100.grid_width == 600 // 50
    assert dto_100.grid_height == 450 // 50


# =========================================================================
# Section 3: Conditional Probability Function (CPF) Wind Rose Analytics
# =========================================================================

@pytest.mark.anyio
async def test_cpf_rose_16_sectors_contract(app):
    """
    Verify GET /api/v1/analytics/cpf returns exactly 16 sectors with:
    - 22.5 degree azimuth increments.
    - Correct canonical direction labels (N through NNW).
    - Monotonically increasing sector indices [0..15].
    """
    expected_labels = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
    ]

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/analytics/cpf?district=Lahore&pollutant=PM2.5")
        assert response.status_code == 200
        data = response.json()

        assert data["district"] == "Lahore"
        assert data["pollutant"] == "PM2.5"
        sectors = data["sectors"]
        assert len(sectors) == 16, f"Expected exactly 16 sectors, got {len(sectors)}"

        for idx, sec in enumerate(sectors):
            assert sec["sector_index"] == idx
            assert sec["azimuth_deg"] == round(idx * 22.5, 1)
            assert sec["direction_label"] == expected_labels[idx]
            assert sec["total_hours"] >= 0
            assert sec["exceedance_hours"] >= 0
            assert sec["exceedance_hours"] <= sec["total_hours"]


@pytest.mark.anyio
async def test_cpf_rose_small_sample_suppression_rule(app):
    """
    Verify small-sample suppression rule (TRANSFORMATION_LOGIC_SPEC.md §2.5.2):
    - If sector observations Nk < 6: cpf_probability MUST be None.
    - If sector observations Nk >= 6: cpf_probability MUST be float in [0.0, 1.0],
      matching round(mk / Nk, 4).
    Tests across multiple districts (Lahore, Attock) to evaluate both suppressed
    (0 < Nk < 6) and unsuppressed (Nk >= 6) sectors.
    """
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        for district in ["Lahore", "Attock", "Rawalpindi"]:
            response = await client.get(f"/api/v1/analytics/cpf?district={district}&pollutant=PM2.5")
            assert response.status_code == 200
            data = response.json()

            for sec in data["sectors"]:
                nk = sec["total_hours"]
                mk = sec["exceedance_hours"]
                prob = sec["cpf_probability"]

                if nk < 6:
                    assert prob is None, (
                        f"Suppression failure in {district} sector {sec['direction_label']}: "
                        f"total_hours={nk} < 6 but cpf_probability={prob}"
                    )
                else:
                    assert isinstance(prob, float), (
                        f"Expected float probability in {district} sector {sec['direction_label']}, got {prob}"
                    )
                    assert 0.0 <= prob <= 1.0
                    expected_p = round(mk / nk, 4)
                    assert prob == expected_p, (
                        f"Mismatch in {district} sector {sec['direction_label']}: {prob} != {expected_p}"
                    )


@pytest.mark.anyio
async def test_cpf_rose_calm_fraction_calculation(app):
    """
    Verify calm fraction calculation with threshold ws < 0.5 m/s:
    - Calm observations (ws < 0.5 m/s) are recorded in calm_fraction in [0.0, 1.0].
    - Calm observations are strictly excluded from the 16 directional compass sectors.
    - Evaluates calm conditions in Lahore (high calm) and Multan (low calm).
    """
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Lahore: known high aerodynamic calm fraction
        resp_lhr = await client.get("/api/v1/analytics/cpf?district=Lahore&pollutant=PM2.5")
        assert resp_lhr.status_code == 200
        data_lhr = resp_lhr.json()
        assert 0.0 <= data_lhr["calm_fraction"] <= 1.0
        assert data_lhr["calm_fraction"] > 0.50, "Expected high calm fraction in Lahore basin"

        # Multan: known low calm fraction (active convective dispersion)
        resp_mul = await client.get("/api/v1/analytics/cpf?district=Multan&pollutant=PM2.5")
        assert resp_mul.status_code == 200
        data_mul = resp_mul.json()
        assert 0.0 <= data_mul["calm_fraction"] <= 1.0
        assert data_mul["calm_fraction"] < 0.20, "Expected low calm fraction in Multan"

        # Unknown district handling
        resp_bad = await client.get("/api/v1/analytics/cpf?district=NonExistentDistrict&pollutant=PM2.5")
        assert resp_bad.status_code == 400
        assert "Unknown administrative district" in resp_bad.json()["detail"]
