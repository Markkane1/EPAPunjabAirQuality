"""API Route Module: Real-Time Server-Sent Events (SSE) Stream (/api/v1/stream)."""
import asyncio
from datetime import datetime
import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, StreamingResponse

from src.api.dependencies import get_observation_service
from src.services.observation_service import ObservationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/stream", tags=["Streaming"])

KEEPALIVE_INTERVAL_SECONDS: float = 15.0
POLL_CHECK_INTERVAL_SECONDS: float = 2.0


async def sse_event_generator(
    request: Request,
    obs_service: ObservationService,
    max_events: Optional[int] = None,
) -> AsyncGenerator[str, None]:
    """
    Generates asynchronous Server-Sent Events stream.
    Emits initial full snapshot frame upon connection, then listens on orchestrator queue
    or falls back to heartbeat polling loop.
    Pings clients with ': keepalive\\n\\n' every 15 seconds.
    Emits 'event: hourly_update' when a new hourly observation is registered.
    Gracefully exits when client disconnects or when max_events threshold is reached.
    """
    events_sent = 0
    initial_data: dict = {}
    try:
        initial_data = obs_service.get_latest_summary_for_stream()
        yield f"event: hourly_update\ndata: {json.dumps(initial_data)}\n\n"
        events_sent += 1
        if max_events is not None and events_sent >= max_events:
            return
    except Exception as e:
        logger.error(f"Error generating initial SSE snapshot: {e}")
        yield f"event: error\ndata: {json.dumps({'message': 'Initial snapshot failed'})}\n\n"
        events_sent += 1
        if max_events is not None and events_sent >= max_events:
            return

    orchestrator = getattr(request.app.state, "orchestrator", None) if hasattr(request, "app") else None
    client_queue = orchestrator.subscribe() if orchestrator else None

    # Wire to Redis Pub/Sub Fan-Out if available
    repo = getattr(request.app.state, "repo", None) if hasattr(request, "app") else None
    redis_mgr = getattr(repo, "cache_mgr", None) if repo else None
    redis_queue = None
    if redis_mgr and not client_queue:
        redis_queue = asyncio.Queue()
        redis_mgr._local_subscribers.append(redis_queue)
        client_queue = redis_queue

    last_ping = asyncio.get_event_loop().time()
    last_emitted_timestamp = initial_data.get("timestamp")

    try:
        while True:
            if await request.is_disconnected():
                logger.info("SSE client disconnected.")
                break

            if client_queue:
                # Event-driven wait on orchestrator queue with keepalive timeout
                try:
                    payload = await asyncio.wait_for(client_queue.get(), timeout=KEEPALIVE_INTERVAL_SECONDS)
                    # Enrich with latest summary from obs_service
                    summary = obs_service.get_latest_summary_for_stream()
                    summary.update(payload)
                    yield f"event: hourly_update\ndata: {json.dumps(summary)}\n\n"
                    events_sent += 1
                    if max_events is not None and events_sent >= max_events:
                        break
                except asyncio.TimeoutError:
                    # Check if observation service updated directly (e.g. repo injection)
                    latest_ts = obs_service.get_latest_timestamp_utc()
                    if latest_ts and latest_ts != last_emitted_timestamp:
                        update_payload = obs_service.get_latest_summary_for_stream()
                        yield f"event: hourly_update\ndata: {json.dumps(update_payload)}\n\n"
                        last_emitted_timestamp = latest_ts
                        events_sent += 1
                        if max_events is not None and events_sent >= max_events:
                            break
                    # 15s timeout: emit keepalive
                    yield ": keepalive\n\nevent: keepalive\ndata: {}\n\n"
            else:
                # Polling fallback mode
                await asyncio.sleep(POLL_CHECK_INTERVAL_SECONDS)
                now = asyncio.get_event_loop().time()

                latest_ts = obs_service.get_latest_timestamp_utc()
                if latest_ts and latest_ts != last_emitted_timestamp:
                    update_payload = obs_service.get_latest_summary_for_stream()
                    yield f"event: hourly_update\ndata: {json.dumps(update_payload)}\n\n"
                    last_emitted_timestamp = latest_ts
                    events_sent += 1
                    if max_events is not None and events_sent >= max_events:
                        break

                if now - last_ping >= KEEPALIVE_INTERVAL_SECONDS:
                    yield ": keepalive\n\nevent: keepalive\ndata: {}\n\n"
                    last_ping = now

    except asyncio.CancelledError:
        logger.info("SSE connection task cancelled by client.")
    except Exception as e:
        logger.error(f"Unexpected error in SSE stream generator: {e}")
    finally:
        if redis_queue and redis_mgr and redis_queue in redis_mgr._local_subscribers:
            redis_mgr._local_subscribers.remove(redis_queue)
        if orchestrator and client_queue and client_queue != redis_queue:
            orchestrator.unsubscribe(client_queue)


@router.get("/live", summary="Continuous Server-Sent Events (SSE) telemetry feed")
async def live_stream(
    request: Request,
    max_events: Optional[int] = Query(default=None, description="Optional max events limit for testing/batching"),
    obs_service: ObservationService = Depends(get_observation_service),
) -> StreamingResponse:
    """
    Establishes real-time push channel to client dashboards.
    Sends 15s keepalive pings and hourly_update event packets.
    """
    return StreamingResponse(
        sse_event_generator(request, obs_service, max_events=max_events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/tick", summary="Advance simulation or trigger manual pipeline run")
async def trigger_pipeline_tick(
    request: Request,
    mode: Optional[str] = Query(default=None, description="Execution mode: 'simulation' or 'live'"),
) -> JSONResponse:
    """
    Manually advances the simulation pump by 1 hour or executes an immediate live pipeline cycle.
    Broadcasts the newly committed frame to all active SSE subscribers.
    """
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if not orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pipeline orchestrator is not initialized on application state.",
        )

    try:
        report = await orchestrator.tick_async(mode=mode)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "mode": mode or orchestrator.mode,
                "message": f"Successfully processed and committed frame for {report.timestamp.isoformat()}",
                "report": {
                    "timestamp": report.timestamp.isoformat(),
                    "stations_committed": report.stations_committed,
                    "districts_committed": report.districts_committed,
                    "unmonitored_imputed": report.unmonitored_imputed,
                    "mean_aqi": report.mean_aqi,
                    "peak_aqi": report.peak_aqi,
                    "peak_district": report.peak_district,
                    "active_fires_count": report.active_fires_count,
                    "cross_border_cities_count": report.cross_border_cities_count,
                    "net_transboundary_flux": report.net_transboundary_flux,
                },
            },
        )
    except Exception as e:
        logger.error("Pipeline tick execution failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Pipeline tick failed: {str(e)}")


@router.post("/mode", summary="Set stream operating mode (simulation or live)")
async def set_stream_mode(request: Request) -> JSONResponse:
    """Sets stream operating mode between 'simulation' and 'live'."""
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if not orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pipeline orchestrator is not initialized on application state.",
        )
    try:
        body = await request.json()
        target_mode = body.get("mode", "simulation")
        orchestrator.set_mode(target_mode)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "success", "mode": orchestrator.mode},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request payload: {e}")


@router.get("/status", summary="Operational health and stream status")
async def get_stream_status(request: Request) -> JSONResponse:
    """Returns operational status of all streams and orchestrator telemetry."""
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if not orchestrator:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "uninitialized", "message": "Orchestrator not attached to app state."},
        )
    return JSONResponse(status_code=status.HTTP_200_OK, content=orchestrator.get_status())
