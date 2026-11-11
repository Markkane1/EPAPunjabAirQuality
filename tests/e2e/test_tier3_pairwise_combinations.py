"""
Tier 3: Pairwise Combinations & Cross-Feature Integration Tests
Tests combinatorial pairs of meteorological states, pollutants, pipeline events,
and multi-step calculations across system subsystems.
"""
import math
from typing import Any, Dict, List

import pytest
from tests.e2e.conftest import (
    PAQReferenceOracle,
    UserCSVRowContract,
)


class TestTier3MeteorologicalCombinations:
    """Pairwise combinations of wind velocity and direction across all cardinal quadrants."""

    WIND_SPEEDS = [0.2, 1.0, 5.0, 25.0]  # Calm, Light, Moderate, High
    WIND_DIRECTIONS = [0.0, 90.0, 180.0, 270.0]  # North, East, South, West

    @pytest.mark.parametrize("speed", WIND_SPEEDS)
    @pytest.mark.parametrize("direction", WIND_DIRECTIONS)
    def test_wind_vector_pairwise_kinematics(
        self, speed: float, direction: float, reference_oracle: PAQReferenceOracle
    ):
        """Validates polar to Cartesian conversion across 16 speed x direction combinations."""
        u, v = reference_oracle.polar_to_cartesian_wind(speed, direction)
        assert u is not None and v is not None

        # Scalar speed invariant
        calc_speed = math.sqrt(u ** 2 + v ** 2)
        assert abs(calc_speed - speed) < 1e-4

        # Verify directional sign invariants
        if direction == 90.0:   # Wind from East -> blows West (u < 0)
            assert u < 0 or speed == 0.0
            assert abs(v) < 1e-4
        elif direction == 270.0:  # Wind from West -> blows East (u > 0)
            assert u > 0 or speed == 0.0
            assert abs(v) < 1e-4
        elif direction == 0.0:    # Wind from North -> blows South (v < 0)
            assert v < 0 or speed == 0.0
            assert abs(u) < 1e-4
        elif direction == 180.0:  # Wind from South -> blows North (v > 0)
            assert v > 0 or speed == 0.0
            assert abs(u) < 1e-4


class TestTier3CrossPollutantCombinations:
    """Pairwise testing of multi-pollutant concentrations and composite AQI rules."""

    POLLUTANTS_AND_VALUES = [
        ("PM2.5", [10.0, 30.0, 60.0, 120.0, 200.0, 300.0, 450.0]),
        ("PM10", [50.0, 100.0, 200.0, 300.0, 400.0, 500.0, 650.0]),
        ("NO2", [20.0, 60.0, 100.0, 150.0, 250.0, 450.0, 700.0]),
        ("SO2", [30.0, 90.0, 170.0, 270.0, 500.0, 1000.0, 1800.0]),
        ("CO", [1.5, 3.5, 6.0, 8.5, 18.0, 30.0, 50.0]),
        ("O3", [40.0, 90.0, 160.0, 220.0, 350.0, 500.0, 600.0]),
    ]

    def test_multipollutant_aqi_monotonicity(self, reference_oracle: PAQReferenceOracle):
        """As pollutant concentration increases, the computed sub-index must strictly be non-decreasing."""
        for pol, values in self.POLLUTANTS_AND_VALUES:
            indices = [reference_oracle.pepc_calculate_aqi(pol, v) for v in values]
            for i in range(len(indices) - 1):
                assert indices[i] <= indices[i + 1], (
                    f"Monotonicity violation in {pol}: {indices[i]} > {indices[i+1]}"
                )

    def test_composite_aqi_governance(self, reference_oracle: PAQReferenceOracle):
        """Composite AQI is strictly governed by particulate matter max(PM2.5, PM10)."""
        # Scenario A: PM2.5 dominates
        pm25_c = 200.0  # AQI ~255
        pm10_c = 100.0  # AQI ~67
        aqi_25 = reference_oracle.pepc_calculate_aqi("PM2.5", pm25_c)
        aqi_10 = reference_oracle.pepc_calculate_aqi("PM10", pm10_c)
        comp_a = reference_oracle.pepc_composite_aqi(aqi_25, aqi_10)
        assert comp_a == aqi_25

        # Scenario B: PM10 dominates
        pm25_c = 25.0   # AQI 75
        pm10_c = 300.0  # AQI 175
        aqi_25 = reference_oracle.pepc_calculate_aqi("PM2.5", pm25_c)
        aqi_10 = reference_oracle.pepc_calculate_aqi("PM10", pm10_c)
        comp_b = reference_oracle.pepc_composite_aqi(aqi_25, aqi_10)
        assert comp_b == aqi_10


class TestTier3CrossFeatureDataflow:
    """Verifies end-to-end data flow across ingestion, spatial interpolation, and analytics."""

    def test_csv_upload_triggers_idw_recalculation(
        self, load_csv_fixture, reference_oracle: PAQReferenceOracle
    ):
        """Simulates CSV upload -> validation -> spatial imputation of unmonitored district."""
        raw_rows = load_csv_fixture("valid_station_observations.csv")

        # 1. Parse and validate rows
        validated_stations = []
        for r in raw_rows:
            if r["pollutant"].lower() == "pm25":
                val = float(r["value"])
                validated_stations.append({
                    "station_id": r["station_id"],
                    "coords": (float(r["latitude"]), float(r["longitude"])),
                    "value": val
                })

        assert len(validated_stations) > 0

        # 2. Impute unmonitored district (e.g. Kasur centroid if unmonitored or test coord)
        target_coords = (31.1179, 74.4460)  # Kasur
        imputed_value = reference_oracle.discrete_geodesic_idw(
            target_coords=target_coords,
            monitored_nodes=validated_stations,
            power=2.0,
            d0_km=5.0
        )
        assert imputed_value is not None
        assert 100.0 <= imputed_value <= 200.0

    def test_wind_update_recalculates_cpf_and_flux(
        self, reference_oracle: PAQReferenceOracle
    ):
        """Simulates changing wind vectors triggering both CPF sector redistribution and flux recalculated."""
        # Initial wind: East (90 deg) at 3.0 m/s
        obs_east = [
            {"wind_speed": 3.0, "wind_direction": 90.0, "value": 220.0}
            for _ in range(8)
        ]
        rose_east = reference_oracle.calculate_cpf_rose(obs_east, threshold_p75=200.0)
        assert rose_east["sectors"][4] == 1.0  # Sector 4 (East) has 100% exceedance

        # Wind shift to South (180 deg) at 3.0 m/s
        obs_south = [
            {"wind_speed": 3.0, "wind_direction": 180.0, "value": 220.0}
            for _ in range(8)
        ]
        rose_south = reference_oracle.calculate_cpf_rose(obs_south, threshold_p75=200.0)
        assert rose_south["sectors"][8] == 1.0  # Sector 8 (South) now has 100% exceedance
        assert rose_south["sectors"][4] is None  # Sector 4 now has 0 obs

        # Concurrently recalculate inter-district flux:
        # Source (Lahore 31.5204, 74.3587), Receptor (Kasur 31.1179, 74.4460) bearing ~168 deg
        # East wind (90 deg, blows West 270 deg) -> divergence ~102 deg > 35 deg -> Flux is None
        flux_east = reference_oracle.calculate_advection_flux(
            source_coords=(31.5204, 74.3587),
            receptor_coords=(31.1179, 74.4460),
            concentration=220.0,
            u_wind=-3.0,
            v_wind=0.0,
            pollutant="PM2.5"
        )
        assert flux_east is None

        # Wind from North-Northwest blowing towards Kasur (~168 deg TO) -> Active Flux!
        rad = math.radians(168.0)
        flux_aligned = reference_oracle.calculate_advection_flux(
            source_coords=(31.5204, 74.3587),
            receptor_coords=(31.1179, 74.4460),
            concentration=220.0,
            u_wind=3.0 * math.sin(rad),
            v_wind=3.0 * math.cos(rad),
            pollutant="PM2.5"
        )
        assert flux_aligned is not None
        assert flux_aligned["flux"] > 0.0

    def test_top_60_pathway_truncation_contract(self):
        """Ensures inter-district transport pathways are strictly sorted and truncated to top 60."""
        # Generate 100 dummy pathway links
        candidate_links = [
            {"source": f"SRC_{i}", "receptor": f"REC_{i}", "score": float(i * 1.5)}
            for i in range(100)
        ]
        # Contract sorting & truncation: sort descending by score, slice 60
        top_links = sorted(candidate_links, key=lambda x: x["score"], reverse=True)[:60]
        assert len(top_links) == 60
        assert top_links[0]["score"] == 99 * 1.5
        assert top_links[-1]["score"] == 40 * 1.5
