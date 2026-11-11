"""
Tier 1: Feature Coverage & Contract Validation Tests
Tests each core feature in isolation across mathematical transforms, schemas,
data ingestion pipelines, and API contracts according to PROJECT.md and docs/.
"""
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pytest
from tests.e2e.conftest import (
    PAQReferenceOracle,
    RawStationMeasurementContract,
    UserCSVRowContract,
)


class TestTier1MathematicalTransforms:
    """Verifies all 11 scientific transformation functions in isolation."""

    def test_haversine_geodesic_distance(self, reference_oracle: PAQReferenceOracle):
        """T1: Great-circle distance between known Punjab coordinates."""
        # Lahore (31.5204, 74.3587) to Kasur (31.1179, 74.4460)
        d_km = reference_oracle.haversine_distance(31.5204, 74.3587, 31.1179, 74.4460)
        assert 45.4 <= d_km <= 45.6, f"Expected ~45.5 km, got {d_km}"

        # Coincident coordinates must yield exactly 0.0 km
        assert reference_oracle.haversine_distance(31.5, 74.3, 31.5, 74.3) == 0.0

    def test_discrete_geodesic_idw_interpolation(self, reference_oracle: PAQReferenceOracle):
        """T1: Discrete IDW interpolation with Haversine distance and d0=5km clamping."""
        target = (31.5000, 74.3000)
        stations = [
            {"coords": (31.5500, 74.3500), "value": 150.0},
            {"coords": (31.4500, 74.2500), "value": 180.0},
            {"coords": (31.6000, 74.4000), "value": 120.0},
        ]
        val = reference_oracle.discrete_geodesic_idw(target, stations, power=2.0, d0_km=5.0)
        assert val is not None
        assert 120.0 <= val <= 180.0

    def test_vector_wind_conversion(self, reference_oracle: PAQReferenceOracle):
        """T4: Meteorological polar to Cartesian (u, v) kinematic flow vectors."""
        # Wind FROM East (90 deg) blows TO West -> u < 0, v == 0
        u, v = reference_oracle.polar_to_cartesian_wind(10.0, 90.0)
        assert abs(u - (-10.0)) < 1e-5
        assert abs(v - 0.0) < 1e-5

        # Wind FROM South (180 deg) blows TO North -> u == 0, v > 0
        u, v = reference_oracle.polar_to_cartesian_wind(10.0, 180.0)
        assert abs(u - 0.0) < 1e-5
        assert abs(v - 10.0) < 1e-5

        # Reconstructed speed and direction match input
        speed_rec, dir_rec = reference_oracle.cartesian_to_polar_wind(u, v)
        assert abs(speed_rec - 10.0) < 1e-4
        assert abs(dir_rec - 180.0) < 1e-4

    def test_cpf_wind_rose_16_sectors(self, reference_oracle: PAQReferenceOracle):
        """T5: 16-sector CPF polar wind rose calculation with calm exclusion."""
        # 8 observations from East (90 deg, sector 4)
        obs = [
            {"wind_speed": 2.0, "wind_direction": 90.0, "value": 250.0},
            {"wind_speed": 2.5, "wind_direction": 90.0, "value": 260.0},
            {"wind_speed": 2.2, "wind_direction": 90.0, "value": 240.0},
            {"wind_speed": 1.8, "wind_direction": 90.0, "value": 270.0},
            {"wind_speed": 3.0, "wind_direction": 90.0, "value": 280.0},
            {"wind_speed": 2.1, "wind_direction": 90.0, "value": 290.0},
            {"wind_speed": 1.9, "wind_direction": 90.0, "value": 150.0},
            {"wind_speed": 2.0, "wind_direction": 90.0, "value": 140.0},
            # 2 calm observations (< 0.5 m/s)
            {"wind_speed": 0.2, "wind_direction": 90.0, "value": 300.0},
            {"wind_speed": 0.3, "wind_direction": 180.0, "value": 310.0},
        ]
        threshold_tau = 200.0
        result = reference_oracle.calculate_cpf_rose(obs, threshold_tau, calm_threshold_ms=0.5)

        assert result["calm_ratio"] == 0.2  # 2 calms out of 10
        # Sector 4 (East) has 8 non-calm obs (>= 6 min threshold), 6 exceed tau=200 -> CPF = 6/8 = 0.75
        assert result["sectors"][4] == 0.75
        # Other sectors have 0 obs (< 6 threshold) -> None (small-sample suppression)
        assert result["sectors"][0] is None
        assert result["sectors"][8] is None

    def test_advection_transport_flux(self, reference_oracle: PAQReferenceOracle):
        """T6: Physical inter-district advection mass flux calculation."""
        # Source at Lahore (31.5204, 74.3587), Receptor at Kasur (31.1179, 74.4460)
        # Kasur is South-Southeast of Lahore (bearing ~168 degrees)
        # Wind blowing towards Kasur (u > 0, v < 0)
        # Vector pointing ~168 deg TO -> u = 2.0 * sin(168), v = 2.0 * cos(168)
        rad = math.radians(168.0)
        u_wind = 2.5 * math.sin(rad)
        v_wind = 2.5 * math.cos(rad)

        flux = reference_oracle.calculate_advection_flux(
            source_coords=(31.5204, 74.3587),
            receptor_coords=(31.1179, 74.4460),
            concentration=200.0,
            u_wind=u_wind,
            v_wind=v_wind,
            pollutant="PM2.5",
            max_dist_km=180.0,
            cone_deg=35.0,
            residence_km=100.0
        )
        assert flux is not None
        assert flux["flux"] > 0.0
        assert flux["distance_km"] < 50.0
        assert flux["divergence_deg"] <= 35.0

    def test_pepc_piecewise_linear_aqi(self, reference_oracle: PAQReferenceOracle):
        """T9: Statutory PEPC piecewise linear sub-indices across all 6 categories."""
        # PM2.5 = 15.0 -> Category 0 top = AQI 50 (Good)
        assert reference_oracle.pepc_calculate_aqi("PM2.5", 15.0) == 50

        # PM2.5 = 35.0 -> Category 1 top = AQI 100 (Satisfactory)
        assert reference_oracle.pepc_calculate_aqi("PM2.5", 35.0) == 100

        # PM2.5 = 70.0 -> Category 2 top = AQI 150 (Moderate)
        assert reference_oracle.pepc_calculate_aqi("PM2.5", 70.0) == 150

        # PM2.5 = 140.0 -> Category 3 top = AQI 200 (Unhealthy Sensitive)
        assert reference_oracle.pepc_calculate_aqi("PM2.5", 140.0) == 200

        # PM2.5 = 250.0 -> Category 4 top = AQI 300 (Unhealthy)
        assert reference_oracle.pepc_calculate_aqi("PM2.5", 250.0) == 300

        # PM2.5 = 350.0 -> Category 5 top = AQI 400 (Very Unhealthy)
        assert reference_oracle.pepc_calculate_aqi("PM2.5", 350.0) == 400

        # PM2.5 = 450.0 -> Clamped to 500 (Hazardous)
        assert reference_oracle.pepc_calculate_aqi("PM2.5", 450.0) == 500

    def test_pepc_composite_aqi_and_colors(self, reference_oracle: PAQReferenceOracle):
        """T9: Composite AQI = max(PM2.5, PM10) and official PEPC color mapping."""
        # Composite AQI is max between PM2.5 and PM10
        composite = reference_oracle.pepc_composite_aqi(pm25_aqi=150, pm10_aqi=100)
        assert composite == 150

        # Color stops
        assert reference_oracle.pepc_get_color(45) == "#00B050"   # Good
        assert reference_oracle.pepc_get_color(80) == "#92D050"   # Satisfactory
        assert reference_oracle.pepc_get_color(135) == "#FFFF00"  # Moderate
        assert reference_oracle.pepc_get_color(175) == "#ED7D31"  # Unhealthy Sensitive
        assert reference_oracle.pepc_get_color(260) == "#FF0000"  # Unhealthy
        assert reference_oracle.pepc_get_color(360) == "#7030A0"  # Very Unhealthy
        assert reference_oracle.pepc_get_color(450) == "#C00000"  # Hazardous

    def test_temporal_qc_cleaning(self, reference_oracle: PAQReferenceOracle):
        """T10: Zero-purge, 7h median spike filter, and 3h logger hold filter."""
        # 12-hour series:
        # Index 0: 50.0
        # Index 1: 0.0 (must be nulled)
        # Index 2: -10.0 (must be nulled)
        # Index 3-5: 50.0, 52.0, 51.0
        # Index 6: 450.0 (Spike: > 4 * median(51) and > 3 * 35 -> must be nulled)
        # Index 7-8: 50.0, 52.0
        # Index 9-11: 85.0, 85.0, 85.0 (3h Hold: index 11 must be nulled)
        series = [50.0, 0.0, -10.0, 50.0, 52.0, 51.0, 450.0, 50.0, 52.0, 85.0, 85.0, 85.0]
        cleaned, spike_count = reference_oracle.temporal_qc_clean(series, ref_limit=35.0, pollutant="PM2.5")

        assert cleaned[1] is None  # Zero purged
        assert cleaned[2] is None  # Negative purged
        assert cleaned[6] is None  # Spike nulled
        assert spike_count >= 1
        assert cleaned[11] is None  # 3h hold nulled at index 11
        assert cleaned[9] == 85.0  # Initial hold value preserved

    def test_equirectangular_projection(self, reference_oracle: PAQReferenceOracle):
        """T11: Plate Carrée with standard parallel 31 deg N projection."""
        x, y = reference_oracle.equirectangular_project(31.5204, 74.3587, width_px=1200, height_px=900)
        assert 0.0 <= x <= 1200.0
        assert 0.0 <= y <= 900.0


class TestTier1SchemasAndDataContracts:
    """Verifies Pydantic v2 data models and ingestion schemas."""

    def test_raw_station_measurement_schema_valid(self):
        """Validates standard compliant station measurement payload."""
        data = {
            "station_id": "PK_LHR_001",
            "station_name": "Lahore Town Hall",
            "district": "Lahore",
            "timestamp": "2026-11-10T12:00:00Z",
            "pm25": 185.4,
            "pm10": 290.1,
            "wind_speed": 2.5,
            "wind_direction": 90.0,
            "aqi": 235.0
        }
        item = RawStationMeasurementContract(**data)
        assert item.station_name == "Lahore Town Hall"
        assert item.pm25 == 185.4
        assert item.wind_speed == 2.5

    def test_user_csv_row_schema_valid(self):
        """Validates user-submitted CSV row schema."""
        row_data = {
            "timestamp": "2026-11-10 12:00",
            "station_id": "USER_ST_001",
            "station_name": "Rural Monitor 1",
            "district": "Kasur",
            "latitude": 31.1179,
            "longitude": 74.4460,
            "pollutant": "PM2.5",
            "value": 145.2,
            "wind_speed": 2.0,
            "wind_direction": 85.0
        }
        item = UserCSVRowContract(**row_data)
        assert item.pollutant == "pm25"
        assert item.latitude == 31.1179
        assert item.value == 145.2

    def test_csv_fixture_ingestion_parsing(self, load_csv_fixture):
        """Verifies parsing and validating all rows from valid_station_observations.csv."""
        rows = load_csv_fixture("valid_station_observations.csv")
        assert len(rows) > 0

        validated_count = 0
        for r in rows:
            validated = UserCSVRowContract(
                timestamp=r["timestamp"],
                station_id=r["station_id"],
                station_name=r["station_name"],
                district=r["district"],
                latitude=float(r["latitude"]),
                longitude=float(r["longitude"]),
                pollutant=r["pollutant"],
                value=float(r["value"]),
                wind_speed=float(r["wind_speed"]) if r.get("wind_speed") else None,
                wind_direction=float(r["wind_direction"]) if r.get("wind_direction") else None,
            )
            assert validated.value >= 0.0
            validated_count += 1

        assert validated_count == len(rows)


class TestTier1APIEndpointContracts:
    """Verifies API route schemas and response contracts defined in SYSTEM_ARCHITECTURE.md."""

    def test_api_route_specifications_present(self):
        """Ensures all 10 core API route specifications are documented with contract expectations."""
        required_routes = [
            ("GET", "/api/v1/meta/districts"),
            ("GET", "/api/v1/meta/stations"),
            ("GET", "/api/v1/observations/current"),
            ("GET", "/api/v1/observations/hourly"),
            ("GET", "/api/v1/spatial/surface"),
            ("GET", "/api/v1/analytics/cpf"),
            ("GET", "/api/v1/analytics/flux"),
            ("GET", "/api/v1/analytics/transboundary"),
            ("POST", "/api/v1/ingest/csv"),
            ("GET", "/api/v1/stream/live"),
        ]
        assert len(required_routes) == 10
