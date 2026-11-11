"""Pydantic v2 schemas for API contracts."""
from src.api.schemas.analytics import (
    AdvectionPathwayLink,
    BorderDistrictTransboundaryDetail,
    BorderSampleNode,
    CPFRoseResponse,
    CPFSectorDetail,
    FluxTransportResponse,
    TransboundaryResponse,
)
from src.api.schemas.ingest import CSVIngestResponse, QuarantineDetail
from src.api.schemas.meta import DistrictMetaResponse, StationMetaResponse
from src.api.schemas.observations import (
    AirportReadingSchema,
    CurrentObservationsResponse,
    DistrictHourlySeriesSchema,
    DistrictReadingSchema,
    HourlyObservationsResponse,
    ProvincialSummarySchema,
)
from src.api.schemas.spatial import SpatialSurfaceResponse
from src.api.schemas.stream import SSEHourlyUpdatePayload

__all__ = [
    "DistrictMetaResponse",
    "StationMetaResponse",
    "ProvincialSummarySchema",
    "DistrictReadingSchema",
    "AirportReadingSchema",
    "CurrentObservationsResponse",
    "DistrictHourlySeriesSchema",
    "HourlyObservationsResponse",
    "SpatialSurfaceResponse",
    "CPFSectorDetail",
    "CPFRoseResponse",
    "AdvectionPathwayLink",
    "FluxTransportResponse",
    "BorderDistrictTransboundaryDetail",
    "BorderSampleNode",
    "TransboundaryResponse",
    "QuarantineDetail",
    "CSVIngestResponse",
    "SSEHourlyUpdatePayload",
]
