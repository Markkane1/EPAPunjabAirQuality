import asyncio
from httpx import AsyncClient, ASGITransport
from src.api.main import app

async def test():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/observations/cross-border")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        print("API Status:", data.get("status"))
        print("Total Reference Cities Returned:", data.get("count"))
        print("-" * 75)
        for c in data.get("cities", []):
            print(f"{c['city']:16} | {c['state']:16} | {c['distance_km']:3.0f} km | PEPC AQI: {c['pepc_aqi']:3d} | {c['status']}")
        print("-" * 75)

if __name__ == "__main__":
    asyncio.run(test())
