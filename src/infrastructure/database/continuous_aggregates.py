"""
Continuous Aggregates Engine for TimescaleDB and Automated Database Rollups.
Replaces in-memory bisect range scans with automated database materialized continuous aggregates
for hourly and daily multi-pollutant rollups.
"""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

logger = logging.getLogger("paq.continuous_rollups")

# TimescaleDB Continuous Aggregates DDL
TIMESCALE_CONTINUOUS_AGGREGATES_DDL = """
-- 1. Hourly District Continuous Rollup Aggregate
CREATE MATERIALIZED VIEW IF NOT EXISTS district_hourly_cagg
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', o.recorded_at) AS bucket,
    s.district AS district,
    s.station_type,
    AVG(o.pm25) AS avg_pm25,
    AVG(o.pm10) AS avg_pm10,
    AVG(o.no2) AS avg_no2,
    AVG(o.so2) AS avg_so2,
    AVG(o.co) AS avg_co,
    AVG(o.o3) AS avg_o3,
    AVG(o.aqi_pepc) AS avg_aqi,
    AVG(o.u_ms) AS avg_u,
    AVG(o.v_ms) AS avg_v,
    AVG(o.wind_speed_ms) AS avg_wind_speed,
    COUNT(o.pm25) AS reporting_count
FROM station_hourly_observations o
JOIN spatial_stations s ON o.station_id = s.station_id
GROUP BY bucket, s.district, s.station_type
WITH NO DATA;

-- Continuous Aggregate Refresh Policy: Refresh hourly buckets every 15 minutes
SELECT add_continuous_aggregate_policy('district_hourly_cagg',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '15 minutes',
    if_not_exists => TRUE
);

-- 2. Daily District Continuous Rollup Aggregate
CREATE MATERIALIZED VIEW IF NOT EXISTS district_daily_cagg
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', o.recorded_at) AS bucket,
    s.district AS district,
    AVG(o.pm25) AS daily_avg_pm25,
    MAX(o.pm25) AS daily_max_pm25,
    MIN(o.pm25) AS daily_min_pm25,
    AVG(o.pm10) AS daily_avg_pm10,
    MAX(o.pm10) AS daily_max_pm10,
    AVG(o.aqi_pepc) AS daily_avg_aqi,
    MAX(o.aqi_pepc) AS daily_max_aqi,
    COUNT(*) AS total_samples
FROM station_hourly_observations o
JOIN spatial_stations s ON o.station_id = s.station_id
GROUP BY bucket, s.district
WITH NO DATA;

-- Daily Continuous Aggregate Refresh Policy: Refresh daily buckets every 1 hour
SELECT add_continuous_aggregate_policy('district_daily_cagg',
    start_offset => INTERVAL '30 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);
"""


class ContinuousRollupService:
    """
    Coordinates automated database rollups across hourly and daily intervals.
    Executes against TimescaleDB continuous aggregate views when active, or issues
    optimized SQL date_trunc group-by aggregations directly in PostgreSQL.
    """

    def __init__(self, engine: Engine, session_factory: Any) -> None:
        self.engine = engine
        self.session_factory = session_factory
        self.has_cagg: bool = False
        self._check_continuous_aggregates()

    def _check_continuous_aggregates(self) -> None:
        """Checks if TimescaleDB continuous aggregates exist in the database."""
        if self.engine.dialect.name != "postgresql":
            self.has_cagg = False
            return
        try:
            with self.engine.connect() as conn:
                res = conn.execute(
                    text("SELECT 1 FROM pg_matviews WHERE matviewname = 'district_hourly_cagg'")
                ).scalar()
                self.has_cagg = (res == 1)
        except Exception:
            self.has_cagg = False

    def setup_continuous_aggregates(self) -> bool:
        """Attempts to create TimescaleDB continuous aggregate materialized views."""
        if self.engine.dialect.name != "postgresql":
            return False
        try:
            with self.engine.begin() as conn:
                # Check if timescaledb extension is active
                has_ts = conn.execute(
                    text("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'")
                ).scalar() == 1
                if not has_ts:
                    return False

                conn.execute(text(TIMESCALE_CONTINUOUS_AGGREGATES_DDL))
                self.has_cagg = True
                logger.info("Successfully created TimescaleDB continuous aggregate views and refresh policies.")
                return True
        except Exception as e:
            logger.warning(f"Could not initialize TimescaleDB continuous aggregate views: {e}")
            self.has_cagg = False
            return False

    def get_hourly_district_rollup(
        self,
        district: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        pollutant: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves automated hourly rollups for a district across a time window.
        Uses database continuous aggregates for O(1) performance instead of Python bisect scans.
        """
        session = self.session_factory()
        try:
            if self.has_cagg:
                query_str = """
                    SELECT bucket, district, avg_pm25, avg_pm10, avg_no2, avg_so2, avg_co, avg_o3,
                           avg_aqi, avg_u, avg_v, avg_wind_speed, reporting_count
                    FROM district_hourly_cagg
                    WHERE LOWER(district) = LOWER(:district)
                """
                params: Dict[str, Any] = {"district": district}
                if start_time:
                    query_str += " AND bucket >= :start_time"
                    params["start_time"] = start_time
                if end_time:
                    query_str += " AND bucket <= :end_time"
                    params["end_time"] = end_time
                query_str += " ORDER BY bucket ASC"
                if limit is not None:
                    query_str += f" LIMIT {int(limit)}"
            else:
                # Automated SQL rollup fallback
                if self.engine.dialect.name == "postgresql":
                    trunc_expr = "date_trunc('hour', o.recorded_at)"
                else:
                    trunc_expr = "strftime('%Y-%m-%d %H:00:00', o.recorded_at)"

                query_str = f"""
                    SELECT 
                        {trunc_expr} AS bucket,
                        s.district,
                        AVG(o.pm25) AS avg_pm25,
                        AVG(o.pm10) AS avg_pm10,
                        AVG(o.no2) AS avg_no2,
                        AVG(o.so2) AS avg_so2,
                        AVG(o.co) AS avg_co,
                        AVG(o.o3) AS avg_o3,
                        AVG(o.aqi_pepc) AS avg_aqi,
                        AVG(o.u_ms) AS avg_u,
                        AVG(o.v_ms) AS avg_v,
                        AVG(o.wind_speed_ms) AS avg_wind_speed,
                        COUNT(o.pm25) AS reporting_count
                    FROM station_hourly_observations o
                    JOIN spatial_stations s ON o.station_id = s.station_id
                    WHERE LOWER(s.district) = LOWER(:district)
                """
                params = {"district": district}
                if start_time:
                    query_str += " AND o.recorded_at >= :start_time"
                    params["start_time"] = start_time
                if end_time:
                    query_str += " AND o.recorded_at <= :end_time"
                    params["end_time"] = end_time
                query_str += f" GROUP BY {trunc_expr}, s.district ORDER BY bucket ASC"
                if limit is not None:
                    query_str += f" LIMIT {int(limit)}"


            res = session.execute(text(query_str), params).fetchall()
            results = []
            for row in res:
                results.append({
                    "timestamp": row.bucket.isoformat() if hasattr(row.bucket, "isoformat") else str(row.bucket),
                    "district": row.district,
                    "pm25": round(row.avg_pm25, 2) if row.avg_pm25 is not None else None,
                    "pm10": round(row.avg_pm10, 2) if row.avg_pm10 is not None else None,
                    "no2": round(row.avg_no2, 2) if row.avg_no2 is not None else None,
                    "so2": round(row.avg_so2, 2) if row.avg_so2 is not None else None,
                    "co": round(row.avg_co, 2) if row.avg_co is not None else None,
                    "o3": round(row.avg_o3, 2) if row.avg_o3 is not None else None,
                    "aqi": round(row.avg_aqi, 1) if row.avg_aqi is not None else None,
                    "u": round(row.avg_u, 2) if row.avg_u is not None else 0.0,
                    "v": round(row.avg_v, 2) if row.avg_v is not None else 0.0,
                    "wind_speed": round(row.avg_wind_speed, 2) if row.avg_wind_speed is not None else 0.0,
                    "reporting_count": int(row.reporting_count) if row.reporting_count is not None else 0,
                })
            return results
        finally:
            session.close()

    def get_daily_district_rollup(
        self,
        district: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves automated daily rollups (mean, min, max, AQI peak) for a district.
        """
        session = self.session_factory()
        try:
            if self.has_cagg:
                query_str = """
                    SELECT bucket, district, daily_avg_pm25, daily_max_pm25, daily_min_pm25,
                           daily_avg_pm10, daily_max_pm10, daily_avg_aqi, daily_max_aqi, total_samples
                    FROM district_daily_cagg
                    WHERE LOWER(district) = LOWER(:district)
                """
                params: Dict[str, Any] = {"district": district}
                if start_time:
                    query_str += " AND bucket >= :start_time"
                    params["start_time"] = start_time
                if end_time:
                    query_str += " AND bucket <= :end_time"
                    params["end_time"] = end_time
                query_str += " ORDER BY bucket ASC"
                if limit is not None:
                    query_str += f" LIMIT {int(limit)}"
            else:
                if self.engine.dialect.name == "postgresql":
                    trunc_expr = "date_trunc('day', o.recorded_at)"
                else:
                    trunc_expr = "strftime('%Y-%m-%d 00:00:00', o.recorded_at)"

                query_str = f"""
                    SELECT 
                        {trunc_expr} AS bucket,
                        s.district,
                        AVG(o.pm25) AS daily_avg_pm25,
                        MAX(o.pm25) AS daily_max_pm25,
                        MIN(o.pm25) AS daily_min_pm25,
                        AVG(o.pm10) AS daily_avg_pm10,
                        MAX(o.pm10) AS daily_max_pm10,
                        AVG(o.aqi_pepc) AS daily_avg_aqi,
                        MAX(o.aqi_pepc) AS daily_max_aqi,
                        COUNT(*) AS total_samples
                    FROM station_hourly_observations o
                    JOIN spatial_stations s ON o.station_id = s.station_id
                    WHERE LOWER(s.district) = LOWER(:district)
                """
                params = {"district": district}
                if start_time:
                    query_str += " AND o.recorded_at >= :start_time"
                    params["start_time"] = start_time
                if end_time:
                    query_str += " AND o.recorded_at <= :end_time"
                    params["end_time"] = end_time
                query_str += f" GROUP BY {trunc_expr}, s.district ORDER BY bucket ASC"
                if limit is not None:
                    query_str += f" LIMIT {int(limit)}"

            res = session.execute(text(query_str), params).fetchall()
            results = []
            for row in res:
                results.append({
                    "date": row.bucket.isoformat() if hasattr(row.bucket, "isoformat") else str(row.bucket),
                    "district": row.district,
                    "avg_pm25": round(row.daily_avg_pm25, 2) if row.daily_avg_pm25 is not None else None,
                    "max_pm25": round(row.daily_max_pm25, 2) if row.daily_max_pm25 is not None else None,
                    "min_pm25": round(row.daily_min_pm25, 2) if row.daily_min_pm25 is not None else None,
                    "avg_pm10": round(row.daily_avg_pm10, 2) if row.daily_avg_pm10 is not None else None,
                    "max_pm10": round(row.daily_max_pm10, 2) if row.daily_max_pm10 is not None else None,
                    "avg_aqi": round(row.daily_avg_aqi, 1) if row.daily_avg_aqi is not None else None,
                    "max_aqi": round(row.daily_max_aqi, 1) if row.daily_max_aqi is not None else None,
                    "samples": int(row.total_samples) if row.total_samples is not None else 0,
                })
            return results
        finally:
            session.close()

    get_hourly_rollups = get_hourly_district_rollup
    get_daily_rollups = get_daily_district_rollup

