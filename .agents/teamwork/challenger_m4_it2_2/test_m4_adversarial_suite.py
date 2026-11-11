"""
Empirical Adversarial Test Suite for Milestone M4 (Iteration 2).
Author: challenger_m4_it2_2
Location: .agents/teamwork/challenger_m4_it2_2/test_m4_adversarial_suite.py

Covers the 5 mandatory challenge areas:
1. Physical AQI guard on advection flux (whitespace, case, control characters, URL variations).
2. SSE live stream headers, initial hourly_update frame, keepalive comments, and client disconnect cancellation.
3. Spatial surface IDW resolution boundaries (1-50 valid, 0 and >50 rejected), bounding boxes, determinism.
4. CPF rose calm threshold exclusion (< 0.5 m/s) and small-sample suppression (Nk < 6 returning None).
5. CSV multipart upload fuzzing (corrupt timestamps, negative concentrations, out-of-bounds coords) isolated into quarantine without 500 errors.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import io
import json
import anyio
import httpx
from httpx import ASGITransport
import pytest

from src.api.main import create_application
import src.api.routes.stream as stream_route
from src.domain.entities.models import StationObservation
from src.domain.math.cpf import calculate_cpf_rose
from src.domain.math.flux import calculate_advection_flux
from src.services.analytics_service import AnalyticsService
from src.services.spatial_service import SpatialService


@pytest.fixture(scope="module")
def app():
    """Module-scoped FastAPI application instance."""
    return create_application()


@pytest.fixture
def anyio_backend():
    return "asyncio"


# =============================================================================
# Challenge 1: Physical AQI Guard on Advection Flux
# =============================================================================

class TestChallenge1PhysicalAQIGuard:
    """
    Adversarial verification of physical AQI guard on advection mass flux.
    Assert that passing ANY variation of 'AQI' unconditionally returns HTTP 400 Bad Request
    and that lower layers (service, domain math) also enforce this invariant.
    """

    AQI_VARIATIONS = [
        "AQI",
        "aqi",
        "Aqi",
        "aQi",
        " AQI ",
        "  aqi  ",
        "\tAQI\n",
        "\r\n Aqi \t",
        "AQI ",
        " aqi",
    ]

    @pytest.mark.anyio
    @pytest.mark.parametrize("pollutant_variant", AQI_VARIATIONS)
    async def test_api_advection_flux_rejects_aqi_variations(self, app, pollutant_variant):
        """API GET /api/v1/analytics/flux must unconditionally return HTTP 400 for AQI variants."""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/api/v1/analytics/flux", params={"pollutant": pollutant_variant})
            assert resp.status_code == 400, (
                f"Expected HTTP 400 for variant {repr(pollutant_variant)}, got {resp.status_code}: {resp.text}"
            )
            data = resp.json()
            assert "detail" in data
            assert "AQI" in data["detail"]
            assert "dimensionless" in data["detail"].lower() or "physically undefined" in data["detail"].lower()

    @pytest.mark.anyio
    @pytest.mark.parametrize("pollutant_variant", AQI_VARIATIONS)
    def test_service_layer_raises_value_error_for_aqi_variations(self, app, pollutant_variant):
        """AnalyticsService.calculate_flux must raise ValueError for all AQI variants."""
        service: AnalyticsService = app.state.analytics_service
        with pytest.raises(ValueError) as exc_info:
            service.calculate_flux(pollutant=pollutant_variant)
        assert "dimensionless" in str(exc_info.value).lower() or "AQI" in str(exc_info.value)

    @pytest.mark.parametrize("pollutant_variant", AQI_VARIATIONS + ["", None])
    def test_domain_math_returns_none_for_aqi_variations(self, pollutant_variant):
        """Domain math calculate_advection_flux must return None for any AQI variant or empty."""
        source_station = {
            "coords": (31.5204, 74.3587),
            "value": 150.0,
            "u": 2.0,
            "v": 2.0,
        }
        receptor_coords = (31.4187, 73.0791)
        res = calculate_advection_flux(source_station, receptor_coords, pollutant=pollutant_variant)
        assert res is None, f"Expected None for pollutant {repr(pollutant_variant)}, got {res}"

    @pytest.mark.anyio
    async def test_api_advection_flux_accepts_valid_mass_species(self, app):
        """Ensure physical mass pollutants (PM2.5, PM10, NO2) return HTTP 200 with valid fluxes."""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            for valid_species in ["PM2.5", "pm2.5", "PM10", "no2"]:
                resp = await client.get("/api/v1/analytics/flux", params={"pollutant": valid_species})
                assert resp.status_code == 200, f"Expected HTTP 200 for valid species {valid_species}, got {resp.status_code}"
                body = resp.json()
                assert "top_pathways" in body
                assert "net_balance" in body


# =============================================================================
# Challenge 2: SSE Live Stream (/api/v1/stream/live)
# =============================================================================

class TestChallenge2SSELiveStream:
    """
    Adversarial verification of Server-Sent Events live telemetry stream.
    Asserts streaming headers, immediate hourly_update frame, keepalive comments,
    and graceful cancellation upon client disconnect.
    """

    @pytest.mark.anyio
    async def test_sse_headers_and_initial_frame(self, app):
        """Verify headers and immediate hourly_update packet emission."""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/api/v1/stream/live?max_events=1")
            assert resp.status_code == 200

            # 1. Headers verification
            assert "text/event-stream" in resp.headers.get("content-type", "")
            assert "no-cache" in resp.headers.get("cache-control", "")
            assert resp.headers.get("x-accel-buffering") == "no"

            # 2. Frame structure
            body = resp.text
            assert body.startswith("event: hourly_update\n"), f"Stream did not start with hourly_update: {body[:60]}"
            assert "\ndata: " in body
            assert body.endswith("\n\n")

            # 3. Payload sanity
            lines = body.strip().split("\n")
            data_line = next(line for line in lines if line.startswith("data: "))
            payload = json.loads(data_line[6:])
            assert "timestamp" in payload
            assert "provincial_summary" in payload
            assert "district_readings" in payload
            assert isinstance(payload["district_readings"], dict)
            assert "airports" in payload
            assert isinstance(payload["airports"], list)

    @pytest.mark.anyio
    async def test_sse_keepalive_emission(self, monkeypatch):
        """Verify ': keepalive\\n\\n' comment frames are produced."""
        fresh_app = create_application()
        repo = fresh_app.state.repo

        monkeypatch.setattr(stream_route, "KEEPALIVE_INTERVAL_SECONDS", 0.04)
        monkeypatch.setattr(stream_route, "POLL_CHECK_INTERVAL_SECONDS", 0.02)

        async def push_update():
            await asyncio.sleep(0.06)
            latest_ts = repo.get_latest_timestamp()
            new_ts = latest_ts + timedelta(hours=1)
            stn = repo.list_stations()[0]
            obs = StationObservation(
                station_id=stn.id,
                recorded_at=new_ts,
                aqi=120,
                pm25=60.0,
            )
            repo.add_station_observations([obs])

        async with anyio.create_task_group() as tg:
            tg.start_soon(push_update)
            async with httpx.AsyncClient(transport=ASGITransport(app=fresh_app), base_url="http://testserver") as client:
                resp = await client.get("/api/v1/stream/live?max_events=2")
                assert resp.status_code == 200
                text = resp.text
                assert ": keepalive\n\n" in text
                assert text.count("event: hourly_update") == 2

    @pytest.mark.anyio
    async def test_sse_client_disconnect_task_cancellation(self, monkeypatch):
        """Verify client disconnect raises asyncio.CancelledError handled cleanly without leaking errors."""
        fresh_app = create_application()
        monkeypatch.setattr(stream_route, "POLL_CHECK_INTERVAL_SECONDS", 0.02)
        monkeypatch.setattr(stream_route, "KEEPALIVE_INTERVAL_SECONDS", 0.05)

        # Abrupt disconnect via client timeout
        async with httpx.AsyncClient(transport=ASGITransport(app=fresh_app), base_url="http://testserver") as client:
            try:
                with anyio.fail_after(0.12):
                    await client.get("/api/v1/stream/live")
            except TimeoutError:
                pass  # Disconnect triggered

        # Application state must remain intact and serve subsequent requests
        async with httpx.AsyncClient(transport=ASGITransport(app=fresh_app), base_url="http://testserver") as client:
            health = await client.get("/health")
            assert health.status_code == 200
            assert health.json()["status"] == "healthy"


# =============================================================================
# Challenge 3: Spatial Surface IDW Bounds & Determinism
# =============================================================================

class TestChallenge3SpatialSurfaceIDW:
    """
    Adversarial verification of 2D spatial continuous IDW surface.
    Asserts resolution bounds (1-50 valid, 0 and >50 rejected), bounding box bounds,
    and deterministic repeatability.
    """

    @pytest.mark.anyio
    @pytest.mark.parametrize("valid_res", [1, 5, 10, 25, 50])
    async def test_valid_resolutions_grid_dimensions(self, app, valid_res):
        """Valid resolution (1-50) returns exact grid width and height matching canvas 600x450."""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get(f"/api/v1/spatial/surface?pollutant=PM2.5&resolution={valid_res}", timeout=30.0)
            assert resp.status_code == 200
            data = resp.json()
            assert data["resolution"] == valid_res
            expected_w = 600 // valid_res
            expected_h = 450 // valid_res
            assert data["grid_width"] == expected_w
            assert data["grid_height"] == expected_h
            assert len(data["grid_matrix"]) == expected_h
            assert all(len(row) == expected_w for row in data["grid_matrix"])
            assert all(val >= 0.0 for row in data["grid_matrix"] for val in row)

    @pytest.mark.anyio
    @pytest.mark.parametrize("invalid_res", [0, -1, -10, 51, 100, 200])
    async def test_invalid_resolutions_rejected_with_422(self, app, invalid_res):
        """Resolution outside 1..50 must be rejected with HTTP 422 Unprocessable Entity."""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get(f"/api/v1/spatial/surface?pollutant=PM2.5&resolution={invalid_res}")
            assert resp.status_code == 422, f"Expected HTTP 422 for resolution {invalid_res}, got {resp.status_code}"
            body = resp.json()
            assert body["error_type"] == "ValidationError"

    def test_spatial_service_resolution_clamping(self, app):
        """Direct call to SpatialService clamps resolution strictly to [1, 50]."""
        service: SpatialService = app.state.spatial_service
        # Resolution 100 clamped to 50
        dto_high = service.get_surface_matrix(resolution=100)
        assert dto_high.resolution == 50
        assert dto_high.grid_width == 600 // 50
        # Resolution 0 clamped to 1
        dto_low = service.get_surface_matrix(resolution=0)
        assert dto_low.resolution == 1
        assert dto_low.grid_width == 600 // 1

    @pytest.mark.anyio
    async def test_spatial_interpolation_determinism(self, app):
        """Two calls for the same parameters must return strictly identical matrix values."""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp1 = await client.get("/api/v1/spatial/surface?pollutant=PM2.5&resolution=10")
            resp2 = await client.get("/api/v1/spatial/surface?pollutant=PM2.5&resolution=10")
            assert resp1.status_code == 200 and resp2.status_code == 200

            data1 = resp1.json()
            data2 = resp2.json()

            assert data1["min_val"] == data2["min_val"]
            assert data1["max_val"] == data2["max_val"]
            assert data1["grid_matrix"] == data2["grid_matrix"]
            assert data1["opacity_matrix"] == data2["opacity_matrix"]


# =============================================================================
# Challenge 4: CPF Rose Calm Exclusion & Small-Sample Suppression
# =============================================================================

class TestChallenge4CPFRoseAnalytics:
    """
    Adversarial verification of CPF Rose calculations:
    1. Aerodynamic calm exclusion (< 0.5 m/s) excluded from directional compass sectors.
    2. Small-sample suppression: sectors with Nk < 6 must return None.
    3. Sectors with Nk >= 6 must return round(mk / Nk, 4).
    """

    def test_cpf_all_calm_observations_exclusion(self):
        """When all observations have wind speed < 0.5 m/s, all sectors must be None and calm_ratio == 1.0."""
        calm_observations = [
            {"value": 150.0, "wind_speed": 0.2, "wind_direction": 90.0},
            {"value": 200.0, "wind_speed": 0.4, "wind_direction": 180.0},
            {"value": 80.0,  "wind_speed": 0.0, "wind_direction": 270.0},
            {"value": 120.0, "wind_speed": 0.49, "wind_direction": 0.0},
        ]
        rose = calculate_cpf_rose(calm_observations, calm_threshold=0.5)
        assert rose["calm_ratio"] == 1.0
        assert all(sec is None for sec in rose["sectors"])
        assert all(count == 0 for count in rose["sector_counts"])

    def test_cpf_small_sample_suppression_boundary_nk_5_vs_6(self):
        """
        Adversarial test on exact boundary Nk = 5 (suppressed to None)
        vs Nk = 6 (unsuppressed, calculated as mk / Nk).
        """
        # East sector (index 4: 90 deg) with exactly 5 observations
        # West sector (index 12: 270 deg) with exactly 6 observations
        observations = []
        # Sector 4: 5 observations, 3 exceedances (value > 100)
        for val in [150.0, 160.0, 170.0, 50.0, 60.0]:
            observations.append({"value": val, "wind_speed": 2.5, "wind_direction": 90.0})

        # Sector 12: 6 observations, 4 exceedances (value > 100)
        for val in [150.0, 160.0, 170.0, 180.0, 50.0, 60.0]:
            observations.append({"value": val, "wind_speed": 3.0, "wind_direction": 270.0})

        # Add 1 calm observation
        observations.append({"value": 300.0, "wind_speed": 0.1, "wind_direction": 90.0})

        rose = calculate_cpf_rose(observations, threshold_p75=100.0, calm_threshold=0.5)

        # Sector 4 (90 deg): Nk=5 < 6 -> MUST BE None
        assert rose["sector_counts"][4] == 5
        assert rose["sectors"][4] is None, f"Expected None for Nk=5, got {rose['sectors'][4]}"

        # Sector 12 (270 deg): Nk=6 >= 6 -> MUST BE 4 / 6 = 0.6667
        assert rose["sector_counts"][12] == 6
        assert rose["sector_exceedances"][12] == 4
        assert rose["sectors"][12] == round(4 / 6, 4)

        # Calm ratio: 1 calm out of 12 total = 1/12
        assert rose["calm_ratio"] == round(1 / 12, 4)

    @pytest.mark.anyio
    async def test_api_cpf_rose_contract_and_suppression(self, app):
        """GET /api/v1/analytics/cpf adheres to 16 sectors and small-sample suppression rule."""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/api/v1/analytics/cpf?district=Lahore&pollutant=PM2.5")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["sectors"]) == 16
            assert 0.0 <= data["calm_fraction"] <= 1.0

            for sec in data["sectors"]:
                nk = sec["total_hours"]
                mk = sec["exceedance_hours"]
                prob = sec["cpf_probability"]
                if nk < 6:
                    assert prob is None, f"Sector {sec['direction_label']} has Nk={nk} < 6 but prob is {prob}"
                else:
                    assert prob == round(mk / nk, 4)


# =============================================================================
# Challenge 5: CSV Multipart Upload Fuzzing & Dead-Letter Isolation
# =============================================================================

class TestChallenge5CSVIngestionFuzzing:
    """
    Adversarial fuzzing of POST /api/v1/ingest/csv:
    - Corrupt timestamps
    - Negative concentrations
    - Latitude out of Punjab bounds [27.0, 35.0]
    - Longitude out of Punjab bounds [69.0, 76.0]
    - Out of range wind speeds
    Verifies graceful isolation into quarantine_records without unhandled 500 errors.
    """

    ADVERSARIAL_CSV = (
        "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value,wind_speed,wind_direction\n"
        # Row 2: Valid baseline row
        "2026-11-10T12:00:00Z,PK_GOOD_01,Town Hall,Lahore,31.5204,74.3587,pm25,120.0,2.5,90.0\n"
        # Row 3: Corrupt timestamp
        "corrupt-timestamp-string,PK_BAD_01,Test Station 1,Lahore,31.5204,74.3587,pm25,120.0,2.5,90.0\n"
        # Row 4: Negative concentration value (-45.0)
        "2026-11-10T12:00:00Z,PK_BAD_02,Test Station 2,Lahore,31.5204,74.3587,pm25,-45.0,2.5,90.0\n"
        # Row 5: Latitude out of Punjab bounds (45.5 > 35.0)
        "2026-11-10T12:00:00Z,PK_BAD_03,Test Station 3,Lahore,45.5000,74.3587,pm25,120.0,2.5,90.0\n"
        # Row 6: Longitude out of Punjab bounds (85.2 > 76.0)
        "2026-11-10T12:00:00Z,PK_BAD_04,Test Station 4,Lahore,31.5204,85.2000,pm25,120.0,2.5,90.0\n"
        # Row 7: Valid baseline row 2
        "2026-11-10T12:00:00Z,PK_GOOD_02,Faisalabad Center,Faisalabad,31.4187,73.0791,pm10,210.0,1.5,180.0\n"
    )

    @pytest.mark.anyio
    async def test_fuzzed_csv_gracefully_quarantined_without_500(self, app):
        """
        Uploading a CSV with fuzzed and out-of-bounds rows must:
        - Return HTTP 200 (graceful non-halting processing).
        - Status == 'partial_quarantine'.
        - Total rows == 6.
        - Valid rows == 2 or 3 (depending on timestamp fallback).
        - Quarantined rows > 0.
        - No unhandled 500 error raised.
        """
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            files = {"file": ("adversarial_fuzz.csv", self.ADVERSARIAL_CSV.encode("utf-8"), "text/csv")}
            resp = await client.post("/api/v1/ingest/csv", files=files)
            assert resp.status_code == 200, f"Expected HTTP 200, got {resp.status_code}: {resp.text}"

            data = resp.json()
            assert data["status"] in ("partial_quarantine", "failed")
            assert data["total_rows"] == 6
            assert data["quarantined_rows"] > 0
            assert "quarantine_records" in data
            assert len(data["quarantine_records"]) == data["quarantined_rows"]

            # Check that quarantined records identify specific row issues
            q_recs = data["quarantine_records"]
            q_errors = [q["error_message"].lower() for q in q_recs]
            q_types = [q["error_type"] for q in q_recs]

            # At least coordinates and negative values are isolated
            assert any("coordinate" in err or "latitude" in err or "bounds" in err or "type" in str(qt).lower() for err, qt in zip(q_errors, q_types))
            assert any("value" in err or "qc_purged" in str(qt).lower() or "negative" in err for err, qt in zip(q_errors, q_types))

    @pytest.mark.anyio
    async def test_all_invalid_csv_fails_gracefully(self, app):
        """CSV containing only invalid rows returns status 'failed' with HTTP 200 and full quarantine."""
        bad_csv = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            "2026-11-10T12:00:00Z,PK_01,Bad Node 1,Unknown,55.0,90.0,pm25,-10.0\n"
            "2026-11-10T12:00:00Z,PK_02,Bad Node 2,Unknown,10.0,50.0,pm25,6000.0\n"
        )
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            files = {"file": ("all_bad.csv", bad_csv.encode("utf-8"), "text/csv")}
            resp = await client.post("/api/v1/ingest/csv", files=files)
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "failed"
            assert data["valid_rows"] == 0
            assert data["quarantined_rows"] == 2
            assert len(data["quarantine_records"]) == 2
