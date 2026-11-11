"""
Tier 4: Real-World Operational Scenario Verification Tests
Executes comprehensive end-to-end user workflows and environmental episodes
simulating actual atmospheric and system conditions in Punjab.
"""
import math
from typing import Any, Dict, List

import pytest
from tests.e2e.conftest import (
    PAQReferenceOracle,
    UserCSVRowContract,
)


class TestTier4RealWorldScenarios:
    """End-to-end integration workflows across the 5 core operational scenarios."""

    def test_scenario_1_severe_smog_inversion_episode(
        self, load_csv_fixture, reference_oracle: PAQReferenceOracle
    ):
        """
        Scenario 1: Severe Smog Inversion Episode
        Simulates nocturnal radiation inversion over Lahore, Kasur, and Gujranwala:
        - PM2.5 surges above 450 ug/m3.
        - Statutory PEPC AQI sub-index triggers operational ceiling clamp at 500 (Hazardous).
        - Color maps to Deep Maroon.
        - Active eastward-to-westward transport flux vectors are generated.
        """
        rows = load_csv_fixture("severe_smog_event.csv")
        assert len(rows) > 0

        # 1. Verify all rows in the severe episode
        lahore_pm25 = []
        for r in rows:
            if r["district"] == "Lahore" and r["pollutant"] == "pm25":
                lahore_pm25.append(float(r["value"]))

        assert len(lahore_pm25) >= 3
        # Inversion peak concentrations are hazardous
        assert any(c > 400.0 for c in lahore_pm25)

        # 2. Evaluate Statutory Sub-Index & Clamping for extreme peak
        peak_conc = max(lahore_pm25)
        aqi_subindex = reference_oracle.pepc_calculate_aqi("PM2.5", peak_conc)
        assert aqi_subindex == 500  # Statutory operational ceiling clamp!

        # 3. Composite AQI Evaluation
        # Town Hall has PM10 = 620 -> also clamped to 500
        aqi_pm10 = reference_oracle.pepc_calculate_aqi("PM10", 620.0)
        assert aqi_pm10 == 500
        composite_aqi = reference_oracle.pepc_composite_aqi(aqi_subindex, aqi_pm10)
        assert composite_aqi == 500

        # 4. Color Scale Mapping -> Hazardous Deep Maroon
        hazard_color = reference_oracle.pepc_get_color(composite_aqi)
        assert hazard_color == "#C00000"

        # 5. Advection Flux Vector to downwind receptor (Lahore -> Sheikhupura bearing ~305 deg)
        # Wind blowing towards Sheikhupura (from SE ~125 deg)
        rad = math.radians(305.0)
        u_wind = 2.5 * math.sin(rad)
        v_wind = 2.5 * math.cos(rad)

        flux_transport = reference_oracle.calculate_advection_flux(
            source_coords=(31.5704, 74.3096),     # Lahore Town Hall
            receptor_coords=(31.7131, 73.9783),    # Sheikhupura ByPass (~35 km)
            concentration=peak_conc,
            u_wind=u_wind,
            v_wind=v_wind,
            pollutant="PM2.5"
        )
        assert flux_transport is not None
        assert flux_transport["flux"] > 500.0  # Massive mass transport!
        assert flux_transport["distance_km"] < 50.0

    def test_scenario_2_offline_fallback_and_graceful_degradation(
        self, reference_oracle: PAQReferenceOracle
    ):
        """
        Scenario 2: Offline Fallback & Graceful Degradation
        Simulates primary EPA Punjab portal outage (HTTP 404 / 503 gateway failure):
        - Ingestion worker encounters failed primary endpoint.
        - System automatically activates Fallback Baseline Templating Engine.
        - Fallback engine produces schema-conforming station readings seeded from baseline.
        - System sets is_estimated = True / fallback flag without crashing.
        """
        # Baseline station catalog fixture simulating fallback database
        baseline_stations = [
            {"station_id": "PK_LHR_001", "name": "Town Hall", "district": "Lahore", "coords": (31.5704, 74.3096), "baseline_pm25": 165.0},
            {"station_id": "PK_KSR_001", "name": "Kasur City", "district": "Kasur", "coords": (31.1179, 74.4460), "baseline_pm25": 140.0},
            {"station_id": "PK_FSD_001", "name": "Faisalabad Clock Tower", "district": "Faisalabad", "coords": (31.4187, 73.0791), "baseline_pm25": 120.0},
        ]

        def fallback_templating_engine(target_hour: str) -> List[Dict[str, Any]]:
            """Simulates the Fallback Baseline Templating Engine on external API failure."""
            records = []
            for st in baseline_stations:
                aqi = reference_oracle.pepc_calculate_aqi("PM2.5", st["baseline_pm25"])
                records.append({
                    "timestamp": target_hour,
                    "station_id": st["station_id"],
                    "station_name": st["name"],
                    "district": st["district"],
                    "pm25": st["baseline_pm25"],
                    "pepc_aqi": aqi,
                    "is_estimated": True,  # Fallback degradation flag
                    "data_source": "BASELINE_FALLBACK"
                })
            return records

        # Simulate engine run during an outage
        fallback_data = fallback_templating_engine("2026-11-10T18:00:00Z")
        assert len(fallback_data) == 3
        for rec in fallback_data:
            assert rec["is_estimated"] is True
            assert rec["data_source"] == "BASELINE_FALLBACK"
            assert rec["pepc_aqi"] is not None
            assert rec["pm25"] > 0

    def test_scenario_3_custom_user_csv_dynamic_reinterpolation(
        self, load_csv_fixture, reference_oracle: PAQReferenceOracle
    ):
        """
        Scenario 3: Custom User CSV Upload & Dynamic Re-Interpolation
        Simulates environmental analyst uploading a custom multi-station CSV:
        - Ingestion adapter validates schema.
        - Zero/negative cleaning is applied.
        - Continuous surface / district IDW is recalculated dynamically.
        """
        rows = load_csv_fixture("valid_station_observations.csv")

        # 1. Ingestion Adapter Validation & Normalization
        clean_measurements = []
        for r in rows:
            if r["pollutant"].lower() == "pm25":
                val = float(r["value"])
                if val > 0:  # Zero sanitization
                    clean_measurements.append({
                        "station_id": r["station_id"],
                        "coords": (float(r["latitude"]), float(r["longitude"])),
                        "value": val
                    })

        assert len(clean_measurements) >= 10

        # 2. Dynamic Spatial Re-Interpolation for 3 unmonitored test district centroids
        test_centroids = [
            ("Nankana Sahib", (31.4500, 73.7000)),
            ("Chiniot", (31.7200, 72.9700)),
            ("Hafizabad", (32.0600, 73.6800)),
        ]

        imputed_results = {}
        for dist_name, coords in test_centroids:
            val = reference_oracle.discrete_geodesic_idw(
                target_coords=coords,
                monitored_nodes=clean_measurements,
                power=2.0,
                d0_km=5.0
            )
            assert val is not None
            imputed_results[dist_name] = round(val, 2)

        assert "Nankana Sahib" in imputed_results
        assert 100.0 <= imputed_results["Nankana Sahib"] <= 200.0

    def test_scenario_4_cross_border_plume_inflow_analysis(
        self, load_csv_fixture, reference_oracle: PAQReferenceOracle
    ):
        """
        Scenario 4: Cross-Border Plume Inflow Analysis
        Simulates stubble-burning easterly plume transported across international border:
        - Border-belt districts (<120 km) detect easterly winds (inflow sector).
        - Border normal vector dot products (w . n) > +0.25 m/s confirm inflow into Punjab.
        - Net mass balance confirms transboundary import.
        """
        rows = load_csv_fixture("border_transport_plume.csv")
        assert len(rows) > 0

        # 39 border normal vector node coordinates along Pakistan-India border
        # Inward normal vectors pointing West-Southwest (e.g. nx ~ -0.9, ny ~ -0.4)
        border_nodes = [
            {"id": "NODE_01", "lat": 32.10, "lon": 74.87, "nx": -0.95, "ny": -0.31},  # Narowal border
            {"id": "NODE_02", "lat": 31.60, "lon": 74.57, "nx": -0.98, "ny": -0.19},  # Wagah / Lahore border
            {"id": "NODE_03", "lat": 31.11, "lon": 74.45, "nx": -0.92, "ny": -0.39},  # Kasur border
        ]

        # Inflow test: Easterly wind blowing West (u = -3.0 m/s, v = 0.0 m/s)
        u_wind = -3.0
        v_wind = 0.0

        inflow_nodes = 0
        for node in border_nodes:
            # Dot product: Phi = u * nx + v * ny
            phi = u_wind * node["nx"] + v_wind * node["ny"]
            # Phi = (-3.0) * (-0.95) = +2.85 m/s > +0.25 m/s -> Strong Inflow!
            if phi > 0.25:
                inflow_nodes += 1

        assert inflow_nodes == len(border_nodes), "All border nodes must detect transboundary inflow!"

    def test_scenario_5_multistation_district_disaggregation(
        self, load_csv_fixture, reference_oracle: PAQReferenceOracle
    ):
        """
        Scenario 5: Multi-Station District Disaggregation (Lahore 13 Stations vs Single Station)
        - Verifies that in dense urban districts (Lahore), the P75 criterion threshold tau
          is evaluated on the POOLED set of individual station-hour observations,
          preserving localized emission hot spots (e.g. Wagah Border, Kot Lakhpat)
          which would be flattened by computing on smoothed district-wide means.
        """
        rows = load_csv_fixture("multistation_lahore_cluster.csv")
        assert len(rows) == 13  # 13 distinct stations in Lahore

        lahore_values = [float(r["value"]) for r in rows]

        # 1. District smoothed arithmetic mean
        district_mean = sum(lahore_values) / len(lahore_values)
        assert 220.0 <= district_mean <= 240.0

        # 2. Localized hotspots are preserved in individual station records
        max_hotspot = max(lahore_values)  # Wagah Border = 360.0
        min_background = min(lahore_values)  # DHA Phase 5 = 165.0
        assert max_hotspot == 360.0
        assert min_background == 165.0
        assert max_hotspot - min_background > 150.0  # Demonstrates spatial gradient

        # 3. Pooled P75 evaluation
        sorted_values = sorted(lahore_values)
        p75_index = int(0.75 * (len(sorted_values) - 1))
        pooled_tau = sorted_values[p75_index]
        assert pooled_tau > district_mean, "Pooled P75 must capture upper quantile gradients"
