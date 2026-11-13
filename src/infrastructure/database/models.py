"""
SQLAlchemy ORM Models for Relational Core, PostGIS Spatial Geometries, and TimescaleDB Hypertables.
Matches specifications in docs/SYSTEM_ARCHITECTURE.md §§ 4.1, 4.2.
"""
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
)
from sqlalchemy.sql import func

from src.infrastructure.database.connection import Base


class SpatialDistrictModel(Base):
    """
    Relational representation of administrative districts with PostGIS spatial geometry.
    Matches spatial_districts table in docs/SYSTEM_ARCHITECTURE.md §4.1.
    """
    __tablename__ = "spatial_districts"

    district_id = Column(Integer, primary_key=True, autoincrement=True)
    id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(64), unique=True, nullable=False, index=True)
    division = Column(String(64), nullable=False)
    is_monitored = Column(Boolean, nullable=False, default=False)
    centroid_lat = Column(Float, nullable=False)
    centroid_lon = Column(Float, nullable=False)
    centroid_geom = Column(Text, nullable=True)  # WKT / Point representation
    boundary_geom = Column(Text, nullable=True)  # GeoJSON / WKT boundary polygon
    border_distance_km = Column(Float, nullable=False, default=999.0)
    india_inflow_sectors_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    @property
    def india_inflow_sectors(self) -> List[int]:
        try:
            return json.loads(self.india_inflow_sectors_json)
        except Exception:
            return []

    @india_inflow_sectors.setter
    def india_inflow_sectors(self, val: List[int]) -> None:
        self.india_inflow_sectors_json = json.dumps(val)


class SpatialStationModel(Base):
    """
    Relational representation of ground air quality monitoring stations and aerodromes.
    Matches spatial_stations table in docs/SYSTEM_ARCHITECTURE.md §4.1.
    """
    __tablename__ = "spatial_stations"

    station_id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    district_id = Column(Integer, ForeignKey("spatial_districts.district_id"), nullable=True)
    district = Column(String(64), nullable=False, index=True)
    station_type = Column(String(32), nullable=False, default="fixed")  # 'fixed', 'mobile', 'airport_metar', 'wmo_synop'
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location_geom = Column(Text, nullable=True)  # WKT / Point representation
    has_anemometer = Column(Boolean, nullable=False, default=False)
    anemometer_blacklisted = Column(Boolean, nullable=False, default=False)
    altitude_m = Column(Float, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class StationHourlyObservationModel(Base):
    """
    TimescaleDB Hypertable for multi-pollutant and meteorological station observations.
    Partitioned into 30-day chunks with LZ4 compression policies.
    Matches station_hourly_observations table in docs/SYSTEM_ARCHITECTURE.md §4.2.
    """
    __tablename__ = "station_hourly_observations"

    recorded_at = Column(DateTime(timezone=True), nullable=False)
    station_id = Column(String(64), ForeignKey("spatial_stations.station_id"), nullable=False)
    pm25 = Column(Float, nullable=True)
    pm10 = Column(Float, nullable=True)
    no2 = Column(Float, nullable=True)
    so2 = Column(Float, nullable=True)
    co = Column(Float, nullable=True)
    o3 = Column(Float, nullable=True)
    no = Column(Float, nullable=True)
    nox = Column(Float, nullable=True)
    aqi_pepc = Column(Float, nullable=True)
    wind_speed_ms = Column(Float, nullable=True)
    wind_direction_deg = Column(Float, nullable=True)
    u_ms = Column(Float, nullable=True)
    v_ms = Column(Float, nullable=True)
    temp_c = Column(Float, nullable=True)
    rh_pct = Column(Float, nullable=True)
    qc_flags = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        PrimaryKeyConstraint("recorded_at", "station_id", name="pk_station_hourly"),
        Index("idx_station_hourly_lookup", "station_id", "recorded_at"),
    )


class DistrictHourlyAggregateModel(Base):
    """
    TimescaleDB Hypertable for district-level harmonized hourly summaries.
    Partitioned into 14-day chunks.
    Matches district_hourly_aggregates table in docs/SYSTEM_ARCHITECTURE.md §4.2.
    """
    __tablename__ = "district_hourly_aggregates"

    recorded_at = Column(DateTime(timezone=True), nullable=False)
    district_id = Column(String(64), nullable=False)
    district_name = Column(String(64), nullable=False)
    pm25 = Column(Float, nullable=True)
    pm10 = Column(Float, nullable=True)
    no2 = Column(Float, nullable=True)
    so2 = Column(Float, nullable=True)
    co = Column(Float, nullable=True)
    o3 = Column(Float, nullable=True)
    no = Column(Float, nullable=True)
    nox = Column(Float, nullable=True)
    aqi_pepc = Column(Float, nullable=True)
    u_ms = Column(Float, nullable=False, default=0.0)
    v_ms = Column(Float, nullable=False, default=0.0)
    wind_speed_ms = Column(Float, nullable=False, default=0.0)
    wind_direction_deg = Column(Float, nullable=False, default=0.0)
    is_estimated = Column(Boolean, nullable=False, default=False)
    reporting_stations_count = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        PrimaryKeyConstraint("recorded_at", "district_id", name="pk_district_hourly"),
        Index("idx_district_hourly_lookup", "district_id", "recorded_at"),
    )


class InterdistrictTransportFluxModel(Base):
    """
    TimescaleDB Hypertable for inter-district advection mass flux links.
    Partitioned into 14-day chunks with LZ4 compression policies and 180-day retention.
    Matches interdistrict_transport_flux table in docs/SYSTEM_ARCHITECTURE.md §4.2.
    """
    __tablename__ = "interdistrict_transport_flux"

    recorded_at = Column(DateTime(timezone=True), nullable=False)
    source_district_id = Column(String(64), nullable=False)
    receptor_district_id = Column(String(64), nullable=False)
    pollutant = Column(String(16), nullable=False)
    flux_value = Column(Float, nullable=False)
    angular_divergence_deg = Column(Float, nullable=False)
    effective_distance_km = Column(Float, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint(
            "recorded_at", "source_district_id", "receptor_district_id", "pollutant",
            name="pk_transport_flux"
        ),
        Index("idx_transport_flux_lookup", "source_district_id", "receptor_district_id", "recorded_at"),
    )
