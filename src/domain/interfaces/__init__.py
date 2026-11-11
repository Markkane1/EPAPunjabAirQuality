"""Domain interface definitions for Punjab Air Quality system."""
from src.domain.interfaces.repositories import (
    AnalyticsRepository,
    DistrictRepository,
    ObservationRepository,
    StationRepository,
)

__all__ = [
    "StationRepository",
    "DistrictRepository",
    "ObservationRepository",
    "AnalyticsRepository",
]
