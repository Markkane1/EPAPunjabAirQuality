"""
Unit tests for EPA Punjab Live AQMS Worker & Station Catalog.
Tests conformance with EPD AQMS API specifications (documented 13 Nov 2026).
"""
from datetime import datetime, timezone, timedelta
import pytest
import httpx

from src.domain.constants.epa_stations import (
    EPA_STATIONS_CATALOG,
    get_epa_station_info,
    get_all_epa_stations,
    resolve_district_for_station,
    resolve_station_coords,
)
from src.domain.schemas.measurement import RawStationMeasurement, PKT, UTC
from src.pipelines.epa_punjab import EPAPunjabIngestionWorker


class TestEPAStationsCatalog:
    """Verifies official 38-station directory and coordinate mapping."""

    def test_catalog_station_count(self):
        stations = get_all_epa_stations()
        assert len(stations) == 38
        assert len(EPA_STATIONS_CATALOG) == 38

    def test_lahore_fixed_stations(self):
        uet = get_epa_station_info("UET-LHR")
        assert uet is not None
        assert uet["district"] == "Lahore"
        assert uet["station_type"] == "fixed"
        assert round(uet["latitude"], 4) == 31.5798
        assert round(uet["longitude"], 4) == 74.3550

        safari = get_epa_station_info("Safari Park-LHR")
        assert safari is not None
        assert safari["district"] == "Lahore"

    def test_mobile_station_resolution(self):
        # By API id
        m1 = get_epa_station_info("Mobile 1")
        assert m1 is not None
        assert m1["station_type"] == "mobile"
        assert m1["district"] == "Kasur"
        assert m1["display_name"] == "Raja Jang Kasur - Mobile 1"

        # By full display name alias
        m2 = get_epa_station_info("Lathepur LHR - Mobile 2")
        assert m2 is not None
        assert m2["api_id"] == "Mobile 2"
        assert m2["district"] == "Lahore"

    def test_resolve_coords_and_district(self):
        coords = resolve_station_coords("DC Office Rawalpindi")
        assert coords is not None
        assert round(coords[0], 2) == 33.58
        assert round(coords[1], 2) == 73.07

        district = resolve_district_for_station("GCU Faisalabad")
        assert district == "Faisalabad"


class TestEPALiveIngestionWorker:
    """Verifies API requests, parsing, Status_* handling, and error contracts."""

    def test_default_config(self):
        worker = EPAPunjabIngestionWorker()
        assert worker.base_url == "https://api.epd-aqms-pk.com"
        assert worker.api_key == "7b2f49c1e0e447c6a2bde74b81f51a87"
        headers = worker._get_headers()
        assert headers["X-API-Key"] == "7b2f49c1e0e447c6a2bde74b81f51a87"
        assert "EMC-EPA-Punjab" in headers["User-Agent"]

    def test_parse_latest_hour_dictionary(self):
        worker = EPAPunjabIngestionWorker()
        sample_latest = {
            "UET-LHR": {
                "AQI": 117,
                "AQI_category": "Moderate",
                "BP": 992.5,
                "CO": 0.37,
                "Date_Time": "2026-11-13 13:00:00",
                "Dominant_Pollutant": "PM25",
                "NO": 4.06,
                "NO2": 15.56,
                "NOX": 21.84,
                "O3": 35.33,
                "PM10": 157.35,
                "PM25": 46.39,
                "RH": 73.0,
                "Rain": 0.0,
                "SO2": 113.97,
                "SR": 114.76,
                "Temp": 21.21,
                "WD": 285.77,
                "WS": 1.48,
            },
            "Mobile 1": {
                "AQI": 250,
                "Date_Time": "2026-11-13 13:00:00",
                "PM25": 160.0,
                "PM10": 290.0,
            },
        }

        measurements = worker.parse_and_validate(sample_latest)
        assert len(measurements) == 2

        uet = next(m for m in measurements if m.station_id == "UET-LHR")
        assert uet.station_name == "UET-LHR"
        assert uet.district == "Lahore"
        assert uet.pm25 == 46.39
        assert uet.pm10 == 157.35
        assert uet.aqi == 117.0
        assert uet.wind_speed == 1.48
        assert uet.wind_direction == 285.77
        assert uet.is_estimated is False
        # Datetime PKT -> UTC: 13:00 PKT is 08:00 UTC
        assert uet.timestamp.hour == 8

        m1 = next(m for m in measurements if m.station_id == "Mobile 1")
        assert m1.station_name == "Raja Jang Kasur - Mobile 1"
        assert m1.district == "Kasur"
        assert m1.pm25 == 160.0

    def test_status_field_filtering(self):
        worker = EPAPunjabIngestionWorker()
        payload = {
            "Safari Park-LHR": {
                "Date_Time": "2026-11-13 13:00:00",
                "AQI": 304,
                "PM25": 253.4,
                "PM10": 336.7,
                "Status_PM25": "Incomplete",  # Incomplete status must nullify PM25
                "Status_PM10": "Valid",
            }
        }
        res = worker.parse_and_validate(payload)
        assert len(res) == 1
        m = res[0]
        assert m.pm25 is None  # Dropped due to Status_PM25: Incomplete
        assert m.pm10 == 336.7  # Valid status preserved

    def test_parse_periodic_array_format(self):
        worker = EPAPunjabIngestionWorker()
        payload = {
            "Safari Park-LHR": [
                {
                    "Date_Time": "2026-11-13 11:00:00",
                    "AQI": 280,
                    "PM25": 180.0,
                },
                {
                    "Date_Time": "2026-11-13 12:00:00",
                    "AQI": 310,
                    "PM25": 210.0,
                },
            ]
        }
        res = worker.parse_and_validate(payload)
        assert len(res) == 2
        assert res[0].timestamp < res[1].timestamp
        assert res[0].station_name == "Safari Park-LHR"

    def test_invalid_interval_rejection(self):
        worker = EPAPunjabIngestionWorker()
        with pytest.raises(ValueError) as exc:
            import asyncio
            asyncio.run(worker.fetch_periodic("UET-LHR", "2026-11-13 00:00:00", "2026-11-13 12:00:00", interval="45"))
        assert "Invalid interval" in str(exc.value)

    @pytest.mark.anyio
    async def test_mocked_live_fetch(self):
        def handler(request: httpx.Request):
            assert request.headers.get("X-API-Key") == "7b2f49c1e0e447c6a2bde74b81f51a87"
            if request.url.path == "/latest_hour":
                return httpx.Response(200, json={
                    "UET-LHR": {
                        "Date_Time": "2026-11-13 14:00:00",
                        "AQI": 120,
                        "PM25": 50.0,
                        "PM10": 160.0
                    }
                })
            elif request.url.path == "/alerts/last_two_days":
                return httpx.Response(200, json=[
                    {"Alert": "E04.3: No Data from Station DC Office Rahim Yar Khan", "Date_Time": "2026-11-13 14:00:00"}
                ])
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            worker = EPAPunjabIngestionWorker(client=client)
            latest = await worker.fetch_latest_hour()
            assert "UET-LHR" in latest
            measurements = worker.parse_and_validate(latest)
            assert len(measurements) == 1
            assert measurements[0].pm25 == 50.0

            alerts = await worker.fetch_alerts_last_two_days()
            assert len(alerts) == 1
            assert "E04.3" in alerts[0]["Alert"]
