"""
Persistent Unified Repository integrating Relational Core (PostgreSQL 16),
TimescaleDB 2.14 Hypertables, PostGIS 3.4 Spatial Engine, Redis 7.2 High-Speed Cache,
and Continuous Database Rollups.
Conforms to StationRepository, DistrictRepository, ObservationRepository, and AnalyticsRepository interfaces.
"""
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional, Sequence, Tuple

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
from src.domain.interfaces.repositories import (
    AnalyticsRepository,
    DistrictRepository,
    ObservationRepository,
    StationRepository,
)
from src.infrastructure.cache.redis_analytics_repository import RedisAnalyticsRepository
from src.infrastructure.cache.redis_manager import RedisCacheManager
from src.infrastructure.database.connection import DatabaseConfig, DatabaseManager
from src.infrastructure.database.continuous_aggregates import ContinuousRollupService
from src.infrastructure.database.ddl import init_schema
from src.infrastructure.database.seeder import DatabaseSeeder
from src.infrastructure.repositories.sql_district_repository import SqlDistrictRepository
from src.infrastructure.repositories.sql_observation_repository import SqlObservationRepository
from src.infrastructure.repositories.sql_station_repository import SqlStationRepository
from src.infrastructure.spatial.postgis_engine import PostgisSpatialEngine

logger = logging.getLogger("paq.repositories.persistent")


class PersistentRepository(StationRepository, DistrictRepository, ObservationRepository, AnalyticsRepository):
    """
    Production-grade enterprise repository orchestrating the complete persistent architecture:
    1. Relational Core: PostgreSQL 16
    2. Time-Series Persistence: TimescaleDB 2.14 Hypertables
    3. Spatial Engine: PostGIS 3.4
    4. High-Speed Cache: Redis 7.2
    5. Continuous Rollups: Automated Continuous Aggregates
    """

    def __init__(
        self,
        baseline_dir: Optional[Path] = None,
        db_manager: Optional[DatabaseManager] = None,
        cache_manager: Optional[RedisCacheManager] = None,
    ) -> None:
        self._lock = threading.RLock()
        
        if baseline_dir is None:
            self.baseline_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "baseline"
        else:
            self.baseline_dir = Path(baseline_dir)

        # 1. Initialize Database & Schema
        self.db = db_manager or DatabaseManager.get_instance()
        if self.db.engine:
            self.schema_status = init_schema(self.db.engine)
        else:
            self.schema_status = {}

        # 2. Initialize Cache Manager
        self.cache_mgr = cache_manager or RedisCacheManager.get_instance()

        # 3. Initialize Domain Repositories
        self._station_repo = SqlStationRepository(session_factory=self.db._session_factory)
        self._district_repo = SqlDistrictRepository(session_factory=self.db._session_factory)
        self._obs_repo = SqlObservationRepository(
            session_factory=self.db._session_factory,
            engine=self.db.engine,
        )
        self._analytics_repo = RedisAnalyticsRepository(cache_manager=self.cache_mgr)

        # 4. Initialize Spatial Engine & Continuous Rollups
        self.spatial_engine = PostgisSpatialEngine(
            engine=self.db.engine,
            session_factory=self.db._session_factory,
            postgis_active=self.schema_status.get("postgis_enabled", False),
        )
        self.continuous_rollups = ContinuousRollupService(
            engine=self.db.engine,
            session_factory=self.db._session_factory,
        )
        if self.schema_status.get("timescaledb_enabled", False):
            self.continuous_rollups.setup_continuous_aggregates()

        # 5. Border samples & auxiliary stream caches
        self._tb_samples: List[List[float]] = []
        self._latest_fires: List[Any] = []
        self._latest_cross_border: List[Any] = []
        self._latest_cams: Optional[Any] = None

        # 6. Auto-seed if database is unpopulated
        self._ensure_seeded()

    def _ensure_seeded(self) -> None:
        """Hydrates PostgreSQL tables and TimescaleDB hypertables from baseline artifacts if empty."""
        seeder = DatabaseSeeder(
            session_factory=self.db._session_factory,
            baseline_dir=self.baseline_dir,
        )
        if not seeder.is_seeded():
            logger.info("Database is empty on boot. Executing initial baseline hydration...")
            seeder.seed_all()
            self._obs_repo._refresh_timeline_cache()

        # Load border samples from baseline_data.json
        baseline_file = self.baseline_dir / "baseline_data.json"
        if baseline_file.exists():
            try:
                with open(baseline_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                tbgeo = raw.get("tbgeo", {})
                self._tb_samples = tbgeo.get("samples", [])
            except Exception as e:
                logger.warning(f"Error loading transboundary samples: {e}")

    # =========================================================================
    # Facade Properties
    # =========================================================================

    @property
    def stations(self) -> SqlStationRepository:
        return self._station_repo

    @property
    def districts(self) -> SqlDistrictRepository:
        return self._district_repo

    @property
    def station_repo(self) -> SqlStationRepository:
        return self._station_repo

    @property
    def district_repo(self) -> SqlDistrictRepository:
        return self._district_repo

    @property
    def observations(self) -> SqlObservationRepository:
        return self._obs_repo

    @property
    def analytics(self) -> RedisAnalyticsRepository:
        return self._analytics_repo

    # =========================================================================
    # StationRepository Interface Forwarding
    # =========================================================================

    def get_by_id(self, station_id: str) -> Optional[Station]:
        return self._station_repo.get_by_id(station_id)

    def get_by_name(self, name: str) -> Optional[Station]:
        return self._station_repo.get_by_name(name)

    def list_all(self, station_type: Optional[str] = None) -> List[Station]:
        return self._station_repo.list_all(station_type=station_type)

    def list_by_district(self, district: str) -> List[Station]:
        return self._station_repo.list_by_district(district)

    def list_airports(self) -> List[Station]:
        return self._station_repo.list_airports()

    def exists(self, station_id: str) -> bool:
        return self._station_repo.exists(station_id)

    def count(self) -> int:
        return self._station_repo.count()

    def add_station(self, station: Station) -> None:
        self._station_repo.add_station(station)

    def add_stations(self, stations: Sequence[Station]) -> None:
        self._station_repo.add_stations(stations)

    # Aliases
    def get_station_by_id(self, station_id: str) -> Optional[Station]:
        return self.get_by_id(station_id)

    def get_station_by_name(self, name: str) -> Optional[Station]:
        return self.get_by_name(name)

    def list_stations(self, station_type: Optional[str] = None) -> List[Station]:
        return self.list_all(station_type=station_type)

    def count_stations(self) -> int:
        return self.count()

    # =========================================================================
    # DistrictRepository Interface Forwarding
    # =========================================================================

    def get_district_by_id(self, district_id: str) -> Optional[District]:
        return self._district_repo.get_by_id(district_id)

    def get_district_by_name(self, name: str) -> Optional[District]:
        return self._district_repo.get_by_name(name)

    def list_all_districts(self, monitored_only: bool = False) -> List[District]:
        return self._district_repo.list_all(monitored_only=monitored_only)

    def list_districts(self, monitored_only: bool = False) -> List[District]:
        return self._district_repo.list_all(monitored_only=monitored_only)

    def list_border_districts(self, max_border_distance_km: float = 120.0) -> List[District]:
        return self._district_repo.list_border_districts(max_border_distance_km=max_border_distance_km)

    def get_border_districts(self, max_distance_km: float = 120.0) -> List[District]:
        return self.list_border_districts(max_border_distance_km=max_distance_km)

    def count_districts(self) -> int:
        return self._district_repo.count()

    def district_count(self) -> int:
        return self._district_repo.count()

    def get_boundary_geometry(self, district_id: str) -> Optional[Dict[str, Any]]:
        return self._district_repo.get_boundary_geometry(district_id)

    def get_boundary(self, district_id: str) -> Optional[Dict[str, Any]]:
        return self.get_boundary_geometry(district_id)

    def get_label_placement(self, district_id: str) -> Optional[LabelPlacement]:
        return self._district_repo.get_label_placement(district_id)

    def get_border_samples(self) -> List[List[float]]:
        return list(self._tb_samples)

    # =========================================================================
    # ObservationRepository Interface Forwarding (TimescaleDB)
    # =========================================================================

    def get_station_observation(self, station_id: str, timestamp: datetime) -> Optional[StationObservation]:
        return self._obs_repo.get_station_observation(station_id, timestamp)

    def get_latest_station_observations(self, pollutant: Optional[str] = None) -> List[StationObservation]:
        return self._obs_repo.get_latest_station_observations(pollutant=pollutant)

    def get_station_observations_at_timestamp(
        self, timestamp: datetime, pollutant: Optional[str] = None
    ) -> List[StationObservation]:
        return self._obs_repo.get_station_observations_at_timestamp(timestamp, pollutant=pollutant)

    def get_station_hourly_series(
        self,
        station_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        pollutant: Optional[str] = None,
    ) -> List[StationObservation]:
        return self._obs_repo.get_station_hourly_series(
            station_id=station_id,
            start_time=start_time,
            end_time=end_time,
            pollutant=pollutant,
        )

    def get_station_observations_for_district(
        self,
        district: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[StationObservation]:
        return self._obs_repo.get_station_observations_for_district(
            district=district,
            start_time=start_time,
            end_time=end_time,
        )

    def get_district_observation(self, district_id: str, timestamp: datetime) -> Optional[DistrictObservation]:
        return self._obs_repo.get_district_observation(district_id, timestamp)

    def get_latest_district_observations(self, pollutant: Optional[str] = None) -> List[DistrictObservation]:
        return self._obs_repo.get_latest_district_observations(pollutant=pollutant)

    def get_district_observations_at_timestamp(
        self, timestamp: datetime, pollutant: Optional[str] = None
    ) -> List[DistrictObservation]:
        return self._obs_repo.get_district_observations_at_timestamp(timestamp, pollutant=pollutant)

    def get_district_hourly_series(
        self,
        district_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        pollutant: Optional[str] = None,
    ) -> List[DistrictObservation]:
        return self._obs_repo.get_district_hourly_series(
            district_id=district_id,
            start_time=start_time,
            end_time=end_time,
            pollutant=pollutant,
        )

    # Timeline & Scrubber Metadata
    get_latest_observations = get_latest_station_observations
    get_station_observations_by_time_range = get_station_hourly_series
    get_district_observations_by_time_range = get_district_hourly_series

    def get_available_timestamps(self) -> List[datetime]:
        return self._obs_repo.get_available_timestamps()

    def get_timeline_timestamps(self) -> List[datetime]:
        return self._obs_repo.get_available_timestamps()

    def get_latest_timestamp(self) -> Optional[datetime]:
        return self._obs_repo.get_latest_timestamp()

    def get_earliest_timestamp(self) -> Optional[datetime]:
        return self._obs_repo.get_earliest_timestamp()

    def get_timestamp_by_index(self, index: int) -> Optional[datetime]:
        return self._obs_repo.get_timestamp_by_index(index)

    def get_hour_index(self, timestamp: datetime) -> Optional[int]:
        return self._obs_repo.get_hour_index(timestamp)

    def total_hours(self) -> int:
        return self._obs_repo.total_hours()

    # Ingestion & Dynamic Writes
    def add_station_observation(self, observation: StationObservation) -> None:
        self._obs_repo.add_station_observation(observation)
        self.clear_cache()

    def add_station_observations(self, observations: Sequence[StationObservation]) -> None:
        self._obs_repo.add_station_observations(observations)
        self.clear_cache()

    def add_district_observation(self, observation: DistrictObservation) -> None:
        self._obs_repo.add_district_observation(observation)
        self.clear_cache()

    def add_district_observations(self, observations: Sequence[DistrictObservation]) -> None:
        self._obs_repo.add_district_observations(observations)
        self.clear_cache()

    def add_user_csv_observations(self, observations: Sequence[Any]) -> int:
        """
        Dynamically registers user-provided stations and converts normalized CSV observations
        into domain StationObservation entries with thread-safe atomic persistence and cache invalidation.
        """
        with self._lock:
            converted_obs: List[StationObservation] = []
            new_stations: List[Station] = []
            existing_ids = {s.id for s in self._station_repo.list_all()}

            for obs in observations:
                stn_id = getattr(obs, "station_id", None)
                if not stn_id:
                    continue

                if stn_id not in existing_ids:
                    st = Station(
                        id=stn_id,
                        name=getattr(obs, "station_name", stn_id) or stn_id,
                        district=getattr(obs, "district", "Lahore") or "Lahore",
                        latitude=float(getattr(obs, "latitude", 0.0) or 0.0),
                        longitude=float(getattr(obs, "longitude", 0.0) or 0.0),
                        station_type="user_csv",
                        has_anemometer=(getattr(obs, "wind_speed_ms", None) is not None),
                        anemometer_blacklisted=False,
                        altitude_m=None,
                        metadata={"source": "user_csv"},
                    )
                    new_stations.append(st)
                    existing_ids.add(stn_id)

                st_obs = StationObservation(
                    station_id=stn_id,
                    recorded_at=getattr(obs, "timestamp", datetime.now(timezone.utc)),
                    pm25=getattr(obs, "pm25_qc", getattr(obs, "pm25", None)),
                    pm10=getattr(obs, "pm10_qc", getattr(obs, "pm10", None)),
                    no2=getattr(obs, "no2_qc", getattr(obs, "no2", None)),
                    so2=getattr(obs, "so2_qc", getattr(obs, "so2", None)),
                    co=getattr(obs, "co_qc", getattr(obs, "co", None)),
                    o3=getattr(obs, "o3_qc", getattr(obs, "o3", None)),
                    no=getattr(obs, "no_qc", getattr(obs, "no", None)),
                    nox=getattr(obs, "nox_qc", getattr(obs, "nox", None)),
                    aqi=getattr(obs, "pepc_aqi", getattr(obs, "aqi", None)),
                    wind_speed=getattr(obs, "wind_speed_ms", getattr(obs, "wind_speed", None)),
                    wind_direction=getattr(obs, "wind_direction_deg", getattr(obs, "wind_direction", None)),
                    u=getattr(obs, "u_vector_ms", getattr(obs, "u", None)),
                    v=getattr(obs, "v_vector_ms", getattr(obs, "v", None)),
                )
                converted_obs.append(st_obs)

            if new_stations:
                self._station_repo.add_stations(new_stations)

            if converted_obs:
                self.add_station_observations(converted_obs)

            return len(converted_obs)


    # =========================================================================
    # AnalyticsRepository Interface Forwarding (Redis Cache)
    # =========================================================================

    def get_cpf_rose(self, district_id: str, pollutant: str) -> Optional[CPFRoseResult]:
        return self._analytics_repo.get_cpf_rose(district_id, pollutant)

    def save_cpf_rose(self, result: CPFRoseResult) -> None:
        self._analytics_repo.save_cpf_rose(result)

    def get_advection_flux(self, timestamp: datetime, pollutant: str) -> Optional[List[AdvectionFluxLink]]:
        return self._analytics_repo.get_advection_flux(timestamp, pollutant)

    def save_advection_flux(
        self, timestamp: datetime, pollutant: str, links: Sequence[AdvectionFluxLink]
    ) -> None:
        self._analytics_repo.save_advection_flux(timestamp, pollutant, links)

    def get_transboundary_result(self, timestamp: datetime) -> Optional[TransboundaryResult]:
        return self._analytics_repo.get_transboundary_result(timestamp)

    def save_transboundary_result(self, result: TransboundaryResult) -> None:
        self._analytics_repo.save_transboundary_result(result)

    def get_surface_grid(
        self, timestamp: datetime, pollutant: str, resolution: int
    ) -> Optional[List[SurfaceGridPoint]]:
        return self._analytics_repo.get_surface_grid(timestamp, pollutant, resolution)

    def save_surface_grid(
        self, timestamp: datetime, pollutant: str, resolution: int, grid: Sequence[SurfaceGridPoint]
    ) -> None:
        self._analytics_repo.save_surface_grid(timestamp, pollutant, resolution, grid)

    def clear_cache(self) -> None:
        self._analytics_repo.clear_cache()

    # =========================================================================
    # Auxiliary Feeds
    # =========================================================================

    def get_latest_fires(self) -> List[Any]:
        with self._lock:
            return list(self._latest_fires)

    def set_latest_fires(self, fires: List[Any]) -> None:
        with self._lock:
            self._latest_fires = list(fires)

    def get_latest_cross_border(self) -> List[Any]:
        with self._lock:
            return list(self._latest_cross_border)

    def set_latest_cross_border(self, cross_border: List[Any]) -> None:
        with self._lock:
            self._latest_cross_border = list(cross_border)

    def get_latest_cams(self) -> Optional[Any]:
        with self._lock:
            return self._latest_cams

    def set_latest_cams(self, cams: Any) -> None:
        with self._lock:
            self._latest_cams = cams

    def set_latest_auxiliary_feeds(self, fires: Any, cross_border: Any, cams: Any) -> None:
        with self._lock:
            self._latest_fires = list(fires)
            self._latest_cross_border = list(cross_border)
            self._latest_cams = cams
