"""API Route modules for Punjab Air Quality system."""
from src.api.routes import (
    analytics,
    epa,
    ingest,
    meta,
    observations,
    spatial,
    stream,
)

__all__ = [
    "meta",
    "observations",
    "spatial",
    "analytics",
    "ingest",
    "stream",
    "epa",
]
