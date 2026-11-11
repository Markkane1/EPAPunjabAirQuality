"""API Route Module: Real-Time Server-Sent Events (SSE) Stream (/api/v1/stream)."""
import asyncio
import json
import logging
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

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
    Emits initial full snapshot frame upon connection, then enters heartbeat loop.
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

    last_ping = asyncio.get_event_loop().time()
    last_emitted_timestamp = initial_data.get("timestamp")

    try:
        while True:
            if await request.is_disconnected():
                logger.info("SSE client disconnected.")
                break

            await asyncio.sleep(POLL_CHECK_INTERVAL_SECONDS)
            now = asyncio.get_event_loop().time()

            # Check for newly arrived hourly telemetry updates
            latest_ts = obs_service.get_latest_timestamp_utc()
            if latest_ts and latest_ts != last_emitted_timestamp:
                update_payload = obs_service.get_latest_summary_for_stream()
                yield f"event: hourly_update\ndata: {json.dumps(update_payload)}\n\n"
                last_emitted_timestamp = latest_ts
                events_sent += 1
                if max_events is not None and events_sent >= max_events:
                    break

            # 15-second keepalive: proxy comment line AND client EventSource keepalive event
            if now - last_ping >= KEEPALIVE_INTERVAL_SECONDS:
                yield ": keepalive\n\nevent: keepalive\ndata: {}\n\n"
                last_ping = now

    except asyncio.CancelledError:
        logger.info("SSE connection task cancelled by client.")
    except Exception as e:
        logger.error(f"Unexpected error in SSE stream generator: {e}")


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
