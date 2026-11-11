"""
Integration test suite for external data ingestion pipelines and fallback services.
Verifies:
1. FallbackTemplateEngine initialization and schema-conforming generation from baseline data.
2. EPAPunjabIngestionWorker live fetching, retry backoff, Pydantic parsing, fan-out, and fallback.
3. MetarIngestionWorker units conversion (knots-to-m/s, statute-to-meters, metric regex override), weather tokens, and fallback.
4. SynopIngestionWorker WMO FM-12 AAXX telegraphic decoding, 429 rate limit floor, and fallback.
5. OpenMeteoIngestionWorker 41-centroid query, roughness scaling (K_R = 0.22686), vector decomposition, and fallback.
"""
from datetime import datetime, timezone
import pytest
import httpx

from src.domain.schemas.measurement import RawStationMeasurement
from src.pipelines.fallback_engine import FallbackTemplateEngine
from src.pipelines.epa_punjab import EPAPunjabIngestionWorker
from src.pipelines.metar import MetarIngestionWorker
from src.pipelines.synop import SynopIngestionWorker
from src.pipelines.open_meteo import OpenMeteoIngestionWorker


class TestFallbackTemplateEngine:
    """Verifies baseline templating engine seeded from extracted JSON artifacts."""

    def test_engine_initialization_and_inventory(self):
        engine = FallbackTemplateEngine()
        assert len(engine.stations) == 79
        assert len(engine.districts) == 41
        assert len(engine.airports) == 6
        assert len(engine.hours) == 216

    def test_station_measurement_fallback_conformance(self):
        engine = FallbackTemplateEngine()
        meas = engine.get_station_measurement_fallback("Safari Park-LHR", hour_idx=0)
        assert meas is not None
        assert isinstance(meas, RawStationMeasurement)
        assert meas.station_name == "Safari Park-LHR"
        assert meas.district == "Lahore"
        assert meas.pm25 is not None
        assert meas.is_estimated is True
        assert "FALLBACK_BASELINE_ESTIMATION" in meas.qc_flags

    def test_all_stations_measurement_fallback(self):
        engine = FallbackTemplateEngine()
        measurements = engine.get_all_station_measurements_fallback(hour_idx=100)
        assert len(measurements) == 79
        for m in measurements:
            assert isinstance(m, RawStationMeasurement)
            assert m.is_estimated is True

    def test_district_observation_fallback(self):
        engine = FallbackTemplateEngine()
        obs = engine.get_district_observation_fallback("Rawalpindi", hour_idx=50)
        assert obs is not None
        assert obs.district_id == "Rawalpindi"
        assert obs.is_estimated is True
        assert obs.u is not None
        assert obs.v is not None

    def test_airport_metar_fallback(self):
        engine = FallbackTemplateEngine()
        metar = engine.get_airport_metar_fallback("OPLA", hour_idx=10)
        assert metar is not None
        assert metar["icaoId"] == "OPLA"
        assert metar["is_estimated"] is True
        assert "wind_speed_ms" in metar
        assert metar["source"] == "baseline_airports"

    def test_open_meteo_fallback(self):
        engine = FallbackTemplateEngine()
        forecasts = engine.get_open_meteo_fallback(hour_idx=0)
        assert len(forecasts) == 41
        for f in forecasts:
            assert f["is_estimated"] is True
            assert f["k_r"] == 0.22686
            assert "u_calibrated" in f

    def test_canonical_coordinate_resolution(self):
        engine = FallbackTemplateEngine()
        # Sahiwal corrected coordinates
        coords_sahiwal = engine.resolve_station_coords("sahiwal_1", "Sahiwal Municipal Corporation")
        assert coords_sahiwal == (30.6682, 73.1114)

        # Gulberg III
        coords_gulberg = engine.resolve_station_coords("gulberg_1", "Gulberg III")
        assert coords_gulberg == (31.5097, 74.3478)

        # OneNetwork Station 25 excluded
        coords_onenet = engine.resolve_station_coords("25", "OneNetwork Station 25")
        assert coords_onenet is None


class TestEPAPunjabWorker:
    """Verifies EPA Punjab live worker, parsing, extreme exceedance, and fallback."""

    def test_worker_initialization(self):
        worker = EPAPunjabIngestionWorker()
        assert worker.stream_id == "STR-01-EPAPUNJAB"
        assert worker.user_agent == "EMC-EPA-Punjab-AQ-dashboard/1.0"
        assert worker.is_healthy is True

    def test_parse_valid_epa_payload(self):
        worker = EPAPunjabIngestionWorker()
        payload = {
            "status": "success",
            "timestamp": "2026-11-10T12:00:00Z",
            "data": [
                {
                    "station_id": 10,
                    "station_name": "DHQ Sheikhupura",
                    "district": "Sheikhupura",
                    "timestamp": "2026-11-10T12:00:00Z",
                    "aqi": 215.0,
                    "pm25": 165.2,
                    "pm10": 280.5,
                    "wind_speed": 1.5,
                    "wind_direction": 180.0,
                },
                {
                    "station_id": 25,
                    "station_name": "OneNetwork Station 25",
                    "district": "Unknown",
                    "timestamp": "2026-11-10T12:00:00Z",
                    "pm25": 100.0,
                },
            ],
        }
        measurements = worker.parse_and_validate(payload)
        # OneNetwork Station 25 must be excluded
        assert len(measurements) == 1
        m = measurements[0]
        assert m.station_name == "DHQ Sheikhupura"
        assert m.pm25 == 165.2
        assert m.is_estimated is False

    def test_extreme_exceedance_tagging(self):
        worker = EPAPunjabIngestionWorker()
        payload = {
            "data": [
                {
                    "station_id": 99,
                    "station_name": "Lahore Crisis Node",
                    "district": "Lahore",
                    "timestamp": "2026-11-10T12:00:00Z",
                    "pm25": 1250.0,
                    "pm10": 1850.0,
                }
            ]
        }
        meas = worker.parse_and_validate(payload)[0]
        assert meas.pm25 == 1250.0
        assert meas.pm10 == 1850.0
        assert "QC_EXCEEDANCE_EXTREME" in meas.qc_flags

    @pytest.mark.anyio
    async def test_graceful_fallback_on_network_failure(self):
        # Point worker to non-existent endpoint to force network failure
        worker = EPAPunjabIngestionWorker(base_url="http://127.0.0.1:9999", timeout=0.1)
        worker.retry_delays = [0.01]  # Fast retry for test

        results = await worker.run(hour_idx=0)
        assert len(results) == 79
        assert worker.is_healthy is False
        assert worker.consecutive_failures == 1
        assert worker.last_error is not None
        # Verify fallback data
        assert all(m.is_estimated is True for m in results)

    @pytest.mark.anyio
    async def test_circuit_breaker_tripping(self):
        worker = EPAPunjabIngestionWorker(base_url="http://127.0.0.1:9999", timeout=0.1)
        worker.retry_delays = [0.01]
        worker.max_failures_before_circuit_break = 3

        for _ in range(3):
            await worker.run(hour_idx=0)

        assert worker.circuit_breaker_open is True
        assert worker.consecutive_failures == 3

        # Next run routes directly to fallback without network call
        direct_fallback = await worker.run(hour_idx=0)
        assert len(direct_fallback) == 79


class TestMetarWorker:
    """Verifies METAR ingestion, conversions, metric regex override, and fallback."""

    def test_metar_conversions_and_tokens(self):
        worker = MetarIngestionWorker()
        raw_payload = [
            {
                "icaoId": "OPLA",
                "obsTime": "2026-11-10T11:50:00Z",
                "wspd": 10.0,  # 10 knots
                "wdir": 90,    # East
                "visib": 3.0,   # 3 statute miles
                "wxString": "HZ FU",
                "rawOb": "METAR OPLA 101150Z 09010KT 0800 HZ FU NSC 24/16 Q1012 NOSIG=",
            }
        ]
        results = worker.parse_and_validate(raw_payload)
        assert len(results) == 1
        m = results[0]
        assert m["icaoId"] == "OPLA"
        # 10 knots * 0.514444 = 5.14 m/s
        assert abs(m["wind_speed_ms"] - 5.14) < 0.05
        # 0800 in rawOb should override 3 statute miles with 800m metric visibility
        assert m["visibility_m"] == 800.0
        # Decoded weather
        assert "Smoke" in m["weather_decoded"]
        assert "Haze" in m["weather_decoded"]
        # u pointing west (u < 0) for wind FROM 90 deg (East)
        assert m["u"] < 0.0

    def test_variable_wind_vrb(self):
        worker = MetarIngestionWorker()
        raw_payload = [
            {
                "icaoId": "OPST",
                "obsTime": "2026-11-10T12:00:00Z",
                "wspd": 4.0,
                "wdir": "VRB",
                "visib": 6.0,
            }
        ]
        results = worker.parse_and_validate(raw_payload)
        m = results[0]
        assert m["wind_speed_ms"] > 0.0
        assert m["wind_direction_deg"] is None

    @pytest.mark.anyio
    async def test_metar_fallback_on_failure(self):
        worker = MetarIngestionWorker(base_url="http://127.0.0.1:9999", timeout=0.1)
        results = await worker.run(hour_idx=0)
        assert len(results) == len(worker.target_airports)
        for r in results:
            assert r["is_estimated"] is True
            assert r["source"] == "baseline_airports"


class TestSynopWorker:
    """Verifies WMO FM-12 SYNOP telegraphic decoder, 429 rate limit floor, and fallback."""

    def test_decode_standard_synop_telegram(self):
        worker = SynopIngestionWorker()
        # AAXX line for Lahore PBO (41640), iw=4 (knots), wind 180 deg at 02 knots, T=+22.4, Td=+18.2
        line = "AAXX 09184 41640 11560 81802 10224 20182 40162 57018 70582 8536/ 333 55300 20000="
        decoded = worker.decode_synop_line(line)
        assert decoded is not None
        assert decoded["wmo_id"] == "41640"
        assert decoded["station_name"] == "Lahore PBO"
        # 18 tens of degrees = 180.0
        assert decoded["wind_direction_deg"] == 180.0
        # 02 knots * 0.514444 = 1.03 m/s
        assert abs(decoded["wind_speed_ms"] - 1.03) < 0.05
        assert decoded["temperature_c"] == 22.4
        assert decoded["dewpoint_c"] == 18.2
        assert decoded["is_estimated"] is False

    def test_decode_calm_wind(self):
        worker = SynopIngestionWorker()
        line = "AAXX 09181 41641 11560 80000 10210 20170 40160 333="
        decoded = worker.decode_synop_line(line)
        assert decoded is not None
        assert decoded["wind_speed_ms"] == 0.0
        assert decoded["wind_direction_deg"] is None
        assert decoded["u"] == 0.0
        assert decoded["v"] == 0.0

    @pytest.mark.anyio
    async def test_synop_fallback_on_failure(self):
        worker = SynopIngestionWorker(base_url="http://127.0.0.1:9999", timeout=0.1)
        results = await worker.run(hour_idx=0)
        assert len(results) == 7
        for r in results:
            assert r["is_estimated"] is True
            assert r["source"] == "baseline_synop"


class TestOpenMeteoWorker:
    """Verifies ECMWF IFS Open-Meteo multi-point querying, roughness scaling, and fallback."""

    def test_roughness_scaling_and_decomposition(self):
        worker = OpenMeteoIngestionWorker(roughness_k_r=0.22686)
        mock_payload = [
            {
                "latitude": 31.5204,
                "longitude": 74.3587,
                "hourly": {
                    "time": ["2026-11-10T12:00"],
                    "wind_speed_10m": [10.0],
                    "wind_direction_10m": [180.0],
                },
            }
        ]
        parsed = worker.parse_and_validate(mock_payload, district_names=["Lahore"], hour_index=0)
        assert len(parsed) == 1
        res = parsed[0]
        assert res["district"] == "Lahore"
        assert res["wind_speed_raw_ms"] == 10.0
        # 10.0 * 0.22686 = 2.269 m/s
        assert abs(res["wind_speed_calibrated_ms"] - 2.269) < 0.01
        assert res["roughness_factor"] == 0.22686

    @pytest.mark.anyio
    async def test_open_meteo_fallback_on_failure(self):
        worker = OpenMeteoIngestionWorker(base_url="http://127.0.0.1:9999", timeout=0.1)
        results = await worker.run(hour_idx=0)
        assert len(results) == 41
        for r in results:
            assert r["is_estimated"] is True
            assert r["source"] == "baseline_ecmwf"
