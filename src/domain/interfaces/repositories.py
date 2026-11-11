"""
Domain repository interfaces for Punjab Air Quality Monitoring System.
Conforms to Clean Architecture: zero external framework coupling (standard library only).
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from src.domain.entities.models import (
    AdvectionFluxLink,
    CPFRoseResult,
    District,
    DistrictObservation,
    LabelPlacement,
    Station,
    StationObservation,
    SurfaceGridPoint,
    TransboundaryResult,
)


class StationRepository(ABC):
    """Abstract data access interface for monitoring stations and airport aerodromes."""

    @abstractmethod
    def get_by_id(self, station_id: str) -> Optional[Station]:
        """Retrieve a station by its unique station identifier."""
        pass

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Station]:
        """Retrieve a station by display name (case-insensitive)."""
        pass

    @abstractmethod
    def list_all(self, station_type: Optional[str] = None) -> List[Station]:
        """List all registered stations, optionally filtered by station_type."""
        pass

    @abstractmethod
    def list_by_district(self, district: str) -> List[Station]:
        """List all stations operating within a specific administrative district."""
        pass

    @abstractmethod
    def list_airports(self) -> List[Station]:
        """List all airport weather monitoring stations (METAR aerodromes)."""
        pass

    @abstractmethod
    def exists(self, station_id: str) -> bool:
        """Check whether a station identifier is registered."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Return the total number of registered stations."""
        pass

    @abstractmethod
    def add_station(self, station: Station) -> None:
        """Register or update a single station."""
        pass

    @abstractmethod
    def add_stations(self, stations: Sequence[Station]) -> None:
        """Bulk register or update multiple stations."""
        pass

    def get_station_by_id(self, station_id: str) -> Optional[Station]:
        return self.get_by_id(station_id)

    def get_station_by_name(self, name: str) -> Optional[Station]:
        return self.get_by_name(name)

    def list_stations(self, station_type: Optional[str] = None) -> List[Station]:
        return self.list_all(station_type=station_type)

    def get_all(self) -> List[Station]:
        return self.list_all()

    def count_stations(self) -> int:
        return self.count()

    def add_batch(self, stations: Sequence[Station]) -> None:
        self.add_stations(stations)


class DistrictRepository(ABC):
    """Abstract data access interface for administrative districts and spatial boundaries."""

    @abstractmethod
    def get_by_id(self, district_id: str) -> Optional[District]:
        """Retrieve a district by its administrative ID."""
        pass

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[District]:
        """Retrieve a district by name (case-insensitive)."""
        pass

    @abstractmethod
    def list_all(self, monitored_only: bool = False) -> List[District]:
        """List all 41 districts, optionally filtered by active monitoring status."""
        pass

    @abstractmethod
    def list_border_districts(self, max_border_distance_km: float = 120.0) -> List[District]:
        """List districts situated within the international border corridor."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Return total district count (41 for Punjab Province)."""
        pass

    @abstractmethod
    def get_boundary_geometry(self, district_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve GeoJSON boundary polygon geometry for a district."""
        pass

    @abstractmethod
    def get_label_placement(self, district_id: str) -> Optional[LabelPlacement]:
        """Retrieve collision-free label placement coordinates for a district."""
        pass

    def get_district_by_id(self, district_id: str) -> Optional[District]:
        return self.get_by_id(district_id)

    def get_district_by_name(self, name: str) -> Optional[District]:
        return self.get_by_name(name)

    def list_all_districts(self, monitored_only: bool = False) -> List[District]:
        return self.list_all(monitored_only=monitored_only)

    def list_districts(self, monitored_only: bool = False) -> List[District]:
        return self.list_all(monitored_only=monitored_only)

    def get_boundary(self, district_id: str) -> Optional[Dict[str, Any]]:
        return self.get_boundary_geometry(district_id)

    def get_border_districts(self, max_distance_km: float = 120.0) -> List[District]:
        return self.list_border_districts(max_border_distance_km=max_distance_km)

    def count_districts(self) -> int:
        return self.count()

    def district_count(self) -> int:
        return self.count()


class ObservationRepository(ABC):
    """Abstract data access interface for time-series air quality telemetry and meteorological observations."""

    # Station Observations
    @abstractmethod
    def get_station_observation(self, station_id: str, timestamp: datetime) -> Optional[StationObservation]:
        """Retrieve observation for a specific station at an exact timestamp."""
        pass

    @abstractmethod
    def get_latest_station_observations(self, pollutant: Optional[str] = None) -> List[StationObservation]:
        """Retrieve latest snapshot readings across all stations, optionally filtered by non-null pollutant."""
        pass

    @abstractmethod
    def get_station_observations_at_timestamp(
        self, timestamp: datetime, pollutant: Optional[str] = None
    ) -> List[StationObservation]:
        """Retrieve readings across all stations for a specified timestamp."""
        pass

    @abstractmethod
    def get_station_hourly_series(
        self,
        station_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        pollutant: Optional[str] = None,
    ) -> List[StationObservation]:
        """Retrieve chronological historical series for a single station."""
        pass

    @abstractmethod
    def get_station_observations_for_district(
        self,
        district: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[StationObservation]:
        """Retrieve all station observations in a district across a time range."""
        pass

    # District Observations
    @abstractmethod
    def get_district_observation(self, district_id: str, timestamp: datetime) -> Optional[DistrictObservation]:
        """Retrieve aggregated or imputed observation for a district at an exact timestamp."""
        pass

    @abstractmethod
    def get_latest_district_observations(self, pollutant: Optional[str] = None) -> List[DistrictObservation]:
        """Retrieve latest snapshot readings for all 41 districts."""
        pass

    @abstractmethod
    def get_district_observations_at_timestamp(
        self, timestamp: datetime, pollutant: Optional[str] = None
    ) -> List[DistrictObservation]:
        """Retrieve observations for all 41 districts at a specified timestamp."""
        pass

    @abstractmethod
    def get_district_hourly_series(
        self,
        district_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        pollutant: Optional[str] = None,
    ) -> List[DistrictObservation]:
        """Retrieve chronological historical series for a district."""
        pass

    # Timeline & Scrubber Metadata
    @abstractmethod
    def get_available_timestamps(self) -> List[datetime]:
        """Return chronologically sorted list of all available observation timestamps."""
        pass

    @abstractmethod
    def get_latest_timestamp(self) -> Optional[datetime]:
        """Return the most recent available observation timestamp."""
        pass

    @abstractmethod
    def get_earliest_timestamp(self) -> Optional[datetime]:
        """Return the oldest available observation timestamp."""
        pass

    @abstractmethod
    def get_timestamp_by_index(self, index: int) -> Optional[datetime]:
        """Retrieve timestamp corresponding to scrubber index (0..215, supports -1 for latest)."""
        pass

    @abstractmethod
    def get_hour_index(self, timestamp: datetime) -> Optional[int]:
        """Map a datetime to its scrubber integer hour index."""
        pass

    @abstractmethod
    def total_hours(self) -> int:
        """Return total count of unique hourly frames in the timeline."""
        pass

    # Ingestion & Dynamic Storage
    @abstractmethod
    def add_station_observation(self, observation: StationObservation) -> None:
        """Add or update a single station observation."""
        pass

    @abstractmethod
    def add_station_observations(self, observations: Sequence[StationObservation]) -> None:
        """Bulk add or update station observations."""
        pass

    @abstractmethod
    def add_district_observation(self, observation: DistrictObservation) -> None:
        """Add or update a single district observation."""
        pass

    @abstractmethod
    def add_district_observations(self, observations: Sequence[DistrictObservation]) -> None:
        """Bulk add or update district observations."""
        pass


class AnalyticsRepository(ABC):
    """Abstract data access interface for caching and retrieving analytical products."""

    @abstractmethod
    def get_cpf_rose(self, district_id: str, pollutant: str) -> Optional[CPFRoseResult]:
        """Retrieve cached 16-sector CPF wind rose analysis for a district."""
        pass

    @abstractmethod
    def save_cpf_rose(self, result: CPFRoseResult) -> None:
        """Cache CPF wind rose analysis result."""
        pass

    @abstractmethod
    def get_advection_flux(self, timestamp: datetime, pollutant: str) -> Optional[List[AdvectionFluxLink]]:
        """Retrieve cached inter-district transport flux link vectors."""
        pass

    @abstractmethod
    def save_advection_flux(
        self, timestamp: datetime, pollutant: str, links: Sequence[AdvectionFluxLink]
    ) -> None:
        """Cache inter-district transport flux link vectors."""
        pass

    @abstractmethod
    def get_transboundary_result(self, timestamp: datetime) -> Optional[TransboundaryResult]:
        """Retrieve cached cross-border transboundary mass balance index."""
        pass

    @abstractmethod
    def save_transboundary_result(self, result: TransboundaryResult) -> None:
        """Cache transboundary mass balance result."""
        pass

    @abstractmethod
    def get_surface_grid(
        self, timestamp: datetime, pollutant: str, resolution: int
    ) -> Optional[List[SurfaceGridPoint]]:
        """Retrieve cached continuous IDW surface grid points."""
        pass

    @abstractmethod
    def save_surface_grid(
        self, timestamp: datetime, pollutant: str, resolution: int, grid: Sequence[SurfaceGridPoint]
    ) -> None:
        """Cache continuous surface grid points."""
        pass

    @abstractmethod
    def clear_cache(self) -> None:
        """Purge analytical caches upon dynamic dataset updates."""
        pass
