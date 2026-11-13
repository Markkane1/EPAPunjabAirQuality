"""
SQL Station Repository implementation for Punjab Air Quality Relational Core.
Implements StationRepository domain interface using PostgreSQL / SQLAlchemy.
"""
import logging
from typing import Any, Dict, List, Optional, Sequence
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from src.domain.entities.models import Station
from src.domain.interfaces.repositories import StationRepository
from src.infrastructure.database.models import SpatialStationModel

logger = logging.getLogger("paq.repositories.sql_station")


class SqlStationRepository(StationRepository):
    """
    Relational implementation of StationRepository backed by spatial_stations table in PostgreSQL.
    """

    def __init__(self, session_factory: Any) -> None:
        self.session_factory = session_factory

    def _to_entity(self, model: SpatialStationModel) -> Station:
        """Maps ORM model to domain Station entity."""
        return Station(
            id=model.station_id,
            name=model.name,
            district=model.district,
            latitude=model.latitude,
            longitude=model.longitude,
            station_type=model.station_type,
            has_anemometer=model.has_anemometer,
            anemometer_blacklisted=model.anemometer_blacklisted,
            altitude_m=model.altitude_m,
            metadata={"is_active": model.is_active},
        )

    def get_by_id(self, station_id: str) -> Optional[Station]:
        session: Session = self.session_factory()
        try:
            m = session.query(SpatialStationModel).filter(
                SpatialStationModel.station_id == str(station_id)
            ).first()
            return self._to_entity(m) if m else None
        finally:
            session.close()

    def get_by_name(self, name: str) -> Optional[Station]:
        session: Session = self.session_factory()
        try:
            target = name.strip().lower()
            m = session.query(SpatialStationModel).filter(
                func.lower(SpatialStationModel.name) == target
            ).first()
            return self._to_entity(m) if m else None
        finally:
            session.close()

    def list_all(self, station_type: Optional[str] = None) -> List[Station]:
        session: Session = self.session_factory()
        try:
            q = session.query(SpatialStationModel).filter(SpatialStationModel.is_active == True)
            if station_type:
                q = q.filter(SpatialStationModel.station_type == station_type)
            models = q.all()
            return [self._to_entity(m) for m in models]
        finally:
            session.close()

    def list_by_district(self, district: str) -> List[Station]:
        session: Session = self.session_factory()
        try:
            target = district.strip().lower()
            models = session.query(SpatialStationModel).filter(
                SpatialStationModel.is_active == True,
                func.lower(SpatialStationModel.district) == target,
            ).all()
            return [self._to_entity(m) for m in models]
        finally:
            session.close()

    def list_airports(self) -> List[Station]:
        return self.list_all(station_type="airport_metar")

    def exists(self, station_id: str) -> bool:
        session: Session = self.session_factory()
        try:
            count = session.query(SpatialStationModel).filter(
                SpatialStationModel.station_id == str(station_id)
            ).count()
            return count > 0
        finally:
            session.close()

    def count(self) -> int:
        session: Session = self.session_factory()
        try:
            return session.query(SpatialStationModel).filter(SpatialStationModel.is_active == True).count()
        finally:
            session.close()

    def add_station(self, station: Station) -> None:
        self.add_stations([station])

    def add_stations(self, stations: Sequence[Station]) -> None:
        if not stations:
            return
        session: Session = self.session_factory()
        try:
            for s in stations:
                existing = session.query(SpatialStationModel).filter(
                    SpatialStationModel.station_id == s.id
                ).first()
                if existing:
                    existing.name = s.name
                    existing.district = s.district
                    existing.latitude = s.latitude
                    existing.longitude = s.longitude
                    existing.station_type = s.station_type
                    existing.has_anemometer = s.has_anemometer
                    existing.anemometer_blacklisted = s.anemometer_blacklisted
                    existing.altitude_m = s.altitude_m
                else:
                    new_model = SpatialStationModel(
                        station_id=s.id,
                        name=s.name,
                        district=s.district,
                        latitude=s.latitude,
                        longitude=s.longitude,
                        station_type=s.station_type,
                        has_anemometer=s.has_anemometer,
                        anemometer_blacklisted=s.anemometer_blacklisted,
                        altitude_m=s.altitude_m,
                        is_active=True,
                    )
                    session.add(new_model)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
