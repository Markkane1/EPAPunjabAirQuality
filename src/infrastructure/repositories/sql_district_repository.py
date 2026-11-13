"""
SQL District Repository implementation for Punjab Air Quality Relational Core and PostGIS.
Implements DistrictRepository domain interface using PostgreSQL / SQLAlchemy.
"""
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from src.domain.entities.models import District, LabelPlacement
from src.domain.interfaces.repositories import DistrictRepository
from src.infrastructure.database.models import SpatialDistrictModel

logger = logging.getLogger("paq.repositories.sql_district")


class SqlDistrictRepository(DistrictRepository):
    """
    Relational and spatial implementation of DistrictRepository backed by spatial_districts table.
    """

    def __init__(self, session_factory: Any) -> None:
        self.session_factory = session_factory
        self._boundaries_cache: Dict[str, Dict[str, Any]] = {}
        self._labels_cache: Dict[str, LabelPlacement] = {}

    def _to_entity(self, model: SpatialDistrictModel) -> District:
        """Maps ORM model to domain District entity."""
        return District(
            id=model.id,
            name=model.name,
            division=model.division,
            latitude=model.centroid_lat,
            longitude=model.centroid_lon,
            is_monitored=model.is_monitored,
            border_distance_km=model.border_distance_km,
            india_inflow_sectors=tuple(model.india_inflow_sectors),
        )

    def get_by_id(self, district_id: str) -> Optional[District]:
        session: Session = self.session_factory()
        try:
            target = district_id.strip().lower()
            m = session.query(SpatialDistrictModel).filter(
                (SpatialDistrictModel.id == target) | (func.lower(SpatialDistrictModel.name) == target)
            ).first()
            return self._to_entity(m) if m else None
        finally:
            session.close()

    def get_by_name(self, name: str) -> Optional[District]:
        session: Session = self.session_factory()
        try:
            target = name.strip().lower()
            m = session.query(SpatialDistrictModel).filter(
                func.lower(SpatialDistrictModel.name) == target
            ).first()
            return self._to_entity(m) if m else None
        finally:
            session.close()

    def list_all(self, monitored_only: bool = False) -> List[District]:
        session: Session = self.session_factory()
        try:
            q = session.query(SpatialDistrictModel)
            if monitored_only:
                q = q.filter(SpatialDistrictModel.is_monitored == True)
            models = q.order_by(SpatialDistrictModel.name.asc()).all()
            return [self._to_entity(m) for m in models]
        finally:
            session.close()

    def list_border_districts(self, max_border_distance_km: float = 120.0) -> List[District]:
        session: Session = self.session_factory()
        try:
            models = session.query(SpatialDistrictModel).filter(
                SpatialDistrictModel.border_distance_km <= max_border_distance_km
            ).order_by(SpatialDistrictModel.border_distance_km.asc()).all()
            return [self._to_entity(m) for m in models]
        finally:
            session.close()

    def count(self) -> int:
        session: Session = self.session_factory()
        try:
            return session.query(SpatialDistrictModel).count()
        finally:
            session.close()

    def get_boundary_geometry(self, district_id: str) -> Optional[Dict[str, Any]]:
        target = district_id.strip().lower()
        if target in self._boundaries_cache:
            return self._boundaries_cache[target]

        session: Session = self.session_factory()
        try:
            m = session.query(SpatialDistrictModel).filter(
                (SpatialDistrictModel.id == target) | (func.lower(SpatialDistrictModel.name) == target)
            ).first()
            if m and m.boundary_geom:
                try:
                    parsed = json.loads(m.boundary_geom)
                    self._boundaries_cache[target] = parsed
                    return parsed
                except Exception as e:
                    logger.warning(f"Error parsing boundary GeoJSON for {target}: {e}")
            return None
        finally:
            session.close()

    def get_label_placement(self, district_id: str) -> Optional[LabelPlacement]:
        target = district_id.strip().lower()
        if target in self._labels_cache:
            return self._labels_cache[target]

        # Query district coordinates
        d = self.get_by_id(target)
        if not d:
            return None

        # Build standard collision-free placement
        placement = LabelPlacement(
            district_id=d.id,
            text=d.name,
            anchor_x=d.longitude,
            anchor_y=d.latitude,
            offset_x=0.0,
            offset_y=0.0,
            width=len(d.name) * 7.5,
            height=14.0,
            has_leader_line=False,
        )
        self._labels_cache[target] = placement
        return placement

    def set_label_placement(self, district_id: str, placement: LabelPlacement) -> None:
        self._labels_cache[district_id.strip().lower()] = placement
