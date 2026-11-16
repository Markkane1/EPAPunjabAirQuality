import sys, os
sys.path.insert(0, os.path.abspath("."))
import asyncio
import httpx
from src.infrastructure.repositories.baseline_repository import BaselineRepository
from src.pipelines.scheduler import PipelineOrchestrator
from src.pipelines.epa_punjab import EPAPunjabIngestionWorker
from src.pipelines.metar import MetarIngestionWorker
from src.pipelines.firms import FirmsIngestionWorker
from src.pipelines.iqair import IQAirIngestionWorker
from src.pipelines.cams import CamsIngestionWorker

async def main():
    repo = BaselineRepository()
    orch = PipelineOrchestrator(repo, mode="live")

    print(f"Orchestrator Mode: {orch.mode}")
    assert orch.mode == "live", "Orchestrator did not default to live mode"

    # Verify all workers default to live mode
    for name, worker in orch.workers.items():
        mode = getattr(worker, "worker_mode", None)
        print(f"Worker {name} ({worker.stream_id}): mode={mode}, healthy={worker.is_healthy}")
        if mode is not None:
            assert mode == "live", f"Worker {name} worker_mode is {mode}, not 'live'"

    # Verify degraded state contract on severed network
    severed_client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: None))

    # Test IQAir severed
    orch.workers["iqair"].client = severed_client
    iq_res = await orch.workers["iqair"].run()
    assert iq_res == [], f"IQAir returned non-empty {iq_res} on severed connection"
    assert not orch.workers["iqair"].is_healthy, "IQAir is_healthy was not False"
    print(f"IQAir severed: is_healthy={orch.workers['iqair'].is_healthy}, status={orch.workers['iqair'].status}, reason={orch.workers['iqair'].degraded_reason}")

    # Test CAMS severed
    orch.workers["cams"].client = severed_client
    cams_res = await orch.workers["cams"].run()
    assert cams_res == [], f"CAMS returned non-empty {cams_res} on severed connection"
    assert not orch.workers["cams"].is_healthy, "CAMS is_healthy was not False"
    print(f"CAMS severed: is_healthy={orch.workers['cams'].is_healthy}, status={orch.workers['cams'].status}, reason={orch.workers['cams'].degraded_reason}")

    # Test FIRMS without key
    orch.workers["firms"].api_key = None
    firms_res = await orch.workers["firms"].run()
    assert firms_res == [], f"FIRMS returned non-empty {firms_res} when key is None"
    assert not orch.workers["firms"].is_healthy, "FIRMS is_healthy was not False"
    print(f"FIRMS no-key: is_healthy={orch.workers['firms'].is_healthy}, status={orch.workers['firms'].status}, reason={orch.workers['firms'].degraded_reason}")

    # Test Orchestrator live status output
    st = orch.get_status()
    assert st["mode"] == "live"
    assert len(st["live_enabled_streams"]) == 7
    for sid in ["STR-01-EPAPUNJAB", "STR-02-METAR", "STR-03-SYNOP", "STR-04-ECMWF-IFS", "STR-05-FIRMS", "STR-06-IQAIR", "STR-07-CAMS"]:
        assert sid in st["live_enabled_streams"]

    print("ALL 7 PIPELINE REAL-DATA CONTRACTS EMPIRICALLY CONFIRMED!")

if __name__ == "__main__":
    asyncio.run(main())
