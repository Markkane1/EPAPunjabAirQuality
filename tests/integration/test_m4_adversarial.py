"""
Adversarial Challenge Integration Test Suite for Milestone M4: Core Backend Services & API Gateway.

Focus Areas:
1. Adversarial Route Fuzzing & Boundary Conditions (out-of-bounds, non-existent, future, negative, malformed).
2. Physical AQI Guard Verification on Advection Flux (case-insensitivity, physical justification).
3. CSV Ingestion Security & Dead-Letter Quarantine (SQL injection, directory traversal, corrupt rows, DLQ isolation, dynamic catalog updates).
4. Concurrent Repository Stress (simultaneous async reads during dynamic CSV write mutations under threading.RLock).
5. SSE Stream Boundary Stress (bounded event limits, malformed stream query parameters).
"""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
import httpx
from httpx import ASGITransport

from src.api.main import create_application

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="module")
def app():
    """Create and initialize FastAPI application for test suite."""
    return create_application()


@pytest.fixture
def anyio_backend():
    """Specify anyio backend engine."""
    return "asyncio"


# =========================================================================
# 1. PHYSICAL AQI GUARD TESTS
# =========================================================================

class TestPhysicalAQIGuard:
    """
    Verifies that the physical AQI guard strictly prevents advection mass flux
    calculations for the dimensionless ordinal AQI index, in compliance with
    mass conservation laws and PEPC standards.
    """

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "aqi_variant",
        ["AQI", "aqi", "Aqi", " aqi ", "AQI ", " aQi "],
    )
    async def test_flux_aqi_guard_case_insensitivity(self, app, aqi_variant):
        """GET /api/v1/analytics/flux?pollutant=<aqi> MUST return HTTP 400 Bad Request."""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get(f"/api/v1/analytics/flux?pollutant={aqi_variant}")
            assert response.status_code == 400, f"Expected HTTP 400 for '{aqi_variant}', got {response.status_code}"
            data = response.json()
            assert "detail" in data
            detail_lower = data["detail"].lower()
            assert "physically undefined" in detail_lower or "mass conservation" in detail_lower
            assert "dimensionless ordinal index" in detail_lower or "aqi" in detail_lower

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "mass_pollutant",
        ["PM2.5", "pm2.5", "PM10", "pm10", "NO2", "SO2", "CO", "O3"],
    )
    async def test_flux_valid_mass_pollutants_admitted(self, app, mass_pollutant):
        """GET /api/v1/analytics/flux accepts conserved physical mass species."""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get(f"/api/v1/analytics/flux?pollutant={mass_pollutant}")
            assert response.status_code == 200, f"Expected HTTP 200 for physical mass pollutant '{mass_pollutant}', got {response.status_code}"
            data = response.json()
            assert "top_pathways" in data
            assert "net_balance" in data


# =========================================================================
# 2. ADVERSARIAL ROUTE FUZZING & BOUNDARY CONDITIONS
# =========================================================================

class TestAdversarialRouteFuzzing:
    """
    Fuzzes all endpoints with boundary conditions, malformed parameters,
    non-existent entities, future dates, negative timestamps, and injection strings.
    Verifies clean HTTP 400 or 422 responses without unhandled 500 exceptions.
    """

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "url,expected_status",
        [
            # Spatial Surface Resolution Boundaries & Fuzzing (ge=1, le=50)
            ("/api/v1/spatial/surface?resolution=-10", 422),
            ("/api/v1/spatial/surface?resolution=0", 422),
            ("/api/v1/spatial/surface?resolution=51", 422),
            ("/api/v1/spatial/surface?resolution=99999", 422),
            ("/api/v1/spatial/surface?resolution=not_an_int", 422),
            ("/api/v1/spatial/surface?resolution=3.1415", 422),
            # Spatial Surface Timestamp Boundaries
            ("/api/v1/spatial/surface?timestamp=not_a_valid_date", 422),
            ("/api/v1/spatial/surface?timestamp=2099-01-01T00:00:00Z", 200),  # Future date -> empty/fallback grid
            # Advection Flux Limit Boundaries (ge=1, le=200)
            ("/api/v1/analytics/flux?limit=0", 422),
            ("/api/v1/analytics/flux?limit=-5", 422),
            ("/api/v1/analytics/flux?limit=201", 422),
            ("/api/v1/analytics/flux?limit=1000", 422),
            ("/api/v1/analytics/flux?limit=invalid_num", 422),
            ("/api/v1/analytics/flux?timestamp=corrupt_timestamp", 422),
            ("/api/v1/analytics/flux?timestamp=2099-01-01T00:00:00Z", 200),  # Future date -> empty pathways
            # Analytics CPF Fuzzing & Boundaries
            ("/api/v1/analytics/cpf", 422),  # Missing required district parameter
            ("/api/v1/analytics/cpf?district=NonExistentDistrictXYZ999", 400),  # Unknown district
            ("/api/v1/analytics/cpf?district=%27%20OR%201=1%20--", 400),  # SQLi attempt rejected cleanly
            ("/api/v1/analytics/cpf?district=Lahore&threshold=not_a_float", 422),
            # Transboundary Mass Balance Fuzzing
            ("/api/v1/analytics/transboundary?timestamp=invalid_timestamp", 422),
            ("/api/v1/analytics/transboundary?timestamp=2099-01-01T00:00:00Z", 200),  # Future date -> 0 flux
            # Observations Hourly Series Fuzzing
            ("/api/v1/observations/hourly?start_time=invalid_format", 422),
            ("/api/v1/observations/hourly?end_time=invalid_format", 422),
            ("/api/v1/observations/hourly?start_time=2099-01-01T00:00:00Z", 200),  # Future date -> 0 hours
            ("/api/v1/observations/hourly?start_time=2026-11-11T00:00:00Z&end_time=2020-01-01T00:00:00Z", 200),  # Inverted range -> 0 hours
            # Metadata Filter Fuzzing
            ("/api/v1/meta/districts?monitored_only=not_a_bool", 422),
            ("/api/v1/meta/stations?district=NonExistentDistrictXYZ", 200),  # Clean empty list
            ("/api/v1/meta/stations?district=%27%20OR%201=1%20--", 200),  # SQLi string -> clean empty list
            ("/api/v1/meta/stations?station_type=../../etc/passwd", 200),  # Path traversal string -> clean empty list
            # Current Observation Fuzzing
            ("/api/v1/observations/current?district=NonExistentDistrictXYZ", 200),  # Clean empty district map
            ("/api/v1/observations/current?pollutant=UNKNOWN_NOBLE_GAS", 200),  # Unmonitored pollutant -> clean snapshot
            # SSE Stream max_events fuzzing
            ("/api/v1/stream/live?max_events=not_an_int", 422),
        ],
    )
    async def test_endpoint_adversarial_parameter_fuzzing(self, app, url, expected_status):
        """Verifies endpoint returns expected status (400, 422, or 200) and NEVER raises an unhandled 500 error."""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get(url)
            assert response.status_code == expected_status, (
                f"URL '{url}' returned status {response.status_code}, expected {expected_status}. "
                f"Response body: {response.text[:200]}"
            )
            assert response.status_code != 500, f"Critical failure: unhandled 500 Internal Server Error on '{url}'"

    @pytest.mark.anyio
    async def test_spatial_surface_future_date_fallback(self, app):
        """Future timestamp on /api/v1/spatial/surface gracefully falls back to zero raster matrix."""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/api/v1/spatial/surface?timestamp=2099-01-01T00:00:00Z&resolution=10")
            assert response.status_code == 200
            data = response.json()
            assert data["min_val"] == 0.0
            assert data["max_val"] == 0.0
            assert all(all(val == 0.0 for val in row) for row in data["grid_matrix"])

    @pytest.mark.anyio
    async def test_hourly_series_inverted_range_returns_empty_series(self, app):
        """Inverted time range (start > end) on /api/v1/observations/hourly returns 0 hours without crashing."""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get(
                "/api/v1/observations/hourly?start_time=2026-11-10T12:00:00Z&end_time=2026-11-01T12:00:00Z"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["total_hours"] == 0
            assert len(data["hours"]) == 0


# =========================================================================
# 3. CSV INGESTION SECURITY, DEAD-LETTER QUARANTINE & CATALOG UPDATES
# =========================================================================

class TestCSVIngestionSecurityAndDLQ:
    """
    Stress-tests the CSV ingestion pipeline with corrupted data, SQL injection strings,
    directory traversal file payloads, out-of-bounds GPS coordinates, and ragged rows.
    Verifies valid rows are admitted, invalid rows are quarantined in DLQ, and newly
    registered stations appear in the station metadata registry.
    """

    @pytest.mark.anyio
    async def test_ingest_rejects_non_csv_extension(self, app):
        """POST /api/v1/ingest/csv rejects non-csv files with HTTP 400."""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            files = {"file": ("malicious_payload.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/octet-stream")}
            response = await client.post("/api/v1/ingest/csv", files=files)
            assert response.status_code == 400
            assert "Invalid file type" in response.json()["detail"]

    @pytest.mark.anyio
    async def test_ingest_rejects_empty_csv(self, app):
        """POST /api/v1/ingest/csv rejects zero-byte files with HTTP 400."""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            files = {"file": ("empty.csv", b"", "text/csv")}
            response = await client.post("/api/v1/ingest/csv", files=files)
            assert response.status_code == 400
            assert "empty" in response.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_ingest_adversarial_rows_dlq_isolation_and_station_registration(self, app):
        """
        Submits a multi-row CSV payload containing:
        - 1 valid new station in Lahore (should be admitted and registered)
        - 1 valid new station with SQL injection attempt in name (should be treated safely as plain text)
        - 1 valid new station with directory traversal attempt in name (should be treated safely as plain text)
        - 1 row with non-numeric value (should be quarantined as VALIDATION_ERROR)
        - 1 row with out-of-bounds latitude/longitude 999.0, -500.0 (should be quarantined)
        - 1 row with negative wind speed -15.0 m/s (should be quarantined as VALIDATION_ERROR)
        - 1 row with ragged columns (should be quarantined)
        - 1 row with unphysical value > 5000.0 (should be quarantined as VALIDATION_ERROR)
        """
        adversarial_csv = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value,wind_speed,wind_direction\n"
            "2026-11-10 12:00,ADV_ST_001,Valid Challenger Station,Lahore,31.5204,74.3587,PM2.5,42.5,2.1,180.0\n"
            "2026-11-10 12:00,ADV_ST_SQLI,Station'; DROP TABLE stations; --,Faisalabad,31.4504,73.1350,PM2.5,55.0,1.5,90.0\n"
            "2026-11-10 12:00,ADV_ST_TRAV,../../../../etc/passwd,Multan,30.1575,71.5249,PM2.5,60.0,1.0,45.0\n"
            "2026-11-10 12:00,ADV_ST_CORRUPT,Corrupt Float Value,Lahore,31.5204,74.3587,PM2.5,NOT_A_FLOAT_VAL,2.5,180.0\n"
            "2026-11-10 12:00,ADV_ST_OOB,Out of Bounds Coords,Lahore,999.0,-500.0,PM2.5,45.2,2.5,180.0\n"
            "2026-11-10 12:00,ADV_ST_NEGWIND,Negative Wind Speed,Lahore,31.5204,74.3587,PM2.5,45.2,-15.0,180.0\n"
            "2026-11-10 12:00,ADV_ST_RAGGED,Ragged Truncated Row,Lahore\n"
            "2026-11-10 12:00,ADV_ST_CAP,Extreme Unphysical Value,Lahore,31.5204,74.3587,PM2.5,99999.0,2.5,180.0\n"
        )

        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            files = {"file": ("adversarial_test.csv", adversarial_csv.encode("utf-8"), "text/csv")}
            response = await client.post("/api/v1/ingest/csv", files=files)
            assert response.status_code == 200, f"CSV ingestion failed: {response.text}"
            data = response.json()

            # Verify status and row partition counts
            assert data["status"] == "partial_quarantine"
            assert data["total_rows"] == 8
            assert data["valid_rows"] == 3  # ADV_ST_001, ADV_ST_SQLI, ADV_ST_TRAV
            assert data["quarantined_rows"] == 5  # Corrupt, OOB, NegWind, Ragged, Cap

            # Verify Dead-Letter Quarantine structure
            dlq = data["quarantine_records"]
            assert len(dlq) == 5
            error_types = {q["error_type"] for q in dlq}
            assert "VALIDATION_ERROR" in error_types or "COORDINATES_MISSING_OR_UNRESOLVABLE" in error_types

            # Verify that newly ingested valid stations appear in metadata directory
            meta_resp = await client.get("/api/v1/meta/stations")
            assert meta_resp.status_code == 200
            stations = meta_resp.json()

            stn_001 = next((s for s in stations if s["id"] == "ADV_ST_001"), None)
            assert stn_001 is not None, "Station ADV_ST_001 was not dynamically registered in station metadata."
            assert stn_001["name"] == "Valid Challenger Station"
            assert stn_001["district"] == "Lahore"
            assert stn_001["station_type"] == "user_csv"

            stn_sqli = next((s for s in stations if s["id"] == "ADV_ST_SQLI"), None)
            assert stn_sqli is not None, "Station ADV_ST_SQLI was not registered safely as plain text."
            assert "DROP TABLE" in stn_sqli["name"]

            stn_trav = next((s for s in stations if s["id"] == "ADV_ST_TRAV"), None)
            assert stn_trav is not None, "Station ADV_ST_TRAV was not registered safely as plain text."
            assert "/etc/passwd" in stn_trav["name"]


# =========================================================================
# 4. CONCURRENT REPOSITORY STRESS UNDER THREADING.RLOCK
# =========================================================================

class TestConcurrentRepositoryOperations:
    """
    Simulates high concurrency under threading.RLock(): executes simultaneous read
    queries across observation, spatial surface, flux analytics, and station metadata
    while concurrently uploading dynamic CSV ingestion mutations.
    """

    @pytest.mark.anyio
    async def test_concurrent_reads_and_dynamic_csv_mutations(self, app):
        """
        Executes 40 concurrent operations:
        - 8 simultaneous calls to GET /api/v1/observations/current
        - 8 simultaneous calls to GET /api/v1/spatial/surface?resolution=20
        - 8 simultaneous calls to GET /api/v1/analytics/flux?pollutant=PM2.5
        - 8 simultaneous calls to GET /api/v1/meta/stations
        - 8 simultaneous calls to POST /api/v1/ingest/csv with dynamic station insertions
        Verifies 100% success rate without deadlocks, corrupted state, or 500 errors.
        """
        csv_template = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value,wind_speed,wind_direction\n"
            "2026-11-10 12:00,CONC_ST_{idx},Concurrent Station {idx},Rawalpindi,33.5651,73.0169,PM2.5,38.0,2.0,180.0\n"
        )

        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            async def read_observations():
                res = await client.get("/api/v1/observations/current")
                assert res.status_code == 200
                return res.status_code

            async def read_spatial():
                res = await client.get("/api/v1/spatial/surface?resolution=20")
                assert res.status_code == 200
                return res.status_code

            async def read_flux():
                res = await client.get("/api/v1/analytics/flux?pollutant=PM2.5")
                assert res.status_code == 200
                return res.status_code

            async def read_meta():
                res = await client.get("/api/v1/meta/stations")
                assert res.status_code == 200
                return res.status_code

            async def dynamic_ingest(idx: int):
                csv_bytes = csv_template.format(idx=idx).encode("utf-8")
                files = {"file": (f"conc_{idx}.csv", csv_bytes, "text/csv")}
                res = await client.post("/api/v1/ingest/csv", files=files)
                assert res.status_code == 200
                return res.status_code

            tasks = []
            for i in range(8):
                tasks.append(read_observations())
                tasks.append(read_spatial())
                tasks.append(read_flux())
                tasks.append(read_meta())
                tasks.append(dynamic_ingest(i))

            results = await asyncio.gather(*tasks)
            assert len(results) == 40
            assert all(status == 200 for status in results), f"Concurrent request failures detected: {results}"

            # Verify that all 8 dynamic stations were safely registered in the station catalog
            meta_resp = await client.get("/api/v1/meta/stations")
            assert meta_resp.status_code == 200
            stations = meta_resp.json()
            for i in range(8):
                stn_id = f"CONC_ST_{i}"
                assert any(s["id"] == stn_id for s in stations), f"Missing concurrent station '{stn_id}' from catalog."


# =========================================================================
# 5. SSE STREAM LIVE BOUNDARY BEHAVIOR
# =========================================================================

class TestSSEStreamLiveBoundary:
    """Verifies Server-Sent Events stream boundaries and parameter handling."""

    @pytest.mark.anyio
    async def test_stream_live_bounded_events(self, app):
        """GET /api/v1/stream/live?max_events=1 returns 1 frame and cleanly terminates."""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/api/v1/stream/live?max_events=1")
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")
            lines = response.text.strip().split("\n")
            assert any("event: hourly_update" in line for line in lines)
            assert any("data: {" in line for line in lines)

    @pytest.mark.anyio
    async def test_stream_live_max_events_zero(self, app):
        """GET /api/v1/stream/live?max_events=0 terminates immediately without hanging."""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/api/v1/stream/live?max_events=0")
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")
