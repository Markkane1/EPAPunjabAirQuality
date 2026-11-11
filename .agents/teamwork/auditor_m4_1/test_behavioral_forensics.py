"""
Independent Behavioral Runtime Verification Script for Milestone M4.
Forensic Auditor: auditor_m4_1
"""
import asyncio
import json
from pathlib import Path
import random
import sys
import uuid

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import httpx
from httpx import ASGITransport

from src.api.main import create_application


async def run_forensic_probes():
    app = create_application()
    transport = ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://audit-server") as client:
        # 1. Physical AQI Guard Checks
        print("=== PROBE 1: Physical AQI Guard Enforcement ===")
        for pol in ["AQI", "aqi", " AQI ", "Aqi"]:
            res = await client.get(f"/api/v1/analytics/flux?pollutant={pol}")
            print(f"GET /analytics/flux?pollutant={pol!r} -> HTTP {res.status_code}")
            assert res.status_code == 400
            data = res.json()
            assert "detail" in data
            assert "AQI" in data["detail"]
            assert "dimensionless" in data["detail"]
            print(f"  Guarded with detail: {data['detail']}")

        # 2. Advection Flux with Dynamic Species
        print("\n=== PROBE 2: Advection Flux with Mass Pollutant Species ===")
        for species in ["PM2.5", "PM10", "NO2", "SO2"]:
            res = await client.get(f"/api/v1/analytics/flux?pollutant={species}&limit=12")
            assert res.status_code == 200
            data = res.json()
            print(f"Pollutant: {species:5s} | Link Count: {len(data['links']):2d} | Net Balance Districts: {len(data['net_balance'])}")
            assert len(data["links"]) <= 12
            if len(data["links"]) > 0:
                first = data["links"][0]
                assert "source_district" in first
                assert "receptor_district" in first
                assert "flux" in first
                assert "omega" in first
                print(f"  Top Corridor: {first['source_district']} -> {first['receptor_district']} (Flux: {first['flux']:.3f}, Divergence: {first['divergence_deg']} deg)")

        # 3. Dynamic Spatial Surface Grid Calculations
        print("\n=== PROBE 3: Dynamic Spatial Surface Grid Computations ===")
        res_5 = await client.get("/api/v1/spatial/surface?resolution=5&pollutant=PM2.5")
        assert res_5.status_code == 200
        grid_5 = res_5.json()

        res_12 = await client.get("/api/v1/spatial/surface?resolution=12&pollutant=PM2.5")
        assert res_12.status_code == 200
        grid_12 = res_12.json()

        print(f"Step 5  -> grid_width: {grid_5['grid_width']}, grid_height: {grid_5['grid_height']}, rows: {len(grid_5['grid_matrix'])}, cols: {len(grid_5['grid_matrix'][0])}")
        print(f"Step 12 -> grid_width: {grid_12['grid_width']}, grid_height: {grid_12['grid_height']}, rows: {len(grid_12['grid_matrix'])}, cols: {len(grid_12['grid_matrix'][0])}")
        assert grid_5["resolution"] == 5
        assert grid_12["resolution"] == 12
        assert grid_5["grid_width"] != grid_12["grid_width"]
        assert grid_5["grid_height"] != grid_12["grid_height"]
        assert len(grid_5["grid_matrix"]) > len(grid_12["grid_matrix"])

        # 4. Dynamic CPF Threshold Variation
        print("\n=== PROBE 4: Dynamic CPF Threshold Variation ===")
        res_default = await client.get("/api/v1/analytics/cpf?district=Lahore&pollutant=PM2.5")
        assert res_default.status_code == 200
        cpf_default = res_default.json()

        res_custom_high = await client.get("/api/v1/analytics/cpf?district=Lahore&pollutant=PM2.5&threshold=350.0")
        assert res_custom_high.status_code == 200
        cpf_high = res_custom_high.json()

        print(f"Lahore Default P75 Threshold: {cpf_default['threshold_p75']:.2f} | Sectors Count: {len(cpf_default['sectors'])}")
        print(f"Lahore Custom 350.0 Threshold: {cpf_high['threshold_p75']:.2f} | Sectors Count: {len(cpf_high['sectors'])}")
        assert cpf_default["threshold_p75"] != cpf_high["threshold_p75"]

        # 5. Novel Dynamic CSV Upload & State Update Verification
        print("\n=== PROBE 5: Novel Dynamic CSV Upload & State Update Verification ===")
        stn_unique_id = f"FORENSIC_{uuid.uuid4().hex[:8]}"
        stn_name = f"Forensic Station {random.randint(1000, 9999)}"
        novel_csv = (
            f"station_id,station_name,district,latitude,longitude,pollutant,value,timestamp,wind_speed,wind_direction\n"
            f"{stn_unique_id},{stn_name},Lahore,31.5204,74.3587,PM2.5,245.5,2026-11-09T23:00:00Z,3.5,135.0\n"
            f"{stn_unique_id},{stn_name},Lahore,31.5204,74.3587,PM10,380.0,2026-11-09T23:00:00Z,3.5,135.0\n"
        )
        files = {"file": ("novel_dataset.csv", novel_csv.encode("utf-8"), "text/csv")}
        upload_res = await client.post("/api/v1/ingest/csv", files=files)
        assert upload_res.status_code == 200
        upload_data = upload_res.json()
        print(f"CSV Ingest Status: {upload_data['status']}")
        print(f"Valid Rows: {upload_data['valid_rows']}, Quarantined: {upload_data['quarantined_rows']}")
        assert upload_data["status"] == "success"
        assert upload_data["valid_rows"] == 2
        assert upload_data["quarantined_rows"] == 0

        # Query GET /api/v1/meta/stations
        meta_res = await client.get("/api/v1/meta/stations")
        assert meta_res.status_code == 200
        all_stns = meta_res.json()
        matching_stn = next((s for s in all_stns if s["id"] == stn_unique_id), None)
        print(f"Query GET /meta/stations -> Found {stn_unique_id}: {matching_stn is not None}")
        assert matching_stn is not None
        assert matching_stn["name"] == stn_name
        assert matching_stn["latitude"] == 31.5204
        assert matching_stn["longitude"] == 74.3587

        # Query GET /api/v1/observations/current
        obs_res = await client.get("/api/v1/observations/current")
        assert obs_res.status_code == 200
        obs_data = obs_res.json()
        print(f"Query GET /observations/current keys: {list(obs_data.keys())}")
        print(f"Provincial Summary Mean AQI: {obs_data['provincial_summary']['mean_aqi']}")
        assert "districts" in obs_data
        assert "provincial_summary" in obs_data

        # Also verify directly on observation service that domain snapshot contains the station
        obs_service = app.state.observation_service
        snapshot_dto = obs_service.get_current_snapshot()
        stn_match = next((s for s in snapshot_dto.stations if s.station_id == stn_unique_id), None)
        print(f"ObservationService domain snapshot -> Found {stn_unique_id}: {stn_match is not None}")
        assert stn_match is not None
        assert stn_match.pm25 == 245.5
        assert stn_match.pm10 == 380.0
        print(f"  Domain Snapshot reading: AQI={stn_match.aqi}, PM2.5={stn_match.pm25}, PM10={stn_match.pm10}")

        # 6. Dead-Letter Quarantine CSV Upload Verification
        print("\n=== PROBE 6: Dead-Letter Quarantine Isolation ===")
        corrupt_csv = (
            "station_id,station_name,district,latitude,longitude,pollutant,value,timestamp\n"
            "INVALID_STN,Corrupt Station,Lahore,999.0,999.0,PM2.5,-100.0,INVALID_DATE\n"
            f"{stn_unique_id},{stn_name},Lahore,31.5204,74.3587,PM2.5,50.0,2026-11-09T22:00:00Z\n"
        )
        bad_files = {"file": ("corrupted.csv", corrupt_csv.encode("utf-8"), "text/csv")}
        bad_res = await client.post("/api/v1/ingest/csv", files=bad_files)
        assert bad_res.status_code == 200
        bad_report = bad_res.json()
        print(f"Quarantine Status: {bad_report['status']}")
        print(f"Valid Rows: {bad_report['valid_rows']}, Quarantined: {bad_report['quarantined_rows']}")
        assert bad_report["status"] == "partial_quarantine"
        assert bad_report["quarantined_rows"] == 1
        assert len(bad_report["quarantined_records"]) == 1
        first_q = bad_report["quarantined_records"][0]
        print(f"  Quarantine Record: Row {first_q['row_number']}, Error: {first_q['error_message']}")

        # 7. Adversarial Query Stress Testing
        print("\n=== PROBE 7: Adversarial Edge Cases & Boundary Conditions ===")
        # Non-existent district in CPF
        bad_district_res = await client.get("/api/v1/analytics/cpf?district=Atlantis&pollutant=PM2.5")
        print(f"GET /analytics/cpf?district=Atlantis -> HTTP {bad_district_res.status_code}")
        assert bad_district_res.status_code == 400

        # Boundary resolution
        res_zero = await client.get("/api/v1/spatial/surface?resolution=0")
        print(f"GET /spatial/surface?resolution=0 -> HTTP {res_zero.status_code}")
        assert res_zero.status_code == 422  # Pydantic validation ge=1

        # Transboundary analysis
        res_tb = await client.get("/api/v1/analytics/transboundary")
        print(f"GET /analytics/transboundary -> HTTP {res_tb.status_code}")
        assert res_tb.status_code == 200
        tb_data = res_tb.json()
        print(f"  Net Flux: {tb_data['net_transboundary_flux']}, Status: {tb_data['status']}, Border Districts: {len(tb_data['border_districts'])}, Border Nodes: {len(tb_data['border_samples'])}")
        assert len(tb_data["border_samples"]) == 39

        # SSE Stream Endpoint Check
        print("\n=== PROBE 8: Server-Sent Events (SSE) Live Feed Contract ===")
        stream_res = await client.get("/api/v1/stream/live?max_events=1")
        print(f"GET /stream/live?max_events=1 -> HTTP {stream_res.status_code}")
        assert stream_res.status_code == 200
        assert "text/event-stream" in stream_res.headers.get("content-type", "")
        body = stream_res.text
        assert "event: hourly_update" in body
        assert "data: " in body
        print(f"  SSE Initial Event Received: {body[:100]}...")

        print("\n=======================================================")
        print("ALL 8 FORENSIC RUNTIME CHECKS PASSED WITH ZERO ERRORS!")
        print("=======================================================")


if __name__ == "__main__":
    asyncio.run(run_forensic_probes())
