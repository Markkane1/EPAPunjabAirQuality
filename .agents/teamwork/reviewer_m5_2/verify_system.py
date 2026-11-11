import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

import httpx
from httpx import ASGITransport
from src.api.main import create_application

async def run_checks():
    app = create_application()
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # 1. Root & index.html
        r = await client.get("/")
        assert r.status_code == 200, f"GET / failed: {r.status_code}"
        assert "Punjab Air Quality" in r.text
        assert "zone-1-header" in r.text or "banner" in r.text

        r_idx = await client.get("/index.html")
        assert r_idx.status_code == 200, f"GET /index.html failed: {r_idx.status_code}"
        assert r_idx.text == r.text

        # 2. Static assets
        paths = [
            "/static/css/tokens.css",
            "/static/js/app.js",
            "/static/js/api.js",
            "/static/js/canvas.js",
            "/static/js/geo.js",
            "/static/js/ui.js",
            "/static/data/geo_boundaries.json",
            "/static/data/districts.json",
            "/static/data/stations.json",
            "/static/data/airports.json",
            "/static/data/baseline_data.json",
        ]
        for path in paths:
            res = await client.get(path)
            assert res.status_code == 200, f"Failed static: {path} -> {res.status_code}"
            assert len(res.content) > 0, f"Empty static: {path}"
            print(f"Static OK: {path} ({len(res.content)} bytes)")

        # 3. REST endpoints
        r_dist = await client.get("/api/v1/meta/districts")
        assert r_dist.status_code == 200
        districts = r_dist.json()
        assert len(districts) == 41, f"Expected 41 districts, got {len(districts)}"
        print(f"API Districts OK: {len(districts)} districts")

        r_st = await client.get("/api/v1/meta/stations")
        assert r_st.status_code == 200
        stations = r_st.json()
        assert len(stations) >= 70
        print(f"API Stations OK: {len(stations)} stations")

        r_cur = await client.get("/api/v1/observations/current?pollutant=PM2.5")
        assert r_cur.status_code == 200
        cur_data = r_cur.json()
        assert "districts" in cur_data
        print("API Current Obs OK")

        # 4. Physical AQI guard
        r_flux_aqi = await client.get("/api/v1/analytics/flux?pollutant=AQI")
        assert r_flux_aqi.status_code == 400, f"Expected 400 for AQI flux, got {r_flux_aqi.status_code}"
        detail_msg = r_flux_aqi.json().get("detail", "")
        print(f"Physical Guard AQI Flux rejected with 400 OK: {detail_msg}")

        r_flux_pm = await client.get("/api/v1/analytics/flux?pollutant=PM2.5")
        assert r_flux_pm.status_code == 200
        print(f"API Flux PM2.5 OK: {len(r_flux_pm.json().get('top_pathways', []))} pathways")

        print("\n=== ALL COMPONENT INTEGRATION CHECKS VERIFIED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(run_checks())
