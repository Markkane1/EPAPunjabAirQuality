import asyncio
import io
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

import httpx
from httpx import ASGITransport
from src.api.main import create_application

app = create_application()

async def test_all_adversarial():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # 1. Test Physical AQI Guard variations
        for p in ["AQI", "aqi", "Aqi", " aqi ", "AQI "]:
            resp = await client.get(f"/api/v1/analytics/flux?pollutant={p}")
            assert resp.status_code == 400, f"Expected 400 for {p}, got {resp.status_code}"
            assert ("physically undefined" in resp.json()["detail"].lower() or 
                    "mass conservation" in resp.json()["detail"].lower())
        print("1. AQI guard passed across all case variations.")

        # Valid pollutants
        for p in ["PM2.5", "pm25", "PM10", "pm10", "NO2", "SO2", "CO", "O3"]:
            resp = await client.get(f"/api/v1/analytics/flux?pollutant={p}")
            assert resp.status_code == 200, f"Expected 200 for {p}, got {resp.status_code}: {resp.text}"
        print("2. Valid physical pollutants passed advection flux.")

        # 2. Test CPF small-sample suppression and district lookup
        resp = await client.get("/api/v1/analytics/cpf?district=Lahore&pollutant=PM2.5")
        assert resp.status_code == 200
        data = resp.json()
        for sec in data["sectors"]:
            nk = sec["total_hours"]
            prob = sec["cpf_probability"]
            if nk < 6:
                assert prob is None, f"Suppression failed: Nk={nk}, prob={prob}"
            else:
                assert prob is not None, f"Expected prob for Nk={nk}"
        print("3. CPF small sample suppression verified on Lahore.")

        # Nonexistent district
        resp = await client.get("/api/v1/analytics/cpf?district=Atlantis&pollutant=PM2.5")
        assert resp.status_code == 400
        assert "unknown administrative district" in resp.json()["detail"].lower()
        print("4. Unknown district in CPF correctly returns HTTP 400.")

        # 3. Test SSE stream headers & structure
        resp = await client.get("/api/v1/stream/live?max_events=1")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
        assert resp.headers.get("cache-control") == "no-cache"
        assert resp.headers.get("connection") == "keep-alive"
        assert resp.headers.get("x-accel-buffering") == "no"
        body = resp.text
        assert "event: hourly_update\n" in body
        assert "data: {" in body
        print("5. SSE stream headers and event structure verified.")

        # 4. Test Spatial Surface resolution validation
        resp_invalid_low = await client.get("/api/v1/spatial/surface?resolution=0")
        assert resp_invalid_low.status_code == 422
        resp_invalid_high = await client.get("/api/v1/spatial/surface?resolution=51")
        assert resp_invalid_high.status_code == 422
        resp_valid = await client.get("/api/v1/spatial/surface?resolution=10")
        assert resp_valid.status_code == 200
        print("6. Spatial resolution bounds (1..50) enforced by FastAPI validation schema.")

        # 5. Test CSV upload with DLQ quarantine
        csv_content = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value,wind_speed,wind_direction\n"
            "2026-11-10 12:00,STN01,Valid Station,Lahore,31.5204,74.3587,pm25,45.2,3.5,120\n"
            "2026-11-10 12:00,STN02,Bad Lat Station,Lahore,99.9999,74.3587,pm25,45.2,3.5,120\n"
            "2026-11-10 12:00,STN03,Negative Val,Lahore,31.5204,74.3587,pm25,-10.0,3.5,120\n"
            "2026-11-10 12:00,STN04,Bad Pollutant,Lahore,31.5204,74.3587,unknown_pol,45.2,3.5,120\n"
            "2026-11-10 12:00,STN05,Valid Station 2,Faisalabad,31.4504,73.1350,pm10,85.0,2.1,90\n"
        ).encode("utf-8")
        files = {"file": ("mixed_dataset.csv", csv_content, "text/csv")}
        resp_csv = await client.post("/api/v1/ingest/csv", files=files)
        assert resp_csv.status_code == 200
        csv_data = resp_csv.json()
        assert csv_data["status"] == "partial_quarantine"
        assert csv_data["total_rows"] == 5
        assert csv_data["valid_rows"] == 2
        assert csv_data["quarantined_rows"] == 3
        assert len(csv_data["quarantine_records"]) == 3
        # 7. Test dynamic reflection after CSV upload
        new_station_id = "STN_TEST_DYNAMIC_999"
        csv_dynamic = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value,wind_speed,wind_direction\n"
            f"2026-11-11 10:00,{new_station_id},Dynamic Reviewer Test Station,Lahore,31.5204,74.3587,pm25,123.4,4.2,180\n"
        ).encode("utf-8")
        files = {"file": ("dynamic_test.csv", csv_dynamic, "text/csv")}
        resp_upload = await client.post("/api/v1/ingest/csv", files=files)
        assert resp_upload.status_code == 200
        up_data = resp_upload.json()
        assert up_data["status"] == "success"
        assert up_data["valid_rows"] == 1

        # Check meta/stations for new station
        resp_stns = await client.get("/api/v1/meta/stations?district=Lahore")
        assert resp_stns.status_code == 200
        stn_ids = [s["id"] for s in resp_stns.json()]
        assert new_station_id in stn_ids, f"Newly ingested station {new_station_id} should be in stations list"
        print("8. Dynamic station addition and repository reflection verified.")

        # 8. Test SSE keepalive ping generation directly
        from src.api.routes.stream import sse_event_generator
        from unittest.mock import AsyncMock, MagicMock
        mock_req = MagicMock()
        mock_req.is_disconnected = AsyncMock(side_effect=[False, False, True])
        obs_svc = app.state.observation_service
        
        # We can simulate time step
        import time
        from unittest.mock import patch
        
        events = []
        gen = sse_event_generator(mock_req, obs_svc, max_events=5)
        # 1st event is initial snapshot
        e1 = await gen.__anext__()
        assert "event: hourly_update" in e1
        # 9. Test SSE keepalive ping generation explicitly
        simulated_times = [0.0, 16.0]  # First check: 0.0, second check: 16.0s later
        time_idx = 0
        def fake_time():
            nonlocal time_idx
            t = simulated_times[min(time_idx, len(simulated_times) - 1)]
            time_idx += 1
            return t

        loop = asyncio.get_event_loop()
        with patch.object(loop, "time", side_effect=fake_time):
            with patch("asyncio.sleep", AsyncMock()):
                gen = sse_event_generator(mock_req, obs_svc, max_events=None)
                # First event is snapshot
                snap_event = await gen.__anext__()
                assert "event: hourly_update" in snap_event
                # Next event after 16s is keepalive ping
                keepalive_event = await gen.__anext__()
                assert keepalive_event == ": keepalive\n\n", f"Expected keepalive, got {keepalive_event!r}"
                print("10. SSE 15s keepalive ping ': keepalive\\n\\n' explicitly verified.")

if __name__ == "__main__":
    asyncio.run(test_all_adversarial())
