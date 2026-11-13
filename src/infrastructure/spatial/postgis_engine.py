"""
PostGIS 3.4 Spatial Engine for Punjab Air Quality Workstation.
Implements GiST-indexed spatial queries, metric geodetic distances with ::geography casting (resolving Challenge 2.3),
and administrative polygon containment.
"""
from datetime import datetime
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

try:
    from shapely.geometry import Point as ShapelyPoint, shape as shapely_shape
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False

from src.domain.math.geodesy import haversine_distance

logger = logging.getLogger("paq.spatial_engine")


class PostgisSpatialEngine:
    """
    Geospatial engine managing PostGIS 3.4 spatial queries with GiST indexes.
    Enforces the PostGIS Geography Distance Query Rule: ST_DWithin(...::geography, ...::geography, meters).
    """

    def __init__(self, engine: Engine, session_factory: Any, postgis_active: bool = False) -> None:
        self.engine = engine
        self.session_factory = session_factory
        self.postgis_active = postgis_active or self._probe_postgis()

    def _probe_postgis(self) -> bool:
        """Probes whether PostGIS functions are executable on the database connection."""
        if self.engine.dialect.name != "postgresql":
            return False
        try:
            with self.engine.connect() as conn:
                res = conn.execute(
                    text("SELECT PostGIS_Version()")
                ).scalar()
                if res:
                    logger.info(f"PostGIS Spatial Engine active: {res}")
                    return True
        except Exception:
            pass
        return False

    def find_nearest_aerodrome(
        self,
        lat: float,
        lon: float,
        max_distance_km: float = 60.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Finds nearest airport aerodrome within max_distance_km radius.
        MUST cast to geography: ST_DWithin(location::geography, ST_SetSRID(ST_Point(lon, lat), 4326)::geography, meters)
        Evaluates distance in METERS rather than angular degrees (Challenge 2.3).
        """
        radius_meters = max_distance_km * 1000.0

        if self.postgis_active:
            query = text("""
                SELECT 
                    station_id, name, district, latitude, longitude,
                    ST_Distance(
                        location::geography, 
                        ST_SetSRID(ST_Point(:lon, :lat), 4326)::geography
                    ) AS distance_meters
                FROM spatial_stations
                WHERE station_type = 'airport_metar'
                  AND is_active = TRUE
                  AND ST_DWithin(
                      location::geography, 
                      ST_SetSRID(ST_Point(:lon, :lat), 4326)::geography, 
                      :radius_meters
                  )
                ORDER BY distance_meters ASC
                LIMIT 1;
            """)
            session = self.session_factory()
            try:
                row = session.execute(query, {
                    "lat": lat,
                    "lon": lon,
                    "radius_meters": radius_meters
                }).fetchone()
                if row:
                    return {
                        "station_id": row.station_id,
                        "name": row.name,
                        "district": row.district,
                        "latitude": row.latitude,
                        "longitude": row.longitude,
                        "distance_km": round(row.distance_meters / 1000.0, 3),
                    }
            except Exception as e:
                logger.warning(f"PostGIS aerodrome query failed, using geodetic fallback: {e}")
            finally:
                session.close()

        # Fallback: SQL fetch + haversine distance evaluation
        session = self.session_factory()
        try:
            query = text("""
                SELECT station_id, name, district, latitude, longitude
                FROM spatial_stations
                WHERE station_type = 'airport_metar' AND is_active = TRUE
            """)
            airports = session.execute(query).fetchall()
            best_airport = None
            min_dist = max_distance_km
            for a in airports:
                d = haversine_distance(lat, lon, a.latitude, a.longitude)
                if d <= min_dist:
                    min_dist = d
                    best_airport = {
                        "station_id": a.station_id,
                        "name": a.name,
                        "district": a.district,
                        "latitude": a.latitude,
                        "longitude": a.longitude,
                        "distance_km": round(d, 3),
                    }
            return best_airport
        finally:
            session.close()

    def find_stations_within_radius(
        self,
        lat: float,
        lon: float,
        radius_km: float,
        station_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Finds all monitoring stations within a metric distance radius (in kilometers)
        using ST_DWithin on geography types with GiST spatial indexing.
        """
        radius_meters = radius_km * 1000.0

        if self.postgis_active:
            type_filter = "AND station_type = :st_type" if station_type else ""
            query = text(f"""
                SELECT 
                    station_id, name, district, station_type, latitude, longitude,
                    ST_Distance(
                        location::geography, 
                        ST_SetSRID(ST_Point(:lon, :lat), 4326)::geography
                    ) AS distance_meters
                FROM spatial_stations
                WHERE is_active = TRUE
                  {type_filter}
                  AND ST_DWithin(
                      location::geography, 
                      ST_SetSRID(ST_Point(:lon, :lat), 4326)::geography, 
                      :radius_meters
                  )
                ORDER BY distance_meters ASC;
            """)
            session = self.session_factory()
            try:
                params: Dict[str, Any] = {"lat": lat, "lon": lon, "radius_meters": radius_meters}
                if station_type:
                    params["st_type"] = station_type
                rows = session.execute(query, params).fetchall()
                return [
                    {
                        "station_id": r.station_id,
                        "name": r.name,
                        "district": r.district,
                        "station_type": r.station_type,
                        "latitude": r.latitude,
                        "longitude": r.longitude,
                        "distance_km": round(r.distance_meters / 1000.0, 3),
                    }
                    for r in rows
                ]
            except Exception as e:
                logger.warning(f"PostGIS stations radius query failed, using geodetic fallback: {e}")
            finally:
                session.close()

        # Fallback: SQL fetch + haversine distance
        session = self.session_factory()
        try:
            sql = "SELECT station_id, name, district, station_type, latitude, longitude FROM spatial_stations WHERE is_active = TRUE"
            if station_type:
                sql += " AND station_type = :st_type"
            params = {"st_type": station_type} if station_type else {}
            rows = session.execute(text(sql), params).fetchall()
            results = []
            for r in rows:
                d = haversine_distance(lat, lon, r.latitude, r.longitude)
                if d <= radius_km:
                    results.append({
                        "station_id": r.station_id,
                        "name": r.name,
                        "district": r.district,
                        "station_type": r.station_type,
                        "latitude": r.latitude,
                        "longitude": r.longitude,
                        "distance_km": round(d, 3),
                    })
            results.sort(key=lambda x: x["distance_km"])
            return results
        finally:
            session.close()

    def find_district_for_point(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """
        Determines the administrative district containing a given (lat, lon) coordinate
        using PostGIS ST_Contains on MultiPolygon geometries with GiST boundary indexes.
        """
        if self.postgis_active:
            query = text("""
                SELECT district_id, id, name, division, is_monitored
                FROM spatial_districts
                WHERE ST_Contains(
                    boundary, 
                    ST_SetSRID(ST_Point(:lon, :lat), 4326)
                )
                LIMIT 1;
            """)
            session = self.session_factory()
            try:
                row = session.execute(query, {"lat": lat, "lon": lon}).fetchone()
                if row:
                    return {
                        "district_id": row.district_id,
                        "id": row.id,
                        "name": row.name,
                        "division": row.division,
                        "is_monitored": row.is_monitored,
                    }
            except Exception as e:
                logger.warning(f"PostGIS ST_Contains failed, using polygon fallback: {e}")
            finally:
                session.close()

        # Fallback: Shapely point-in-polygon containment
        if HAS_SHAPELY:
            session = self.session_factory()
            try:
                rows = session.execute(
                    text("SELECT district_id, id, name, division, is_monitored, centroid_lat, centroid_lon, boundary_geom FROM spatial_districts")
                ).fetchall()
                pt = ShapelyPoint(lon, lat)
                for r in rows:
                    if r.boundary_geom:
                        try:
                            geom_obj = json.loads(r.boundary_geom) if isinstance(r.boundary_geom, str) else r.boundary_geom
                            if isinstance(geom_obj, list):
                                # Determine whether Polygon or MultiPolygon based on nesting depth
                                if len(geom_obj) > 0 and isinstance(geom_obj[0], list):
                                    if len(geom_obj[0]) > 0 and isinstance(geom_obj[0][0], list):
                                        if len(geom_obj[0][0]) > 0 and isinstance(geom_obj[0][0][0], list):
                                            geom_dict = {"type": "MultiPolygon", "coordinates": geom_obj}
                                        else:
                                            geom_dict = {"type": "Polygon", "coordinates": geom_obj}
                                    else:
                                        geom_dict = {"type": "Polygon", "coordinates": [geom_obj]}
                                else:
                                    continue
                            elif isinstance(geom_obj, dict):
                                geom_dict = geom_obj
                            else:
                                continue

                            poly = shapely_shape(geom_dict)
                            if poly.contains(pt):
                                return {
                                    "district_id": r.district_id,
                                    "id": r.id,
                                    "name": r.name,
                                    "division": r.division,
                                    "is_monitored": r.is_monitored,
                                }
                        except Exception:
                            continue
                # If point is slightly outside boundary vertices, fallback to closest centroid within 35 km
                best_match = None
                min_d = 35.0
                for r in rows:
                    d = haversine_distance(lat, lon, r.centroid_lat, r.centroid_lon)
                    if d < min_d:
                        min_d = d
                        best_match = {
                            "district_id": r.district_id,
                            "id": r.id,
                            "name": r.name,
                            "division": r.division,
                            "is_monitored": r.is_monitored,
                        }
                if best_match:
                    return best_match
            finally:
                session.close()

        return None

    def get_border_districts(self, max_border_distance_km: float = 120.0) -> List[Dict[str, Any]]:
        """
        Queries districts situated within the international transboundary corridor (default: 120 km).
        """
        session = self.session_factory()
        try:
            query = text("""
                SELECT district_id, id, name, division, is_monitored, centroid_lat, centroid_lon, border_distance_km
                FROM spatial_districts
                WHERE border_distance_km <= :max_dist
                ORDER BY border_distance_km ASC;
            """)
            rows = session.execute(query, {"max_dist": max_border_distance_km}).fetchall()
            return [
                {
                    "district_id": r.district_id,
                    "id": r.id,
                    "name": r.name,
                    "division": r.division,
                    "is_monitored": r.is_monitored,
                    "centroid_lat": r.centroid_lat,
                    "centroid_lon": r.centroid_lon,
                    "border_distance_km": r.border_distance_km,
                }
                for r in rows
            ]
        finally:
            session.close()
