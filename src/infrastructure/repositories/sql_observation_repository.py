"""
SQL and TimescaleDB Observation Repository for Punjab Air Quality Workstation.
Replaces in-memory _station_obs_by_id_and_time dictionaries with relational and time-series hypertable queries.
Implements composite primary key ON CONFLICT deduplication (resolving Challenge 2.1).
"""
from bisect import bisect_left, bisect_right
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.domain.entities.models import DistrictObservation, StationObservation
from src.domain.interfaces.repositories import ObservationRepository
from src.infrastructure.database.models import (
    DistrictHourlyAggregateModel,
    SpatialStationModel,
    StationHourlyObservationModel,
)

logger = logging.getLogger("paq.repositories.sql_observation")


class SqlObservationRepository(ObservationRepository):
    """
    Time-Series Persistence repository backed by TimescaleDB hypertables:
    - station_hourly_observations (30-day chunk partitioning)
    - district_hourly_aggregates (14-day chunk partitioning)
    """

    def __init__(self, session_factory: Any, engine: Any) -> None:
        self.session_factory = session_factory
        self.engine = engine
        self._timeline_cache: List[datetime] = []
        self._time_to_idx_cache: Dict[datetime, int] = {}
        self._refresh_timeline_cache()

    def _normalize_dt(self, dt: datetime) -> datetime:
        """Normalizes datetime to UTC timezone."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _refresh_timeline_cache(self) -> None:
        """Loads sorted unique observation timestamps for O(1) scrubber indexing."""
        session: Session = self.session_factory()
        try:
            rows = session.query(
                StationHourlyObservationModel.recorded_at
            ).distinct().order_by(StationHourlyObservationModel.recorded_at.asc()).all()
            
            timestamps = [self._normalize_dt(r[0]) for r in rows]
            self._timeline_cache = timestamps
            self._time_to_idx_cache = {ts: idx for idx, ts in enumerate(timestamps)}
        except Exception as e:
            logger.debug(f"Timeline cache refresh notice: {e}")
        finally:
            session.close()

    def _to_station_entity(self, m: StationHourlyObservationModel) -> StationObservation:
        """Maps ORM model to domain StationObservation entity."""
        return StationObservation(
            station_id=m.station_id,
            recorded_at=self._normalize_dt(m.recorded_at),
            pm25=m.pm25,
            pm10=m.pm10,
            no2=m.no2,
            so2=m.so2,
            co=m.co,
            o3=m.o3,
            no=m.no,
            nox=m.nox,
            aqi=int(m.aqi_pepc) if m.aqi_pepc is not None else None,
            wind_speed=m.wind_speed_ms,
            wind_direction=m.wind_direction_deg,
            u=m.u_ms,
            v=m.v_ms,
            temperature_c=m.temp_c,
            relative_humidity_pct=m.rh_pct,
            qc_flags=m.qc_flags,
        )

    def _to_district_entity(self, m: DistrictHourlyAggregateModel) -> DistrictObservation:
        """Maps ORM model to domain DistrictObservation entity."""
        return DistrictObservation(
            district_id=m.district_id,
            recorded_at=self._normalize_dt(m.recorded_at),
            pm25=m.pm25,
            pm10=m.pm10,
            no2=m.no2,
            so2=m.so2,
            co=m.co,
            o3=m.o3,
            aqi=int(m.aqi_pepc) if m.aqi_pepc is not None else None,
            wind_speed=m.wind_speed_ms,
            wind_direction=m.wind_direction_deg,
            u=m.u_ms,
            v=m.v_ms,
            is_estimated=m.is_estimated,
        )

    # =========================================================================
    # Station Observation Queries
    # =========================================================================

    def get_station_observation(self, station_id: str, timestamp: datetime) -> Optional[StationObservation]:
        norm_dt = self._normalize_dt(timestamp)
        session: Session = self.session_factory()
        try:
            m = session.query(StationHourlyObservationModel).filter(
                StationHourlyObservationModel.station_id == str(station_id),
                StationHourlyObservationModel.recorded_at == norm_dt,
            ).first()
            return self._to_station_entity(m) if m else None
        finally:
            session.close()

    def get_latest_station_observations(self, pollutant: Optional[str] = None) -> List[StationObservation]:
        latest_ts = self.get_latest_timestamp()
        if latest_ts is None:
            return []
        return self.get_station_observations_at_timestamp(latest_ts, pollutant=pollutant)

    def get_station_observations_at_timestamp(
        self, timestamp: datetime, pollutant: Optional[str] = None
    ) -> List[StationObservation]:
        norm_dt = self._normalize_dt(timestamp)
        session: Session = self.session_factory()
        try:
            q = session.query(StationHourlyObservationModel).filter(
                StationHourlyObservationModel.recorded_at == norm_dt
            )
            if pollutant:
                p_attr = pollutant.lower().replace(".", "").replace("-", "")
                if hasattr(StationHourlyObservationModel, p_attr):
                    q = q.filter(getattr(StationHourlyObservationModel, p_attr).isnot(None))

            models = q.all()
            return [self._to_station_entity(m) for m in models]
        finally:
            session.close()

    def get_station_hourly_series(
        self,
        station_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        pollutant: Optional[str] = None,
    ) -> List[StationObservation]:
        session: Session = self.session_factory()
        try:
            q = session.query(StationHourlyObservationModel).filter(
                StationHourlyObservationModel.station_id == str(station_id)
            )
            if start_time:
                q = q.filter(StationHourlyObservationModel.recorded_at >= self._normalize_dt(start_time))
            if end_time:
                q = q.filter(StationHourlyObservationModel.recorded_at <= self._normalize_dt(end_time))
            if pollutant:
                p_attr = pollutant.lower().replace(".", "").replace("-", "")
                if hasattr(StationHourlyObservationModel, p_attr):
                    q = q.filter(getattr(StationHourlyObservationModel, p_attr).isnot(None))

            models = q.order_by(StationHourlyObservationModel.recorded_at.asc()).all()
            return [self._to_station_entity(m) for m in models]
        finally:
            session.close()

    def get_station_observations_for_district(
        self,
        district: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[StationObservation]:
        session: Session = self.session_factory()
        try:
            target = district.strip().lower()
            q = session.query(StationHourlyObservationModel).join(
                SpatialStationModel, StationHourlyObservationModel.station_id == SpatialStationModel.station_id
            ).filter(
                func.lower(SpatialStationModel.district) == target
            )
            if start_time:
                q = q.filter(StationHourlyObservationModel.recorded_at >= self._normalize_dt(start_time))
            if end_time:
                q = q.filter(StationHourlyObservationModel.recorded_at <= self._normalize_dt(end_time))

            models = q.order_by(StationHourlyObservationModel.recorded_at.asc()).all()
            return [self._to_station_entity(m) for m in models]
        finally:
            session.close()

    # =========================================================================
    # District Observation Queries
    # =========================================================================

    def get_district_observation(self, district_id: str, timestamp: datetime) -> Optional[DistrictObservation]:
        norm_dt = self._normalize_dt(timestamp)
        target = district_id.strip().lower()
        session: Session = self.session_factory()
        try:
            m = session.query(DistrictHourlyAggregateModel).filter(
                (func.lower(DistrictHourlyAggregateModel.district_id) == target) |
                (func.lower(DistrictHourlyAggregateModel.district_name) == target),
                DistrictHourlyAggregateModel.recorded_at == norm_dt,
            ).first()
            if not m:
                m = session.query(DistrictHourlyAggregateModel).filter(
                    (func.lower(DistrictHourlyAggregateModel.district_id) == target) |
                    (func.lower(DistrictHourlyAggregateModel.district_name) == target),
                    DistrictHourlyAggregateModel.recorded_at <= norm_dt,
                ).order_by(DistrictHourlyAggregateModel.recorded_at.desc()).first()
            return self._to_district_entity(m) if m else None
        finally:
            session.close()

    def get_latest_district_observations(self, pollutant: Optional[str] = None) -> List[DistrictObservation]:
        latest_ts = self.get_latest_timestamp()
        if latest_ts is None:
            return []
        return self.get_district_observations_at_timestamp(latest_ts, pollutant=pollutant)

    def get_district_observations_at_timestamp(
        self, timestamp: datetime, pollutant: Optional[str] = None
    ) -> List[DistrictObservation]:
        norm_dt = self._normalize_dt(timestamp)
        session: Session = self.session_factory()
        try:
            q = session.query(DistrictHourlyAggregateModel).filter(
                DistrictHourlyAggregateModel.recorded_at == norm_dt
            )
            if pollutant:
                p_attr = pollutant.lower().replace(".", "").replace("-", "")
                if hasattr(DistrictHourlyAggregateModel, p_attr):
                    q = q.filter(getattr(DistrictHourlyAggregateModel, p_attr).isnot(None))

            models = q.all()
            if not models:
                latest_avail_dt = session.query(
                    func.max(DistrictHourlyAggregateModel.recorded_at)
                ).filter(DistrictHourlyAggregateModel.recorded_at <= norm_dt).scalar()
                if latest_avail_dt:
                    q = session.query(DistrictHourlyAggregateModel).filter(
                        DistrictHourlyAggregateModel.recorded_at == latest_avail_dt
                    )
                    if pollutant:
                        p_attr = pollutant.lower().replace(".", "").replace("-", "")
                        if hasattr(DistrictHourlyAggregateModel, p_attr):
                            q = q.filter(getattr(DistrictHourlyAggregateModel, p_attr).isnot(None))
                    models = q.all()
            return [self._to_district_entity(m) for m in models]
        finally:
            session.close()


    def get_district_hourly_series(
        self,
        district_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        pollutant: Optional[str] = None,
    ) -> List[DistrictObservation]:
        target = district_id.strip().lower()
        session: Session = self.session_factory()
        try:
            q = session.query(DistrictHourlyAggregateModel).filter(
                (func.lower(DistrictHourlyAggregateModel.district_id) == target) |
                (func.lower(DistrictHourlyAggregateModel.district_name) == target)
            )
            if start_time:
                q = q.filter(DistrictHourlyAggregateModel.recorded_at >= self._normalize_dt(start_time))
            if end_time:
                q = q.filter(DistrictHourlyAggregateModel.recorded_at <= self._normalize_dt(end_time))
            if pollutant:
                p_attr = pollutant.lower().replace(".", "").replace("-", "")
                if hasattr(DistrictHourlyAggregateModel, p_attr):
                    q = q.filter(getattr(DistrictHourlyAggregateModel, p_attr).isnot(None))

            models = q.order_by(DistrictHourlyAggregateModel.recorded_at.asc()).all()
            return [self._to_district_entity(m) for m in models]
        finally:
            session.close()

    # =========================================================================
    # Timeline & Scrubber Indexing
    # =========================================================================

    def get_available_timestamps(self) -> List[datetime]:
        if not self._timeline_cache:
            self._refresh_timeline_cache()
        return list(self._timeline_cache)

    def get_latest_timestamp(self) -> Optional[datetime]:
        if not self._timeline_cache:
            self._refresh_timeline_cache()
        return self._timeline_cache[-1] if self._timeline_cache else None

    def get_earliest_timestamp(self) -> Optional[datetime]:
        if not self._timeline_cache:
            self._refresh_timeline_cache()
        return self._timeline_cache[0] if self._timeline_cache else None

    def get_timestamp_by_index(self, index: int) -> Optional[datetime]:
        if not self._timeline_cache:
            self._refresh_timeline_cache()
        if not self._timeline_cache:
            return None
        if index == -1 or index >= len(self._timeline_cache):
            return self._timeline_cache[-1]
        if index < 0:
            return self._timeline_cache[0]
        return self._timeline_cache[index]

    def get_hour_index(self, timestamp: datetime) -> Optional[int]:
        norm_dt = self._normalize_dt(timestamp)
        if norm_dt in self._time_to_idx_cache:
            return self._time_to_idx_cache[norm_dt]
        if not self._timeline_cache:
            return None
        # Nearest index
        idx = bisect_left(self._timeline_cache, norm_dt)
        if idx >= len(self._timeline_cache):
            return len(self._timeline_cache) - 1
        return idx

    def total_hours(self) -> int:
        if not self._timeline_cache:
            self._refresh_timeline_cache()
        return len(self._timeline_cache)

    # =========================================================================
    # Ingestion & Dynamic Storage (ON CONFLICT Deduplication)
    # =========================================================================

    def add_station_observation(self, observation: StationObservation) -> None:
        self.add_station_observations([observation])

    def add_station_observations(self, observations: Sequence[StationObservation]) -> None:
        """
        Bulk upsert observations into TimescaleDB hypertable station_hourly_observations.
        Enforces ON CONFLICT (recorded_at, station_id) DO UPDATE (Challenge 2.1).
        """
        if not observations:
            return

        session: Session = self.session_factory()
        try:
            is_postgres = (self.engine.dialect.name == "postgresql")
            new_timestamps = False

            for obs in observations:
                norm_dt = self._normalize_dt(obs.recorded_at)
                if norm_dt not in self._time_to_idx_cache:
                    new_timestamps = True

                row_dict = {
                    "recorded_at": norm_dt,
                    "station_id": str(obs.station_id),
                    "pm25": obs.pm25,
                    "pm10": obs.pm10,
                    "no2": obs.no2,
                    "so2": obs.so2,
                    "co": obs.co,
                    "o3": obs.o3,
                    "no": obs.no,
                    "nox": obs.nox,
                    "aqi_pepc": float(obs.aqi) if obs.aqi is not None else None,
                    "wind_speed_ms": obs.wind_speed,
                    "wind_direction_deg": obs.wind_direction,
                    "u_ms": obs.u,
                    "v_ms": obs.v,
                    "temp_c": obs.temperature_c,
                    "rh_pct": obs.relative_humidity_pct,
                    "qc_flags": obs.qc_flags,
                }

                if is_postgres:
                    stmt = pg_insert(StationHourlyObservationModel).values(row_dict)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["recorded_at", "station_id"],
                        set_={
                            "pm25": stmt.excluded.pm25,
                            "pm10": stmt.excluded.pm10,
                            "no2": stmt.excluded.no2,
                            "so2": stmt.excluded.so2,
                            "co": stmt.excluded.co,
                            "o3": stmt.excluded.o3,
                            "no": stmt.excluded.no,
                            "nox": stmt.excluded.nox,
                            "aqi_pepc": stmt.excluded.aqi_pepc,
                            "wind_speed_ms": stmt.excluded.wind_speed_ms,
                            "wind_direction_deg": stmt.excluded.wind_direction_deg,
                            "u_ms": stmt.excluded.u_ms,
                            "v_ms": stmt.excluded.v_ms,
                            "temp_c": stmt.excluded.temp_c,
                            "rh_pct": stmt.excluded.rh_pct,
                            "qc_flags": stmt.excluded.qc_flags,
                        }
                    )
                    session.execute(stmt)
                else:
                    # SQLite or generic fallback merge
                    existing = session.query(StationHourlyObservationModel).filter(
                        StationHourlyObservationModel.station_id == row_dict["station_id"],
                        StationHourlyObservationModel.recorded_at == row_dict["recorded_at"],
                    ).first()
                    if existing:
                        for k, v in row_dict.items():
                            setattr(existing, k, v)
                    else:
                        session.add(StationHourlyObservationModel(**row_dict))

            session.commit()
            if new_timestamps:
                self._refresh_timeline_cache()

        except Exception as e:
            session.rollback()
            logger.error(f"Error in add_station_observations: {e}")
            raise
        finally:
            session.close()

    def add_district_observation(self, observation: DistrictObservation) -> None:
        self.add_district_observations([observation])

    def add_district_observations(self, observations: Sequence[DistrictObservation]) -> None:
        """
        Bulk upsert district summaries into TimescaleDB hypertable district_hourly_aggregates.
        """
        if not observations:
            return

        session: Session = self.session_factory()
        try:
            is_postgres = (self.engine.dialect.name == "postgresql")
            for obs in observations:
                norm_dt = self._normalize_dt(obs.recorded_at)
                row_dict = {
                    "recorded_at": norm_dt,
                    "district_id": str(obs.district_id),
                    "district_name": str(obs.district_id).capitalize(),
                    "pm25": obs.pm25,
                    "pm10": obs.pm10,
                    "no2": obs.no2,
                    "so2": obs.so2,
                    "co": obs.co,
                    "o3": obs.o3,
                    "aqi_pepc": float(obs.aqi) if obs.aqi is not None else None,
                    "u_ms": obs.u if obs.u is not None else 0.0,
                    "v_ms": obs.v if obs.v is not None else 0.0,
                    "wind_speed_ms": obs.wind_speed if obs.wind_speed is not None else 0.0,
                    "wind_direction_deg": obs.wind_direction if obs.wind_direction is not None else 0.0,
                    "is_estimated": obs.is_estimated,
                    "reporting_stations_count": 1 if not obs.is_estimated else 0,
                }

                if is_postgres:
                    stmt = pg_insert(DistrictHourlyAggregateModel).values(row_dict)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["recorded_at", "district_id"],
                        set_={
                            "pm25": stmt.excluded.pm25,
                            "pm10": stmt.excluded.pm10,
                            "no2": stmt.excluded.no2,
                            "so2": stmt.excluded.so2,
                            "co": stmt.excluded.co,
                            "o3": stmt.excluded.o3,
                            "aqi_pepc": stmt.excluded.aqi_pepc,
                            "u_ms": stmt.excluded.u_ms,
                            "v_ms": stmt.excluded.v_ms,
                            "wind_speed_ms": stmt.excluded.wind_speed_ms,
                            "wind_direction_deg": stmt.excluded.wind_direction_deg,
                            "is_estimated": stmt.excluded.is_estimated,
                            "reporting_stations_count": stmt.excluded.reporting_stations_count,
                        }
                    )
                    session.execute(stmt)
                else:
                    existing = session.query(DistrictHourlyAggregateModel).filter(
                        DistrictHourlyAggregateModel.district_id == row_dict["district_id"],
                        DistrictHourlyAggregateModel.recorded_at == row_dict["recorded_at"],
                    ).first()
                    if existing:
                        for k, v in row_dict.items():
                            setattr(existing, k, v)
                    else:
                        session.add(DistrictHourlyAggregateModel(**row_dict))

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error in add_district_observations: {e}")
            raise
        finally:
            session.close()
