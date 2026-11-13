"""
Database DDL and Schema Initializer for Punjab Air Quality Relational Core, PostGIS, and TimescaleDB.
Executes DDL statements conforming strictly to docs/SYSTEM_ARCHITECTURE.md §§ 4.1, 4.2.
"""
import logging
from typing import Dict, Any, List
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.infrastructure.database.connection import Base
from src.infrastructure.database.models import (
    SpatialDistrictModel,
    SpatialStationModel,
    StationHourlyObservationModel,
    DistrictHourlyAggregateModel,
    InterdistrictTransportFluxModel,
)

logger = logging.getLogger("paq.ddl")

# Raw PostgreSQL + PostGIS + TimescaleDB Production DDL
POSTGRESQL_TIMESCALE_POSTGIS_DDL = """
-- 1. Extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- 2. Spatial Districts Table
CREATE TABLE IF NOT EXISTS spatial_districts (
    district_id SERIAL PRIMARY KEY,
    id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(64) UNIQUE NOT NULL,
    division VARCHAR(64) NOT NULL,
    is_monitored BOOLEAN NOT NULL DEFAULT FALSE,
    centroid_lat DOUBLE PRECISION NOT NULL,
    centroid_lon DOUBLE PRECISION NOT NULL,
    centroid_geom TEXT,
    boundary_geom TEXT,
    border_distance_km DOUBLE PRECISION NOT NULL DEFAULT 999.0,
    india_inflow_sectors_json TEXT NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Spatial Stations Table
CREATE TABLE IF NOT EXISTS spatial_stations (
    station_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    district_id INTEGER REFERENCES spatial_districts(district_id),
    district VARCHAR(64) NOT NULL,
    station_type VARCHAR(32) NOT NULL DEFAULT 'fixed' CHECK (station_type IN ('fixed', 'mobile', 'airport_metar', 'wmo_synop')),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    location_geom TEXT,
    has_anemometer BOOLEAN NOT NULL DEFAULT FALSE,
    anemometer_blacklisted BOOLEAN NOT NULL DEFAULT FALSE,
    altitude_m DOUBLE PRECISION,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Station Hourly Observations Hypertable
CREATE TABLE IF NOT EXISTS station_hourly_observations (
    recorded_at TIMESTAMPTZ NOT NULL,
    station_id VARCHAR(64) NOT NULL REFERENCES spatial_stations(station_id),
    pm25 DOUBLE PRECISION,
    pm10 DOUBLE PRECISION,
    no2 DOUBLE PRECISION,
    so2 DOUBLE PRECISION,
    co DOUBLE PRECISION,
    o3 DOUBLE PRECISION,
    no DOUBLE PRECISION,
    nox DOUBLE PRECISION,
    aqi_pepc DOUBLE PRECISION,
    wind_speed_ms DOUBLE PRECISION,
    wind_direction_deg DOUBLE PRECISION,
    u_ms DOUBLE PRECISION,
    v_ms DOUBLE PRECISION,
    temp_c DOUBLE PRECISION,
    rh_pct DOUBLE PRECISION,
    qc_flags INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT pk_station_hourly PRIMARY KEY (recorded_at, station_id)
);

-- 5. District Hourly Aggregates Hypertable
CREATE TABLE IF NOT EXISTS district_hourly_aggregates (
    recorded_at TIMESTAMPTZ NOT NULL,
    district_id VARCHAR(64) NOT NULL,
    district_name VARCHAR(64) NOT NULL,
    pm25 DOUBLE PRECISION,
    pm10 DOUBLE PRECISION,
    no2 DOUBLE PRECISION,
    so2 DOUBLE PRECISION,
    co DOUBLE PRECISION,
    o3 DOUBLE PRECISION,
    no DOUBLE PRECISION,
    nox DOUBLE PRECISION,
    aqi_pepc DOUBLE PRECISION,
    u_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    v_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    wind_speed_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    wind_direction_deg DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    is_estimated BOOLEAN NOT NULL DEFAULT FALSE,
    reporting_stations_count INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT pk_district_hourly PRIMARY KEY (recorded_at, district_id)
);

-- 6. Inter-District Transport Flux Hypertable
CREATE TABLE IF NOT EXISTS interdistrict_transport_flux (
    recorded_at TIMESTAMPTZ NOT NULL,
    source_district_id VARCHAR(64) NOT NULL,
    receptor_district_id VARCHAR(64) NOT NULL,
    pollutant VARCHAR(16) NOT NULL,
    flux_value DOUBLE PRECISION NOT NULL,
    angular_divergence_deg DOUBLE PRECISION NOT NULL,
    effective_distance_km DOUBLE PRECISION NOT NULL,
    CONSTRAINT pk_transport_flux PRIMARY KEY (recorded_at, source_district_id, receptor_district_id, pollutant)
);
"""


def check_extension_available(engine: Engine, ext_name: str) -> bool:
    """Checks whether an extension is installed or available in PostgreSQL."""
    if engine.dialect.name != "postgresql":
        return False
    try:
        with engine.connect() as conn:
            query = text("SELECT 1 FROM pg_available_extensions WHERE name = :name")
            return conn.execute(query, {"name": ext_name}).scalar() == 1
    except Exception:
        return False


def init_schema(engine: Engine) -> Dict[str, Any]:
    """
    Initializes database schema, creates ORM tables, and executes PostGIS & TimescaleDB setup.
    Detects PostgreSQL extensions dynamically.
    """
    results: Dict[str, Any] = {
        "engine_dialect": engine.dialect.name,
        "tables_created": [],
        "postgis_enabled": False,
        "timescaledb_enabled": False,
        "hypertables_created": [],
        "compression_policies_applied": [],
    }

    logger.info(f"Initializing Relational Core schema on dialect: {engine.dialect.name}")

    # 1. Base ORM tables creation
    Base.metadata.create_all(engine)
    results["tables_created"] = list(Base.metadata.tables.keys())

    # If running on non-PostgreSQL (e.g. SQLite test engine), ORM tables are sufficient
    if engine.dialect.name != "postgresql":
        logger.info("Non-PostgreSQL dialect detected. Completed ORM tables setup.")
        return results

    # 2. Check and enable PostgreSQL extensions
    with engine.begin() as conn:
        # Check PostGIS
        if check_extension_available(engine, "postgis"):
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
                results["postgis_enabled"] = True
                logger.info("PostGIS extension enabled.")
                
                # Check if geometry columns should be added
                try:
                    conn.execute(text("""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns 
                                WHERE table_name = 'spatial_districts' AND column_name = 'boundary'
                            ) THEN
                                ALTER TABLE spatial_districts ADD COLUMN boundary GEOMETRY(MultiPolygon, 4326);
                                CREATE INDEX IF NOT EXISTS idx_spatial_districts_boundary ON spatial_districts USING GIST(boundary);
                            END IF;
                            
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns 
                                WHERE table_name = 'spatial_stations' AND column_name = 'location'
                            ) THEN
                                ALTER TABLE spatial_stations ADD COLUMN location GEOMETRY(Point, 4326);
                                CREATE INDEX IF NOT EXISTS idx_spatial_stations_location ON spatial_stations USING GIST(location);
                            END IF;
                        END $$;
                    """))
                except Exception as postgis_col_err:
                    logger.warning(f"PostGIS geometry columns setup notice: {postgis_col_err}")

            except Exception as e:
                logger.warning(f"Could not enable PostGIS extension: {e}")

        # Check TimescaleDB
        if check_extension_available(engine, "timescaledb"):
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
                results["timescaledb_enabled"] = True
                logger.info("TimescaleDB extension enabled.")

                # Convert tables to Hypertables with configured chunk intervals
                hypertable_configs = [
                    ("station_hourly_observations", "recorded_at", "30 days"),
                    ("district_hourly_aggregates", "recorded_at", "14 days"),
                    ("interdistrict_transport_flux", "recorded_at", "14 days"),
                ]

                for table_name, time_col, chunk_interval in hypertable_configs:
                    try:
                        conn.execute(text(f"""
                            SELECT create_hypertable(
                                '{table_name}', 
                                '{time_col}', 
                                chunk_time_interval => INTERVAL '{chunk_interval}',
                                if_not_exists => TRUE
                            );
                        """))
                        results["hypertables_created"].append(table_name)
                        logger.info(f"Created TimescaleDB hypertable for {table_name} (chunk: {chunk_interval})")
                    except Exception as ht_err:
                        logger.warning(f"Hypertable creation notice for {table_name}: {ht_err}")

                # Configure LZ4 Delta Compression policies
                try:
                    conn.execute(text("""
                        ALTER TABLE station_hourly_observations SET (
                            timescaledb.compress,
                            timescaledb.compress_segmentby = 'station_id',
                            timescaledb.compress_orderby = 'recorded_at DESC'
                        );
                    """))
                    conn.execute(text("""
                        SELECT add_compression_policy('station_hourly_observations', INTERVAL '14 days', if_not_exists => TRUE);
                    """))
                    results["compression_policies_applied"].append("station_hourly_observations")

                    conn.execute(text("""
                        ALTER TABLE interdistrict_transport_flux SET (
                            timescaledb.compress,
                            timescaledb.compress_segmentby = 'source_district_id, receptor_district_id, pollutant',
                            timescaledb.compress_orderby = 'recorded_at DESC'
                        );
                    """))
                    conn.execute(text("""
                        SELECT add_compression_policy('interdistrict_transport_flux', INTERVAL '14 days', if_not_exists => TRUE);
                    """))
                    conn.execute(text("""
                        SELECT add_retention_policy('interdistrict_transport_flux', INTERVAL '180 days', if_not_exists => TRUE);
                    """))
                    results["compression_policies_applied"].append("interdistrict_transport_flux")
                    logger.info("Configured LZ4 compression and retention policies on hypertables.")
                except Exception as comp_err:
                    logger.warning(f"TimescaleDB compression policy notice: {comp_err}")

            except Exception as e:
                logger.warning(f"Could not enable TimescaleDB extension: {e}")

    return results
