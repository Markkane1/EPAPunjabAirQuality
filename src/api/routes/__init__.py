"""API Route modules for Punjab Air Quality system."""
from src.api.routes import (
    analytics,
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
]
