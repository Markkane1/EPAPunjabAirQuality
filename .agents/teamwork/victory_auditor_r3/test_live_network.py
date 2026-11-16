import sys, os
sys.path.insert(0, os.path.abspath("."))
import asyncio
from src.pipelines.metar import MetarIngestionWorker
from src.pipelines.cams import CamsIngestionWorker
from src.pipelines.iqair import IQAirIngestionWorker

async def test_live_network():
    print("Testing live NOAA METAR worker...")
    metar = MetarIngestionWorker()
    try:
        data = await metar.fetch_data(ids=["OPLA", "OPRN", "OPST"], hours=3)
        reports = metar.parse_and_validate(data)
        print(f"METAR live fetch succeeded: {len(reports)} observations parsed across {list(set(r['station_id'] for r in reports))}")
    except Exception as e:
        print(f"METAR live fetch note: {e}")

    print("\nTesting live CAMS/Open-Meteo...")
    cams = CamsIngestionWorker(worker_mode="live")
    try:
        cams_res = await cams.fetch_data()
        print(f"CAMS live fetch result: {cams_res}")
    except Exception as e:
        print(f"CAMS live fetch note: {e}")

    print("\nTesting live IQAir/Open-Meteo Cross-Border...")
    iqair = IQAirIngestionWorker(worker_mode="live")
    try:
        iq_res = await iqair.fetch_data()
        print(f"IQAir live fetch result: {len(iq_res)} cities retrieved: {[c.get('city') for c in iq_res]}")
    except Exception as e:
        print(f"IQAir live fetch note: {e}")

if __name__ == "__main__":
    asyncio.run(test_live_network())
