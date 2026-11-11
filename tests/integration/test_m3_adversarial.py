"""
Comprehensive Adversarial Challenge & Stress Verification Harness for Milestone M3.
Covers:
1. FallbackTemplateEngine under simulated network outage, missing files, corrupt baseline files, and malformed responses.
2. UserCSVIngestionAdapter stress testing:
   - UTF-8 BOM, UTF-16, Latin-1, malformed CSV delimiters, partial lines.
   - Malformed fields, strings with SQL injection, path traversal, excessive lengths in station names.
   - Non-halting quarantine Dead-Letter Queue (DLQ): verify invalid rows produce QuarantineRecord with correct error details, but valid rows continue processing without failing the batch.
   - Negative pollutant concentrations, extreme values (>1000/1500 tagged as QC_EXCEEDANCE_EXTREME, >5000 quarantined as unphysical).
   - Geographic boundary enforcement (latitude in [27.0, 35.0], longitude in [69.0, 76.0]).
   - OneNetwork Station 25 exclusion (must be unconditionally excluded/quarantined).
   - Canonical coordinate repair for the 8 corrupted registry stations.
3. BaseIngestionWorker circuit breaker:
   - Trip after exactly 5 consecutive failures.
   - Verify cooldown of 900 seconds (15 min) where requests fail fast without hitting external endpoints.
   - Verify transition to HALF-OPEN after cooldown, and recovery to healthy on successful execution.
"""
import asyncio
from datetime import datetime, timezone, timedelta
import io
import json
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock
import httpx
import pytest

from src.domain.schemas.measurement import RawStationMeasurement, NormalizedObservation
from src.domain.schemas.csv_schema import UserCSVRow
from src.pipelines.base import BaseIngestionWorker
from src.pipelines.fallback_engine import (
    FallbackTemplateEngine,
    CANONICAL_COORDINATES,
    EXCLUDED_STATIONS,
)
from src.pipelines.csv_adapter import (
    UserCSVIngestionAdapter,
    CSVIngestionResult,
    QuarantineRecord,
)
from src.pipelines.epa_punjab import EPAPunjabIngestionWorker
from src.pipelines.metar import MetarIngestionWorker
from src.pipelines.synop import SynopIngestionWorker
from src.pipelines.open_meteo import OpenMeteoIngestionWorker


# ==============================================================================
# 1. FALLBACK TEMPLATE ENGINE ADVERSARIAL STRESS TESTS
# ==============================================================================

class TestFallbackTemplateEngineAdversarial:
    """Stress tests for FallbackTemplateEngine under corrupt, missing, or hostile conditions."""

    def test_fallback_missing_directory_raises_filenotfound(self):
        """Verify initialization fails explicitly with FileNotFoundError when directory does not exist."""
        with pytest.raises(FileNotFoundError):
            FallbackTemplateEngine(baseline_dir=Path("/nonexistent/baseline/dir/path/xyz"))

    def test_fallback_missing_individual_file_raises_filenotfound(self):
        """Verify initialization fails if any required baseline JSON file is missing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            # Create dummy stations.json, districts.json, airports.json, baseline_data.json
            # Omit districts.json intentionally
            (tmp_path / "stations.json").write_text("[]", encoding="utf-8")
            (tmp_path / "airports.json").write_text("[]", encoding="utf-8")
            (tmp_path / "baseline_data.json").write_text("{}", encoding="utf-8")

            with pytest.raises(FileNotFoundError):
                FallbackTemplateEngine(baseline_dir=tmp_path)

    def test_fallback_corrupt_baseline_json_raises_jsondecodeerror(self):
        """Verify initialization fails with JSONDecodeError when a baseline file contains corrupted JSON."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / "stations.json").write_text("{ unclosed invalid json syntax", encoding="utf-8")
            (tmp_path / "districts.json").write_text("[]", encoding="utf-8")
            (tmp_path / "airports.json").write_text("[]", encoding="utf-8")
            (tmp_path / "baseline_data.json").write_text("{}", encoding="utf-8")

            with pytest.raises(json.JSONDecodeError):
                FallbackTemplateEngine(baseline_dir=tmp_path)

    def test_fallback_unknown_identifiers_return_none_gracefully(self):
        """Verify unknown stations, districts, and airports return None safely without unhandled exceptions."""
        engine = FallbackTemplateEngine()

        assert engine.get_station("NONEXISTENT_STATION_XYZ") is None
        assert engine.get_district("NONEXISTENT_DISTRICT_XYZ") is None
        assert engine.get_airport("ZZZZ") is None

        assert engine.get_station_measurement_fallback("NONEXISTENT_STATION_XYZ") is None
        assert engine.get_district_observation_fallback("NONEXISTENT_DISTRICT_XYZ") is None
        assert engine.get_airport_metar_fallback("ZZZZ") is None

        # Check coordinate resolution for unknown or excluded stations
        assert engine.resolve_station_coords("9999", "Unknown Fake Station") is None
        assert engine.resolve_station_coords("onenetwork_25", "OneNetwork Station 25") is None

    def test_fallback_extreme_hour_indices_clamp_safely(self):
        """Verify extreme negative and positive hour indices are normalized into valid [0, 215] range."""
        engine = FallbackTemplateEngine()

        # Extreme negative index
        meas_neg = engine.get_station_measurement_fallback("Safari Park-LHR", hour_idx=-9999)
        assert meas_neg is not None
        assert isinstance(meas_neg, RawStationMeasurement)
        assert meas_neg.is_estimated is True

        # Extreme positive index
        meas_pos = engine.get_station_measurement_fallback("Safari Park-LHR", hour_idx=99999)
        assert meas_pos is not None
        assert isinstance(meas_pos, RawStationMeasurement)
        assert meas_pos.is_estimated is True

        # District fallback clamping
        dist_neg = engine.get_district_observation_fallback("Lahore", hour_idx=-500)
        assert dist_neg is not None
        assert dist_neg.is_estimated is True

        dist_pos = engine.get_district_observation_fallback("Lahore", hour_idx=5000)
        assert dist_pos is not None
        assert dist_pos.is_estimated is True

    def test_fallback_all_79_stations_conformance(self):
        """Verify fallback generation for all 79 stations produces schema-valid measurements with is_estimated=True."""
        engine = FallbackTemplateEngine()
        all_measurements = engine.get_all_station_measurements_fallback(hour_idx=0)

        assert len(all_measurements) == 79
        for meas in all_measurements:
            assert isinstance(meas, RawStationMeasurement)
            assert meas.is_estimated is True
            assert "FALLBACK_BASELINE_ESTIMATION" in meas.qc_flags
            assert meas.timestamp.tzinfo is not None

            # Verify upper physical bound
            if meas.pm25 is not None:
                assert 0.0 <= meas.pm25 <= 5000.0
                if meas.pm25 > 1000.0:
                    assert "QC_EXCEEDANCE_EXTREME" in meas.qc_flags
            if meas.pm10 is not None:
                assert 0.0 <= meas.pm10 <= 5000.0
                if meas.pm10 > 1500.0:
                    assert "QC_EXCEEDANCE_EXTREME" in meas.qc_flags

    def test_fallback_open_meteo_41_districts_conformance(self):
        """Verify Open-Meteo fallback produces 41 calibrated district centroids with K_R=0.22686."""
        engine = FallbackTemplateEngine()
        forecasts = engine.get_open_meteo_fallback(hour_idx=0)

        assert len(forecasts) == 41
        for f in forecasts:
            assert f["is_estimated"] is True
            assert f["source"] == "baseline_ecmwf"
            assert f["k_r"] == 0.22686
            assert "u_calibrated" in f
            assert "v_calibrated" in f
            assert "district" in f

    def test_fallback_synop_unmapped_wmo_station(self):
        """Verify get_synop_fallback handles unmapped WMO station IDs gracefully without crashing."""
        engine = FallbackTemplateEngine()
        res = engine.get_synop_fallback("99999", hour_idx=0)
        assert res["wmo_id"] == "99999"
        assert res["is_estimated"] is True
        assert res["source"] == "baseline_synop"
        assert "wind_speed_ms" in res
        assert "wind_direction_deg" in res


# ==============================================================================
# 2. WORKER NETWORK OUTAGE & MALFORMED RESPONSE TESTS
# ==============================================================================

class TestWorkerNetworkOutageAndMalformedResponses:
    """Stress tests simulating network outages, timeouts, and malformed JSON payloads across ingestion workers."""

    @pytest.mark.anyio
    async def test_epa_worker_network_outage_graceful_fallback(self):
        """EPA Punjab worker gracefully returns 79 baseline measurements on connection error."""
        worker = EPAPunjabIngestionWorker()
        # Mock fetch_data to raise ConnectError
        worker.fetch_data = AsyncMock(side_effect=httpx.ConnectError("Connection refused by aqi.punjab.gov.pk"))

        results = await worker.run()
        assert len(results) == 79
        assert all(isinstance(r, RawStationMeasurement) for r in results)
        assert all(r.is_estimated is True for r in results)
        assert worker.is_healthy is False
        assert worker.consecutive_failures == 1

    @pytest.mark.anyio
    async def test_epa_worker_malformed_json_response(self):
        """EPA Punjab worker gracefully returns fallback when portal returns unexpected or malformed payload."""
        worker = EPAPunjabIngestionWorker()
        worker.fetch_data = AsyncMock(return_value="<html>502 Bad Gateway</html>")

        results = await worker.run()
        assert len(results) == 79
        assert all(r.is_estimated is True for r in results)
        assert worker.is_healthy is False
        assert worker.consecutive_failures == 1

    @pytest.mark.anyio
    async def test_metar_worker_network_timeout_graceful_fallback(self):
        """METAR worker gracefully returns 12 aerodrome fallback records on network timeout."""
        worker = MetarIngestionWorker()
        worker.fetch_data = AsyncMock(side_effect=httpx.TimeoutException("Read timeout on aviationweather.gov"))

        results = await worker.run()
        assert len(results) == 12
        assert all(r["is_estimated"] is True for r in results)
        assert all(r["source"] == "baseline_airports" for r in results)
        assert worker.is_healthy is False

    @pytest.mark.anyio
    async def test_synop_worker_http_429_graceful_fallback(self):
        """SYNOP worker gracefully returns fallback observations on HTTP 429 Too Many Requests."""
        worker = SynopIngestionWorker()
        worker.fetch_data = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "HTTP 429 Too Many Requests from Ogimet",
                request=httpx.Request("GET", "https://www.ogimet.com"),
                response=httpx.Response(429),
            )
        )

        results = await worker.run()
        assert len(results) == 7  # 7 monitored WMO stations
        assert all(r["is_estimated"] is True for r in results)
        assert all(r["source"] == "baseline_synop" for r in results)
        assert worker.is_healthy is False

    @pytest.mark.anyio
    async def test_open_meteo_worker_server_error_graceful_fallback(self):
        """Open-Meteo worker gracefully returns 41 district centroid fallbacks on HTTP 500 error."""
        worker = OpenMeteoIngestionWorker()
        worker.fetch_data = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "HTTP 500 Server Error",
                request=httpx.Request("GET", "https://api.open-meteo.com"),
                response=httpx.Response(500),
            )
        )

        results = await worker.run()
        assert len(results) == 41
        assert all(r["is_estimated"] is True for r in results)
        assert all(r["source"] == "baseline_ecmwf" for r in results)
        assert worker.is_healthy is False


# ==============================================================================
# 3. BASE INGESTION WORKER CIRCUIT BREAKER STRESS TESTS
# ==============================================================================

class MockCircuitBreakerWorker(BaseIngestionWorker):
    """Subclass of BaseIngestionWorker for deterministic circuit breaker verification."""

    def __init__(self, max_failures: int = 5, cooldown_seconds: float = 900.0):
        super().__init__(
            stream_id="MOCK-CB-STREAM",
            name="Mock Circuit Breaker Worker",
            max_failures_before_circuit_break=max_failures,
            circuit_cooldown_seconds=cooldown_seconds,
        )
        self.fetch_calls = 0
        self.should_succeed = False

    async def fetch_data(self, **kwargs: Any) -> Any:
        self.fetch_calls += 1
        if not self.should_succeed:
            raise httpx.ConnectError("Endpoint unreachable")
        return {"data": [{"station_id": "TEST", "value": 42.0}]}

    def parse_and_validate(self, raw_data: Any) -> List[Any]:
        return raw_data["data"]

    def get_fallback(self, **kwargs: Any) -> List[Any]:
        return [{"fallback": True, "is_estimated": True}]


class TestBaseIngestionWorkerCircuitBreaker:
    """Rigorous empirical verification of circuit breaker state transitions."""

    @pytest.mark.anyio
    async def test_circuit_breaker_exact_trip_after_5_failures(self):
        """Circuit breaker MUST trip after exactly 5 consecutive failures, remaining CLOSED for 1-4."""
        worker = MockCircuitBreakerWorker(max_failures=5, cooldown_seconds=900.0)

        # Runs 1 to 4: consecutive_failures increments, circuit breaker remains CLOSED
        for i in range(1, 5):
            res = await worker.run()
            assert res == [{"fallback": True, "is_estimated": True}]
            assert worker.consecutive_failures == i
            assert worker.is_healthy is False
            assert worker.circuit_breaker_open is False
            assert worker.circuit_breaker_tripped_at is None
            assert worker.fetch_calls == i

        # Run 5: exactly trips circuit breaker to OPEN
        res5 = await worker.run()
        assert res5 == [{"fallback": True, "is_estimated": True}]
        assert worker.consecutive_failures == 5
        assert worker.circuit_breaker_open is True
        assert worker.circuit_breaker_tripped_at is not None
        assert worker.fetch_calls == 5

    @pytest.mark.anyio
    async def test_circuit_breaker_900s_cooldown_fail_fast(self):
        """During 900s cooldown, requests MUST fail fast directly to fallback WITHOUT calling fetch_data."""
        worker = MockCircuitBreakerWorker(max_failures=5, cooldown_seconds=900.0)

        # Trip the breaker
        for _ in range(5):
            await worker.run()
        assert worker.circuit_breaker_open is True
        assert worker.fetch_calls == 5

        # Check call at elapsed = 100s
        worker.circuit_breaker_tripped_at = datetime.now(timezone.utc) - timedelta(seconds=100)
        res_open_100 = await worker.run()
        assert res_open_100 == [{"fallback": True, "is_estimated": True}]
        assert worker.fetch_calls == 5  # fetch_data NOT called!
        assert worker.circuit_breaker_open is True

        # Check call at elapsed = 899s (still within cooldown)
        worker.circuit_breaker_tripped_at = datetime.now(timezone.utc) - timedelta(seconds=899)
        res_open_899 = await worker.run()
        assert res_open_899 == [{"fallback": True, "is_estimated": True}]
        assert worker.fetch_calls == 5  # fetch_data NOT called!
        assert worker.circuit_breaker_open is True

    @pytest.mark.anyio
    async def test_circuit_breaker_half_open_transition_and_recovery(self):
        """After cooldown (>900s), breaker transitions to HALF-OPEN and recovers on successful trial."""
        worker = MockCircuitBreakerWorker(max_failures=5, cooldown_seconds=900.0)

        # Trip the breaker
        for _ in range(5):
            await worker.run()
        assert worker.circuit_breaker_open is True
        assert worker.fetch_calls == 5

        # Simulate cooldown expiration: 901 seconds elapsed
        worker.circuit_breaker_tripped_at = datetime.now(timezone.utc) - timedelta(seconds=901)
        worker.should_succeed = True  # Trial request will succeed

        # Half-open trial run
        res = await worker.run()
        assert worker.fetch_calls == 6  # fetch_data WAS called!
        assert res == [{"station_id": "TEST", "value": 42.0}]

        # Verify full recovery to healthy state
        assert worker.is_healthy is True
        assert worker.consecutive_failures == 0
        assert worker.circuit_breaker_open is False
        assert worker.circuit_breaker_tripped_at is None
        assert worker.last_error is None

    @pytest.mark.anyio
    async def test_circuit_breaker_half_open_trial_failure_re_trips(self):
        """When HALF-OPEN trial request fails, breaker immediately re-trips to OPEN."""
        worker = MockCircuitBreakerWorker(max_failures=5, cooldown_seconds=900.0)

        # Trip the breaker
        for _ in range(5):
            await worker.run()
        assert worker.circuit_breaker_open is True
        assert worker.fetch_calls == 5

        # Simulate cooldown expiration: 901 seconds elapsed
        worker.circuit_breaker_tripped_at = datetime.now(timezone.utc) - timedelta(seconds=901)
        worker.should_succeed = False  # Trial request fails again

        # Execute trial run
        res = await worker.run()
        assert worker.fetch_calls == 6  # fetch_data WAS called!
        assert res == [{"fallback": True, "is_estimated": True}]

        # Verify breaker stays OPEN and failure counter increments
        assert worker.circuit_breaker_open is True
        assert worker.consecutive_failures == 6
        assert worker.is_healthy is False

    @pytest.mark.anyio
    async def test_circuit_breaker_intermittent_success_resets_counter(self):
        """Intermittent success on 4th attempt resets failure counter and prevents tripping."""
        worker = MockCircuitBreakerWorker(max_failures=5, cooldown_seconds=900.0)

        # 4 consecutive failures
        for _ in range(4):
            await worker.run()
        assert worker.consecutive_failures == 4
        assert worker.circuit_breaker_open is False

        # 5th attempt succeeds
        worker.should_succeed = True
        res = await worker.run()
        assert res == [{"station_id": "TEST", "value": 42.0}]
        assert worker.consecutive_failures == 0
        assert worker.is_healthy is True
        assert worker.circuit_breaker_open is False


# ==============================================================================
# 4. CSV ADAPTER ENCODING, DELIMITER & PARTIAL LINE STRESS TESTS
# ==============================================================================

class TestUserCSVAdapterEncodingsAndDelimiters:
    """Stress tests covering byte encodings, BOM markers, delimiters, and ragged lines."""

    def test_csv_utf8_with_bom_bytes(self):
        """CSV prefixed with UTF-8 BOM (b'\\xef\\xbb\\xbf') strips BOM cleanly from headers."""
        raw_csv = (
            b"\xef\xbb\xbf"
            b"timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            b"2026-11-10T12:00:00Z,PK_01,Town Hall,Lahore,31.56,74.31,pm25,120.0\n"
        )
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(raw_csv)

        assert res.status == "success"
        assert res.total_rows == 1
        assert res.valid_count == 1
        assert res.quarantine_count == 0
        assert res.observations[0].station_id == "PK_01"
        assert res.observations[0].station_name == "Town Hall"

    def test_csv_latin1_accented_characters(self):
        """CSV containing Latin-1 accented characters ('Lâhoré', 'Café') is handled safely."""
        csv_str = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            "2026-11-10T12:00:00Z,PK_01,Café Node,Lâhoré,31.56,74.31,pm25,120.0\n"
        )
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(csv_str)

        assert res.status == "success"
        assert res.valid_count == 1
        assert res.observations[0].station_name == "Café Node"
        assert res.observations[0].district == "Lâhoré"

    def test_csv_utf16_byte_stream_failure_handling(self):
        """
        Verify passing raw UTF-16 byte streams fails gracefully with descriptive file_errors
        rather than raising unhandled UnicodeDecodeError or crashing the process.
        """
        csv_str = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            "2026-11-10T12:00:00Z,PK_01,Town Hall,Lahore,31.56,74.31,pm25,120.0\n"
        )
        utf16_bytes = csv_str.encode("utf-16")
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(utf16_bytes)

        # Fails safely with file error because adapter expects UTF-8
        assert res.status == "failed"
        assert len(res.file_errors) > 0
        assert "Missing mandatory CSV columns" in res.file_errors[0]

    def test_csv_malformed_delimiters_semicolon_and_tabs(self):
        """CSV files formatted with semicolons or tabs instead of commas fail safely without crashing."""
        adapter = UserCSVIngestionAdapter()

        # Semicolon delimited
        semi_csv = (
            "timestamp;station_id;station_name;district;latitude;longitude;pollutant;value\n"
            "2026-11-10T12:00:00Z;PK_01;Town Hall;Lahore;31.56;74.31;pm25;120.0\n"
        )
        res_semi = adapter.ingest_csv(semi_csv)
        assert res_semi.status == "failed"
        assert "Missing mandatory CSV columns" in res_semi.file_errors[0]

        # Tab delimited
        tab_csv = (
            "timestamp\tstation_id\tstation_name\tdistrict\tlatitude\tlongitude\tpollutant\tvalue\n"
            "2026-11-10T12:00:00Z\tPK_01\tTown Hall\tLahore\t31.56\t74.31\tpm25\t120.0\n"
        )
        res_tab = adapter.ingest_csv(tab_csv)
        assert res_tab.status == "failed"
        assert "Missing mandatory CSV columns" in res_tab.file_errors[0]

    def test_csv_partial_lines_and_ragged_rows(self):
        """
        Ragged CSV with missing columns on row 2: row 2 is quarantined for missing fields,
        while rows 1 and 3 are successfully admitted.
        """
        csv_data = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            "2026-11-10T12:00:00Z,PK_01,Town Hall,Lahore,31.56,74.31,pm25,120.0\n"
            "2026-11-10T12:00:00Z,PK_02,Truncated Row\n"  # Missing lat, lon, pollutant, value
            "2026-11-10T12:00:00Z,PK_03,Faisalabad Node,Faisalabad,31.42,73.08,pm25,150.0\n"
        )
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(csv_data)

        assert res.status == "partial_quarantine"
        assert res.total_rows == 3
        assert res.valid_count == 2
        assert res.quarantine_count == 1
        assert res.quarantine_records[0].row_number == 3
        assert res.quarantine_records[0].station_id == "PK_02"


# ==============================================================================
# 5. CSV ADAPTER SECURITY & MALFORMED FIELDS STRESS TESTS
# ==============================================================================

class TestUserCSVAdapterSecurityAndMalformedFields:
    """Stress tests verifying immunity to SQL injection, path traversal, and malicious strings."""

    def test_sql_injection_payloads_in_string_fields(self):
        """SQL injection vectors in station_id, station_name, and district are handled safely as pure strings."""
        sqli_name = "Town Hall'; DROP TABLE stations; --"
        sqli_dist = "Lahore' OR '1'='1"
        sqli_id = "PK_01' UNION SELECT * FROM users --"

        csv_data = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            f"2026-11-10T12:00:00Z,{sqli_id},{sqli_name},{sqli_dist},31.56,74.31,pm25,120.0\n"
        )
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(csv_data)

        assert res.status == "success"
        assert res.valid_count == 1
        obs = res.observations[0]
        assert obs.station_id == sqli_id
        assert obs.station_name == sqli_name
        assert obs.district == sqli_dist

    def test_path_traversal_payloads_in_station_identifiers(self):
        """Directory traversal paths in station_id are preserved safely as string literals without file system interaction."""
        traversal_id = "../../../../etc/passwd"
        traversal_name = "..\\..\\windows\\win.ini"

        csv_data = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            f"2026-11-10T12:00:00Z,{traversal_id},{traversal_name},Lahore,31.56,74.31,pm25,120.0\n"
        )
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(csv_data)

        assert res.status == "success"
        assert res.valid_count == 1
        obs = res.observations[0]
        assert obs.station_id == traversal_id
        assert obs.station_name == traversal_name

    def test_excessive_length_strings(self):
        """Station names with 5,000 characters process safely without buffer overflow or memory crashes."""
        long_name = "SuperLongStationName_" + ("A" * 5000)
        csv_data = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            f"2026-11-10T12:00:00Z,PK_LONG,{long_name},Lahore,31.56,74.31,pm25,120.0\n"
        )
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(csv_data)

        assert res.status == "success"
        assert res.valid_count == 1
        assert res.observations[0].station_name == long_name

    def test_malformed_numeric_fields_quarantined(self):
        """Strings supplied in numeric columns (latitude, longitude, value) are quarantined via VALIDATION_ERROR."""
        csv_data = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            "2026-11-10T12:00:00Z,PK_01,Station A,Lahore,not_a_latitude,74.31,pm25,120.0\n"
            "2026-11-10T12:00:00Z,PK_02,Station B,Lahore,31.56,not_a_longitude,pm25,120.0\n"
            "2026-11-10T12:00:00Z,PK_03,Station C,Lahore,31.56,74.31,pm25,NaN_value\n"
        )
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(csv_data)

        assert res.status == "failed"
        assert res.total_rows == 3
        assert res.valid_count == 0
        assert res.quarantine_count == 3
        for q in res.quarantine_records:
            assert q.error_type in ("COORDINATES_MISSING_OR_UNRESOLVABLE", "VALIDATION_ERROR")


# ==============================================================================
# 6. CSV ADAPTER DLQ & NON-HALTING VERIFICATION
# ==============================================================================

class TestUserCSVAdapterDLQAndNonHalting:
    """Stress tests verifying non-halting dead-letter quarantine (DLQ) behavior."""

    def test_non_halting_dead_letter_queue_mixed_batch(self):
        """
        Adversarial test: Batch of 10 rows containing 4 valid rows and 6 invalid rows
        with distinct error types. Valid rows MUST be admitted and invalid rows MUST produce
        correct QuarantineRecords without halting the batch.
        """
        rows = [
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value",
            # Row 2: Valid PM2.5
            "2026-11-10T12:00:00Z,PK_01,Town Hall,Lahore,31.56,74.31,pm25,120.0",
            # Row 3: Out-of-bounds Latitude (45.0 > 35.0) -> COORDINATES_MISSING_OR_UNRESOLVABLE
            "2026-11-10T12:00:00Z,PK_02,Bad Lat Station,Lahore,45.0,74.31,pm25,120.0",
            # Row 4: Unrecognized pollutant -> VALIDATION_ERROR
            "2026-11-10T12:00:00Z,PK_03,Bad Pollutant,Lahore,31.56,74.31,lead_pm,120.0",
            # Row 5: Negative concentration (-45.0) -> VALIDATION_ERROR
            "2026-11-10T12:00:00Z,PK_04,Negative Value,Lahore,31.56,74.31,pm25,-45.0",
            # Row 6: Valid PM10
            "2026-11-10T12:00:00Z,PK_01,Town Hall,Lahore,31.56,74.31,pm10,220.0",
            # Row 7: OneNetwork Station 25 -> STATION_EXCLUDED
            "2026-11-10T12:00:00Z,ON_25,OneNetwork Station 25,Lahore,31.56,74.31,pm25,120.0",
            # Row 8: Zero concentration (0.0) -> QC_PURGED
            "2026-11-10T12:00:00Z,PK_06,Zero Value,Lahore,31.56,74.31,pm25,0.0",
            # Row 9: Exceeds physical ceiling (6000.0 > 5000.0) -> VALIDATION_ERROR
            "2026-11-10T12:00:00Z,PK_07,Extreme Ceiling,Lahore,31.56,74.31,pm25,6000.0",
            # Row 10: Valid NO2
            "2026-11-10T12:00:00Z,PK_08,Faisalabad Node,Faisalabad,31.42,73.08,no2,45.0",
            # Row 11: Valid SO2
            "2026-11-10T12:00:00Z,PK_08,Faisalabad Node,Faisalabad,31.42,73.08,so2,35.0",
        ]
        csv_data = "\n".join(rows) + "\n"
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(csv_data)

        # Batch summary checks
        assert res.status == "partial_quarantine"
        assert res.total_rows == 10
        assert res.valid_count == 4
        assert res.quarantine_count == 6

        # Check quarantine details
        error_types = [q.error_type for q in res.quarantine_records]
        assert "COORDINATES_MISSING_OR_UNRESOLVABLE" in error_types
        assert "VALIDATION_ERROR" in error_types
        assert "STATION_EXCLUDED" in error_types
        assert "QC_PURGED" in error_types

        # Verify each quarantine record possesses required diagnostic metadata
        for q in res.quarantine_records:
            assert isinstance(q.row_number, int)
            assert q.row_number >= 2
            assert q.error_type != ""
            assert q.error_message != ""
            assert isinstance(q.raw_record, dict)

    def test_empty_csv_and_missing_headers_reported_as_file_errors(self):
        """Completely empty files or CSVs without required columns report file_errors."""
        adapter = UserCSVIngestionAdapter()

        # Completely empty file
        res_empty = adapter.ingest_csv("")
        assert res_empty.status == "failed"
        assert "CSV file is empty or missing headers." in res_empty.file_errors

        # Missing mandatory columns
        res_missing = adapter.ingest_csv("timestamp,station_id,value\n2026-11-10T12:00:00Z,PK_01,100.0\n")
        assert res_missing.status == "failed"
        assert len(res_missing.file_errors) == 1
        assert "Missing mandatory CSV columns" in res_missing.file_errors[0]


# ==============================================================================
# 7. CSV ADAPTER BOUNDARY ENFORCEMENT & CANONICAL REPAIRS
# ==============================================================================

class TestUserCSVAdapterBoundariesAndCorrections:
    """Stress tests covering Punjab geographic boundaries, OneNetwork Station 25 exclusion, and 8 canonical repairs."""

    def test_geographic_boundary_enforcement(self):
        """
        Coordinates must be within latitude in [27.0, 35.0] and longitude in [69.0, 76.0].
        Exact boundaries are admitted; coordinates outside trigger quarantine.
        """
        adapter = UserCSVIngestionAdapter()

        # 4 corners of Punjab bounding box
        corners = [
            ("27.0", "69.0", True),
            ("35.0", "76.0", True),
            ("27.0", "76.0", True),
            ("35.0", "69.0", True),
            # Lat out of bounds
            ("26.99", "74.0", False),
            ("35.01", "74.0", False),
            # Lon out of bounds
            ("31.5", "68.99", False),
            ("31.5", "76.01", False),
            # Swapped lat/lon: lat=74.34 (out of bounds), lon=31.50
            ("74.34", "31.50", False),
        ]

        for lat_s, lon_s, should_pass in corners:
            csv_data = (
                "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
                f"2026-11-10T12:00:00Z,PK_TEST,Boundary Station,Lahore,{lat_s},{lon_s},pm25,100.0\n"
            )
            res = adapter.ingest_csv(csv_data)
            if should_pass:
                assert res.valid_count == 1, f"Expected pass for ({lat_s}, {lon_s})"
                assert res.quarantine_count == 0
            else:
                assert res.quarantine_count == 1, f"Expected quarantine for ({lat_s}, {lon_s})"
                assert res.valid_count == 0

    def test_onenetwork_station_25_unconditional_exclusion(self):
        """OneNetwork Station 25 must be unconditionally quarantined regardless of coordinates."""
        adapter = UserCSVIngestionAdapter()

        variations = [
            ("OneNetwork Station 25", "ON_25", "Lahore"),
            ("onenetwork 25", "PK_25", "Lahore"),
            ("Station 25", "ON_25", "Lahore"),
            ("OneNetwork", "PK_01", "Lahore"),
            ("Custom Station", "onenetwork", "Lahore"),
        ]

        for sname, sid, dist in variations:
            csv_data = (
                "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
                f"2026-11-10T12:00:00Z,{sid},{sname},{dist},31.56,74.31,pm25,100.0\n"
            )
            res = adapter.ingest_csv(csv_data)
            assert res.valid_count == 0, f"Expected exclusion for {sname} (id: {sid})"
            assert res.quarantine_count == 1
            assert res.quarantine_records[0].error_type == "STATION_EXCLUDED"

    def test_canonical_coordinate_repair_all_8_stations(self):
        """
        Verify canonical coordinate lookup repairs the 8 corrupted registry stations,
        even when supplied with corrupted or (0, 0) coordinates in the CSV.
        """
        adapter = UserCSVIngestionAdapter()

        station_repairs = [
            ("Gulberg III", "PK_GUL", 31.4200, 74.2800, 31.5097, 74.3478),
            ("DC Office Sialkot", "PK_SKT", 32.4900, 74.5300, 32.4945, 74.5372),
            ("Wazirabad", "PK_WAZ", 32.4400, 74.1200, 32.4428, 74.1197),
            ("Sahiwal", "PK_SWL", 0.0000, 0.0000, 30.6682, 73.1114),
            ("Rajanpur", "PK_RJP", 29.1000, 70.3200, 29.1044, 70.3297),
            ("Talagang", "PK_TLG", 32.9200, 72.4100, 32.9283, 72.4189),
            ("Khushab", "PK_KHB", 32.2900, 72.3500, 32.2955, 72.3522),
            ("Safari Park-LHR", "PK_SAF", 31.3800, 74.2200, 31.3821, 74.2238),
        ]

        rows = ["timestamp,station_id,station_name,district,latitude,longitude,pollutant,value"]
        for sname, sid, bad_lat, bad_lon, _, _ in station_repairs:
            rows.append(f"2026-11-10T12:00:00Z,{sid},{sname},Lahore,{bad_lat},{bad_lon},pm25,120.0")

        csv_data = "\n".join(rows) + "\n"
        res = adapter.ingest_csv(csv_data)

        assert res.valid_count == 8
        assert res.quarantine_count == 0

        for obs in res.observations:
            # Match with expected canonical coordinates
            match = next((item for item in station_repairs if item[0].lower() in obs.station_name.lower()), None)
            assert match is not None, f"No match for {obs.station_name}"
            expected_lat = match[4]
            expected_lon = match[5]
            assert abs(obs.latitude - expected_lat) < 1e-4, f"Lat mismatch for {obs.station_name}: {obs.latitude} vs {expected_lat}"
            assert abs(obs.longitude - expected_lon) < 1e-4, f"Lon mismatch for {obs.station_name}: {obs.longitude} vs {expected_lon}"

    def test_extreme_concentration_tagging_and_clamping(self):
        """
        Verify:
        - PM2.5 > 1000.0 up to 5000.0 ug/m3 is admitted and tagged with QC_EXCEEDANCE_EXTREME.
        - PM10 > 1500.0 up to 5000.0 ug/m3 is admitted and tagged with QC_EXCEEDANCE_EXTREME.
        - Values > 5000.0 ug/m3 exceed statutory physical ceiling and are quarantined via VALIDATION_ERROR.
        - Negative values are quarantined via VALIDATION_ERROR.
        - Zero values are quarantined via QC_PURGED.
        """
        adapter = UserCSVIngestionAdapter()

        cases = [
            # PM2.5 extreme exceedance (admitted with tag)
            ("PK_01", "Town Hall", "Lahore", "pm25", "1250.0", True, ["QC_EXCEEDANCE_EXTREME"]),
            # PM10 extreme exceedance (admitted with tag)
            ("PK_02", "Multan Node", "Multan", "pm10", "1650.0", True, ["QC_EXCEEDANCE_EXTREME"]),
            # PM2.5 exact statutory ceiling (admitted with tag)
            ("PK_03", "Ceiling Node", "Lahore", "pm25", "5000.0", True, ["QC_EXCEEDANCE_EXTREME"]),
            # Normal PM2.5 (admitted without tag)
            ("PK_04", "Normal Node", "Lahore", "pm25", "85.0", True, []),
            # Exceeding 5000 ceiling (quarantined)
            ("PK_05", "Unphysical Node", "Lahore", "pm25", "5001.0", False, "VALIDATION_ERROR"),
            # Negative concentration (quarantined)
            ("PK_06", "Negative Node", "Lahore", "pm25", "-20.0", False, "VALIDATION_ERROR"),
            # Zero concentration (quarantined via Step 0 QC)
            ("PK_07", "Zero Node", "Lahore", "pm25", "0.0", False, "QC_PURGED"),
        ]

        rows = ["timestamp,station_id,station_name,district,latitude,longitude,pollutant,value"]
        for sid, sname, dist, pol, val, _, _ in cases:
            rows.append(f"2026-11-10T12:00:00Z,{sid},{sname},{dist},31.56,74.31,{pol},{val}")

        csv_data = "\n".join(rows) + "\n"
        res = adapter.ingest_csv(csv_data)

        # 4 admitted, 3 quarantined
        assert res.valid_count == 4
        assert res.quarantine_count == 3

        # Verify admitted rows have appropriate flags
        pm25_extreme = next(o for o in res.observations if o.station_id == "PK_01")
        assert "QC_EXCEEDANCE_EXTREME" in pm25_extreme.qc_flags
        assert pm25_extreme.pm25_qc == 1250.0

        pm10_extreme = next(o for o in res.observations if o.station_id == "PK_02")
        assert "QC_EXCEEDANCE_EXTREME" in pm10_extreme.qc_flags
        assert pm10_extreme.pm10_qc == 1650.0

        ceiling_obs = next(o for o in res.observations if o.station_id == "PK_03")
        assert "QC_EXCEEDANCE_EXTREME" in ceiling_obs.qc_flags
        assert ceiling_obs.pm25_qc == 5000.0

        normal_obs = next(o for o in res.observations if o.station_id == "PK_04")
        assert "QC_EXCEEDANCE_EXTREME" not in normal_obs.qc_flags

        # Verify quarantined error types
        q_5001 = next(q for q in res.quarantine_records if q.station_id == "PK_05")
        assert q_5001.error_type == "VALIDATION_ERROR"

        q_neg = next(q for q in res.quarantine_records if q.station_id == "PK_06")
        assert q_neg.error_type == "VALIDATION_ERROR"

        q_zero = next(q for q in res.quarantine_records if q.station_id == "PK_07")
        assert q_zero.error_type == "QC_PURGED"
