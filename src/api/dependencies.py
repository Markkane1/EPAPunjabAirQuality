"""FastAPI Dependency Injection providers bridging routes to repositories and application services."""
from fastapi import Request

from src.domain.interfaces.repositories import (
    AnalyticsRepository,
    DistrictRepository,
    ObservationRepository,
    StationRepository,
)
from src.infrastructure.repositories.baseline_repository import BaselineRepository
from src.services.analytics_service import AnalyticsService
from src.services.ingestion_service import IngestionService
from src.services.observation_service import ObservationService
from src.services.spatial_service import SpatialService


def get_repository(request: Request) -> BaselineRepository:
    """Retrieves the unified baseline repository instance from app.state."""
    return request.app.state.repo


def get_station_repository(request: Request) -> StationRepository:
    repo = request.app.state.repo
    return getattr(repo, "stations", repo)


def get_district_repository(request: Request) -> DistrictRepository:
    repo = request.app.state.repo
    return getattr(repo, "districts", repo)


def get_observation_repository(request: Request) -> ObservationRepository:
    return request.app.state.repo


def get_analytics_repository(request: Request) -> AnalyticsRepository:
    return request.app.state.repo


def get_observation_service(request: Request) -> ObservationService:
    return request.app.state.observation_service


def get_spatial_service(request: Request) -> SpatialService:
    return request.app.state.spatial_service


def get_analytics_service(request: Request) -> AnalyticsService:
    return request.app.state.analytics_service


def get_ingestion_service(request: Request) -> IngestionService:
    return request.app.state.ingestion_service
