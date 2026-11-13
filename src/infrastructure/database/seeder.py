"""
Database Seeder for Punjab Air Quality Relational Core and TimescaleDB Hypertables.
Hydrates PostgreSQL 16 tables from canonical baseline artifacts (data/baseline/).
Ensures persistent data across server restarts.
"""
from datetime import datetime, timezone
import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from sqlalchemy.orm import Session

from src.infrastructure.database.models import (
    DistrictHourlyAggregateModel,
    SpatialDistrictModel,
    SpatialStationModel,
    StationHourlyObservationModel,
)

logger = logging.getLogger("paq.seeder")


class DatabaseSeeder:
    """Seeds relational master tables and TimescaleDB hypertables with baseline data."""

    def __init__(self, session_factory: Any, baseline_dir: Optional[Path] = None) -> None:
        self.session_factory = session_factory
        if baseline_dir is None:
            self.baseline_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "baseline"
        else:
            self.baseline_dir = Path(baseline_dir)

    def is_seeded(self) -> bool:
        """Checks whether the database has already been seeded."""
        session: Session = self.session_factory()
        try:
            d_count = session.query(SpatialDistrictModel).count()
            s_count = session.query(SpatialStationModel).count()
            return d_count > 0 and s_count > 0
        except Exception:
            return False
        finally:
            session.close()

    def seed_all(self, max_hours: Optional[int] = None) -> Dict[str, int]:
        """
        Executes full database hydration from baseline artifacts:
        1. spatial_districts (41 districts)
        2. spatial_stations (79 stations + METAR aerodromes)
        3. station_hourly_observations (216 hours of sensor observations)
        4. district_hourly_aggregates (216 hours of district summaries)
        """
        counts = {
            "districts_seeded": 0,
            "stations_seeded": 0,
            "station_obs_seeded": 0,
            "district_obs_seeded": 0,
        }

        districts_file = self.baseline_dir / "districts.json"
        stations_file = self.baseline_dir / "stations.json"
        airports_file = self.baseline_dir / "airports.json"
        baseline_file = self.baseline_dir / "baseline_data.json"

        if not baseline_file.exists() or not districts_file.exists() or not stations_file.exists():
            logger.warning(f"Baseline files not found in {self.baseline_dir}. Skipping database seed.")
            return counts

        with open(districts_file, "r", encoding="utf-8") as f:
            raw_districts = json.load(f)
        with open(stations_file, "r", encoding="utf-8") as f:
            raw_stations = json.load(f)
        with open(airports_file, "r", encoding="utf-8") as f:
            raw_airports = json.load(f)
        with open(baseline_file, "r", encoding="utf-8") as f:
            raw_baseline = json.load(f)

        tbgeo = raw_baseline.get("tbgeo", {})
        tb_districts_meta = tbgeo.get("districts", {})

        session: Session = self.session_factory()
        try:
            # 1. Seed Districts
            existing_districts = {d.id for d in session.query(SpatialDistrictModel.id).all()}
            district_models = []
            for d in raw_districts:
                did = str(d.get("id", d.get("name"))).strip().lower()
                if did in existing_districts:
                    continue
                dname = d["name"]
                lat = float(d.get("latitude") or d.get("lat") or 0.0)
                lon = float(d.get("longitude") or d.get("lon") or 0.0)
                is_mon = bool(d.get("is_monitored", False))
                tb_info = tb_districts_meta.get(dname, {})
                b_dist = float(tb_info.get("border_km", d.get("border_distance_km", 999.0)))
                inflow_sec = tb_info.get("india_sectors", d.get("india_inflow_sectors", []))
                boundary_data = d.get("boundary") or d.get("polys")

                district_models.append(SpatialDistrictModel(
                    id=did,
                    name=dname,
                    division=d.get("division", dname),
                    is_monitored=is_mon,
                    centroid_lat=lat,
                    centroid_lon=lon,
                    centroid_geom=f"POINT({lon} {lat})",
                    boundary_geom=json.dumps(boundary_data) if boundary_data else None,
                    border_distance_km=b_dist,
                    india_inflow_sectors_json=json.dumps(inflow_sec),
                ))

            if district_models:
                session.add_all(district_models)
                session.commit()
                counts["districts_seeded"] = len(district_models)
                logger.info(f"Seeded {len(district_models)} spatial districts.")

            dist_id_map = {d.name.lower(): d.district_id for d in session.query(SpatialDistrictModel).all()}

            # 2. Seed Stations & Airports
            existing_stations = {s.station_id for s in session.query(SpatialStationModel.station_id).all()}
            station_models = []
            for s in raw_stations:
                sid = str(s.get("id") or s.get("station_id")).strip()
                if sid in existing_stations:
                    continue
                sname = s["name"]
                dname = s.get("district", "Lahore")
                lat = float(s.get("latitude") or s.get("lat") or 0.0)
                lon = float(s.get("longitude") or s.get("lon") or 0.0)
                net_type = s.get("network_type", "fixed")
                qa_sum = s.get("qa_summary", {})
                has_anem = bool(qa_sum.get("wind_valid", 0) > 0)
                is_wazirabad = "wazirabad" in sname.lower()

                station_models.append(SpatialStationModel(
                    station_id=sid,
                    name=sname,
                    district_id=dist_id_map.get(dname.lower()),
                    district=dname,
                    station_type=net_type,
                    latitude=lat,
                    longitude=lon,
                    location_geom=f"POINT({lon} {lat})",
                    has_anemometer=has_anem and not is_wazirabad,
                    anemometer_blacklisted=is_wazirabad,
                    altitude_m=None,
                    is_active=True,
                ))

            for a in raw_airports:
                icao = (a.get("id") or a.get("icao", "")).strip().upper()
                if not icao or icao in existing_stations:
                    continue
                name = a.get("name", icao)
                lat = float(a.get("latitude") or a.get("lat") or 0.0)
                lon = float(a.get("longitude") or a.get("lon") or 0.0)

                station_models.append(SpatialStationModel(
                    station_id=icao,
                    name=name,
                    district_id=None,
                    district=name,
                    station_type="airport_metar",
                    latitude=lat,
                    longitude=lon,
                    location_geom=f"POINT({lon} {lat})",
                    has_anemometer=True,
                    anemometer_blacklisted=False,
                    altitude_m=None,
                    is_active=True,
                ))

            if station_models:
                session.add_all(station_models)
                session.commit()
                counts["stations_seeded"] = len(station_models)
                logger.info(f"Seeded {len(station_models)} monitoring stations and aerodromes.")

            # 3. Seed Observations
            raw_hours = raw_baseline.get("hours", [])
            timestamps = [
                datetime.strptime(h, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                for h in raw_hours
            ]
            if max_hours is not None:
                timestamps = timestamps[:max_hours]

            pol_dict = raw_baseline.get("pol", {})
            wind_frames = raw_baseline.get("wind", [])

            obs_count = session.query(StationHourlyObservationModel).count()
            if obs_count == 0 and timestamps:
                logger.info(f"Seeding historical sensor observations across {len(timestamps)} hours...")
                station_obs_batch = []

                for s in raw_stations:
                    sid = str(s.get("id") or s.get("station_id")).strip()
                    sname = s["name"]
                    dname = s.get("district", "Lahore")

                    for idx, dt in enumerate(timestamps):
                        vals: Dict[str, Optional[float]] = {}
                        for p in ("AQI", "PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "NO", "NOX"):
                            p_stations = pol_dict.get(p, {}).get("stations", {})
                            series = p_stations.get(sname)
                            if series and idx < len(series) and series[idx] is not None:
                                try:
                                    v = float(series[idx])
                                    vals[p] = v if v > 0.0 else None
                                except (ValueError, TypeError):
                                    vals[p] = None
                            else:
                                vals[p] = None

                        u_val, v_val, spd_val, deg_val = None, None, None, None
                        if idx < len(wind_frames) and dname in wind_frames[idx]:
                            uv = wind_frames[idx][dname]
                            if isinstance(uv, (list, tuple)) and len(uv) >= 2:
                                try:
                                    u_val = float(uv[0])
                                    v_val = float(uv[1])
                                    spd_val = round(math.hypot(u_val, v_val), 2)
                                    deg_val = round((math.degrees(math.atan2(-u_val, -v_val)) + 360.0) % 360.0, 1)
                                except Exception:
                                    pass

                        obs_row = {
                            "recorded_at": dt,
                            "station_id": sid,
                            "pm25": vals.get("PM2.5"),
                            "pm10": vals.get("PM10"),
                            "no2": vals.get("NO2"),
                            "so2": vals.get("SO2"),
                            "co": vals.get("CO"),
                            "o3": vals.get("O3"),
                            "no": vals.get("NO"),
                            "nox": vals.get("NOX"),
                            "aqi_pepc": float(vals["AQI"]) if vals.get("AQI") is not None else None,
                            "wind_speed_ms": spd_val,
                            "wind_direction_deg": deg_val,
                            "u_ms": u_val,
                            "v_ms": v_val,
                            "temp_c": 22.0,
                            "rh_pct": 55.0,
                            "qc_flags": 0,
                        }
                        station_obs_batch.append(obs_row)

                        if len(station_obs_batch) >= 2000:
                            session.bulk_insert_mappings(StationHourlyObservationModel, station_obs_batch)
                            session.commit()
                            counts["station_obs_seeded"] += len(station_obs_batch)
                            station_obs_batch.clear()

                if station_obs_batch:
                    session.bulk_insert_mappings(StationHourlyObservationModel, station_obs_batch)
                    session.commit()
                    counts["station_obs_seeded"] += len(station_obs_batch)
                    station_obs_batch.clear()

                logger.info(f"Seeded {counts['station_obs_seeded']} station hourly observations.")

            # 4. Seed District Hourly Aggregates (41 districts across 216 hours)
            existing_dist_obs_count = session.query(DistrictHourlyAggregateModel).count()
            if existing_dist_obs_count < 1000:
                if existing_dist_obs_count > 0:
                    session.query(DistrictHourlyAggregateModel).delete()
                    session.commit()
                logger.info("Seeding district hourly aggregates...")
                district_obs_batch = []

                for d in raw_districts:
                    dname = d["name"]
                    is_mon = bool(d.get("is_monitored", False))

                    for idx, dt in enumerate(timestamps):
                        vals = {}
                        for p in ("AQI", "PM2.5", "PM10", "NO2", "SO2", "CO", "O3"):
                            frames = pol_dict.get(p, {}).get("frames", [])
                            if idx < len(frames) and "c" in frames[idx]:
                                v = frames[idx]["c"].get(dname)
                                if v is not None:
                                    try:
                                        fv = float(v)
                                        vals[p] = fv if fv > 0.0 else None
                                    except (ValueError, TypeError):
                                        vals[p] = None
                                else:
                                    vals[p] = None
                            else:
                                vals[p] = None

                        u_val, v_val, spd_val, deg_val = 0.0, 0.0, 0.0, 0.0
                        if idx < len(wind_frames) and dname in wind_frames[idx]:
                            uv = wind_frames[idx][dname]
                            if isinstance(uv, (list, tuple)) and len(uv) >= 2:
                                try:
                                    u_val = float(uv[0])
                                    v_val = float(uv[1])
                                    spd_val = round(math.hypot(u_val, v_val), 2)
                                    deg_val = round((math.degrees(math.atan2(-u_val, -v_val)) + 360.0) % 360.0, 1)
                                except Exception:
                                    pass

                        dist_row = {
                            "recorded_at": dt,
                            "district_id": dname,
                            "district_name": dname,
                            "pm25": vals.get("PM2.5"),
                            "pm10": vals.get("PM10"),
                            "no2": vals.get("NO2"),
                            "so2": vals.get("SO2"),
                            "co": vals.get("CO"),
                            "o3": vals.get("O3"),
                            "no": None,
                            "nox": None,
                            "aqi_pepc": float(vals["AQI"]) if vals.get("AQI") is not None else None,
                            "u_ms": u_val,
                            "v_ms": v_val,
                            "wind_speed_ms": spd_val,
                            "wind_direction_deg": deg_val,
                            "is_estimated": not is_mon,
                            "reporting_stations_count": 1 if is_mon else 0,
                        }
                        district_obs_batch.append(dist_row)

                        if len(district_obs_batch) >= 2000:
                            session.bulk_insert_mappings(DistrictHourlyAggregateModel, district_obs_batch)
                            session.commit()
                            counts["district_obs_seeded"] += len(district_obs_batch)
                            district_obs_batch.clear()

                if district_obs_batch:
                    session.bulk_insert_mappings(DistrictHourlyAggregateModel, district_obs_batch)
                    session.commit()
                    counts["district_obs_seeded"] += len(district_obs_batch)
                    district_obs_batch.clear()

                logger.info(f"Seeded {counts['district_obs_seeded']} district hourly aggregates.")

            return counts


        except Exception as e:
            session.rollback()
            logger.error(f"Error seeding database: {e}")
            raise
        finally:
            session.close()
