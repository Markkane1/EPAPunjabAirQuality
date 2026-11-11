"""
Thread-safe, sub-millisecond in-memory repository backed by extracted baseline datasets
(data/baseline/stations.json, districts.json, airports.json, baseline_data.json)
and supporting dynamic additions from user CSV ingestion.
"""
from bisect import bisect_left, bisect_right
from datetime import datetime, timezone
import json
import logging
import math
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

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
from src.domain.math.projection import equirectangular_project, greedy_label_placement
from src.domain.schemas.measurement import NormalizedObservation

logger = logging.getLogger(__name__)


class BaselineStationRepository(StationRepository):
    """Clean LSP-compliant adapter for StationRepository delegating to BaselineRepository store."""

    def __init__(self, store: "BaselineRepository") -> None:
        self._store = store

    def get_by_id(self, station_id: str) -> Optional[Station]:
        return self._store.get_station_by_id(station_id)

    def get_by_name(self, name: str) -> Optional[Station]:
        return self._store.get_station_by_name(name)

    def list_all(self, station_type: Optional[str] = None) -> List[Station]:
        return self._store.list_stations(station_type=station_type)

    def list_by_district(self, district: str) -> List[Station]:
        return self._store.list_by_district(district)

    def list_airports(self) -> List[Station]:
        return self._store.list_airports()

    def exists(self, station_id: str) -> bool:
        return self._store.exists(station_id)

    def count(self) -> int:
        return self._store.count_stations()

    def add_station(self, station: Station) -> None:
        self._store.add_station(station)

    def add_stations(self, stations: Sequence[Station]) -> None:
        self._store.add_stations(stations)


class BaselineDistrictRepository(DistrictRepository):
    """Clean LSP-compliant adapter for DistrictRepository delegating to BaselineRepository store."""

    def __init__(self, store: "BaselineRepository") -> None:
        self._store = store

    def get_by_id(self, district_id: str) -> Optional[District]:
        return self._store.get_district_by_id(district_id)

    def get_by_name(self, name: str) -> Optional[District]:
        return self._store.get_district_by_name(name)

    def list_all(self, monitored_only: bool = False) -> List[District]:
        return self._store.list_all_districts(monitored_only=monitored_only)

    def list_border_districts(self, max_border_distance_km: float = 120.0) -> List[District]:
        return self._store.list_border_districts(max_border_distance_km=max_border_distance_km)

    def count(self) -> int:
        return self._store.count_districts()

    def get_boundary_geometry(self, district_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get_boundary_geometry(district_id)

    def get_label_placement(self, district_id: str) -> Optional[LabelPlacement]:
        return self._store.get_label_placement(district_id)


class BaselineRepository(
    StationRepository,
    DistrictRepository,
    ObservationRepository,
    AnalyticsRepository,
):
    """
    Unified concrete repository implementing Station, District, Observation, and Analytics interfaces.
    Maintains multi-index hash maps for O(1) sub-millisecond retrieval under concurrent access.
    """

    def __init__(self, baseline_dir: Optional[Path] = None) -> None:
        self._lock = threading.RLock()

        if baseline_dir is None:
            self.baseline_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "baseline"
        else:
            self.baseline_dir = Path(baseline_dir)

        # Station storage & indexes
        self._stations: Dict[str, Station] = {}
        self._stations_by_name: Dict[str, Station] = {}
        self._stations_by_district: Dict[str, List[Station]] = {}
        self._airports: Dict[str, Station] = {}

        # District storage & indexes
        self._districts: Dict[str, District] = {}
        self._districts_by_name: Dict[str, District] = {}
        self._district_boundaries: Dict[str, Dict[str, Any]] = {}
        self._border_districts: List[District] = []

        # Observation storage & indexes
        self._station_obs_by_id_and_time: Dict[Tuple[str, datetime], StationObservation] = {}
        self._station_obs_by_time: Dict[datetime, List[StationObservation]] = {}
        self._station_obs_by_station: Dict[str, List[StationObservation]] = {}

        self._district_obs_by_id_and_time: Dict[Tuple[str, datetime], DistrictObservation] = {}
        self._district_obs_by_time: Dict[datetime, List[DistrictObservation]] = {}
        self._district_obs_by_district: Dict[str, List[DistrictObservation]] = {}

        # Airport wind vectors
        self._airport_winds: Dict[str, Dict[datetime, Tuple[Optional[float], Optional[float]]]] = {}

        # Transboundary geometry data
        self._tb_samples: List[List[float]] = []
        self._tb_districts_meta: Dict[str, Dict[str, Any]] = {}

        # Timeline indexes
        self._timeline_timestamps: List[datetime] = []
        self._time_to_index: Dict[datetime, int] = {}
        self._latest_timestamp: Optional[datetime] = None
        self._earliest_timestamp: Optional[datetime] = None

        # Analytics cache
        self._cpf_cache: Dict[Tuple[str, str], CPFRoseResult] = {}
        self._flux_cache: Dict[Tuple[datetime, str], List[AdvectionFluxLink]] = {}
        self._transboundary_cache: Dict[datetime, TransboundaryResult] = {}
        self._surface_cache: Dict[Tuple[datetime, str, int], List[SurfaceGridPoint]] = {}

        # Label placement cache
        self._label_placements: Dict[str, LabelPlacement] = {}

        # LSP-compliant adapter facades
        self._station_repo = BaselineStationRepository(self)
        self._district_repo = BaselineDistrictRepository(self)

        # Load and index baseline
        self._load_baseline()

    @property
    def stations(self) -> BaselineStationRepository:
        return self._station_repo

    @property
    def districts(self) -> BaselineDistrictRepository:
        return self._district_repo

    @property
    def station_repo(self) -> BaselineStationRepository:
        return self._station_repo

    @property
    def district_repo(self) -> BaselineDistrictRepository:
        return self._district_repo

    def _load_baseline(self) -> None:
        """Parse baseline JSON artifacts and construct high-performance indexes."""
        with self._lock:
            stations_file = self.baseline_dir / "stations.json"
            districts_file = self.baseline_dir / "districts.json"
            airports_file = self.baseline_dir / "airports.json"
            baseline_file = self.baseline_dir / "baseline_data.json"

            with open(stations_file, "r", encoding="utf-8") as f:
                raw_stations = json.load(f)
            with open(districts_file, "r", encoding="utf-8") as f:
                raw_districts = json.load(f)
            with open(airports_file, "r", encoding="utf-8") as f:
                raw_airports = json.load(f)
            with open(baseline_file, "r", encoding="utf-8") as f:
                raw_baseline = json.load(f)

            # 1. Parse and index timeline hours
            raw_hours = raw_baseline.get("hours", [])
            self._timeline_timestamps = [
                datetime.strptime(h, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                for h in raw_hours
            ]
            self._timeline_timestamps.sort()
            self._time_to_index = {dt: idx for idx, dt in enumerate(self._timeline_timestamps)}
            if self._timeline_timestamps:
                self._earliest_timestamp = self._timeline_timestamps[0]
                self._latest_timestamp = self._timeline_timestamps[-1]

            # 2. Extract transboundary metadata
            tbgeo = raw_baseline.get("tbgeo", {})
            self._tb_samples = tbgeo.get("samples", [])
            self._tb_districts_meta = tbgeo.get("districts", {})

            # 3. Parse and index districts
            for d in raw_districts:
                did = str(d.get("id", d.get("name")))
                dname = d["name"]
                lat = float(d.get("latitude") or d.get("lat") or 0.0)
                lon = float(d.get("longitude") or d.get("lon") or 0.0)
                is_mon = bool(d.get("is_monitored", False))

                tb_info = self._tb_districts_meta.get(dname, {})
                b_dist = float(tb_info.get("border_km", d.get("border_distance_km", 999.0)))
                inflow_sec = tuple(tb_info.get("india_sectors", d.get("india_inflow_sectors", ())))

                district_entity = District(
                    id=did,
                    name=dname,
                    division=d.get("division", dname),
                    latitude=lat,
                    longitude=lon,
                    is_monitored=is_mon,
                    border_distance_km=b_dist,
                    india_inflow_sectors=inflow_sec,
                )
                self._districts[did] = district_entity
                self._districts[dname] = district_entity
                self._districts_by_name[dname.lower()] = district_entity

                boundary_data = d.get("boundary") or d.get("polys")
                if boundary_data:
                    self._district_boundaries[did] = boundary_data
                    self._district_boundaries[dname] = boundary_data

                if b_dist <= 120.0:
                    self._border_districts.append(district_entity)

            # 3b. Compute collision-free label placements for all districts
            label_requests: List[Dict[str, Any]] = []
            seen_districts: Set[str] = set()

            for d in self._districts.values():
                if d.name in seen_districts:
                    continue
                seen_districts.add(d.name)
                px, py = equirectangular_project(d.latitude, d.longitude)
                label_requests.append({
                    "district_id": str(d.id),
                    "text": d.name,
                    "anchor_x": px,
                    "anchor_y": py,
                    "width": 48.0,
                    "height": 16.0,
                })

            placed = greedy_label_placement(label_requests)
            for item in placed:
                lp = LabelPlacement(
                    district_id=str(item["district_id"]),
                    text=item["text"],
                    anchor_x=item["anchor_x"],
                    anchor_y=item["anchor_y"],
                    offset_x=item["offset_x"],
                    offset_y=item["offset_y"],
                    width=48.0,
                    height=16.0,
                    has_leader_line=item["has_leader_line"],
                )
                self._label_placements[str(lp.district_id)] = lp
                self._label_placements[lp.text] = lp
                self._label_placements[lp.text.lower()] = lp
                self._label_placements[str(lp.district_id).lower()] = lp

            # 4. Parse and index stations
            for s in raw_stations:
                sid = str(s.get("id") or s.get("station_id"))
                sname = s["name"]
                district_name = s.get("district", "Lahore")
                lat = float(s.get("latitude") or s.get("lat") or 0.0)
                lon = float(s.get("longitude") or s.get("lon") or 0.0)
                net_type = s.get("network_type", "fixed")
                qa_sum = s.get("qa_summary", {})
                has_anem = bool(qa_sum.get("wind_valid", 0) > 0)
                is_wazirabad = "wazirabad" in sname.lower()

                station_entity = Station(
                    id=sid,
                    name=sname,
                    district=district_name,
                    latitude=lat,
                    longitude=lon,
                    station_type=net_type,
                    has_anemometer=has_anem and not is_wazirabad,
                    anemometer_blacklisted=is_wazirabad,
                    altitude_m=None,
                    metadata={"numeric_id": s.get("numeric_id"), "coord_source": s.get("coord_source")},
                )
                self._index_station(station_entity)

            # 5. Parse and index airports as specialized stations
            for a in raw_airports:
                icao = a.get("id") or a.get("icao")
                if not icao:
                    continue
                icao = icao.upper()
                name = a.get("name", icao)
                lat = float(a.get("latitude") or a.get("lat") or 0.0)
                lon = float(a.get("longitude") or a.get("lon") or 0.0)

                airport_station = Station(
                    id=icao,
                    name=name,
                    district=name,
                    latitude=lat,
                    longitude=lon,
                    station_type="airport_metar",
                    has_anemometer=True,
                    anemometer_blacklisted=False,
                    altitude_m=None,
                    metadata={"icao": icao},
                )
                self._airports[icao] = airport_station
                self._index_station(airport_station)

                # Store airport winds
                u_list = a.get("u", [])
                v_list = a.get("v", [])
                self._airport_winds[icao] = {}
                for idx, dt in enumerate(self._timeline_timestamps):
                    u_val = u_list[idx] if idx < len(u_list) else None
                    v_val = v_list[idx] if idx < len(v_list) else None
                    self._airport_winds[icao][dt] = (u_val, v_val)

            # 6. Populate observation time series from baseline_data.json
            pol_dict = raw_baseline.get("pol", {})
            wind_frames = raw_baseline.get("wind", [])

            for dt in self._timeline_timestamps:
                self._station_obs_by_time[dt] = []
                self._district_obs_by_time[dt] = []

            # Station hourly observations
            for sid, station in self._stations.items():
                sname = station.name
                district_name = station.district
                obs_list: List[StationObservation] = []

                for idx, dt in enumerate(self._timeline_timestamps):
                    # If this is an airport station, extract airport wind
                    if station.station_type == "airport_metar":
                        aw = self._airport_winds.get(station.id, {}).get(dt, (None, None))
                        u_val, v_val = aw
                        spd_val = round(math.hypot(u_val, v_val), 2) if (u_val is not None and v_val is not None) else None
                        deg_val = (
                            round((math.degrees(math.atan2(-u_val, -v_val)) + 360.0) % 360.0, 1)
                            if (u_val is not None and v_val is not None)
                            else None
                        )
                        st_obs = StationObservation(
                            station_id=sid,
                            recorded_at=dt,
                            wind_speed=spd_val,
                            wind_direction=deg_val,
                            u=u_val,
                            v=v_val,
                        )
                        self._station_obs_by_id_and_time[(sid, dt)] = st_obs
                        self._station_obs_by_time[dt].append(st_obs)
                        obs_list.append(st_obs)
                        continue

                    # Extract pollutant readings
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

                    # Extract wind from district frames
                    u_val, v_val, spd_val, deg_val = None, None, None, None
                    if idx < len(wind_frames) and district_name in wind_frames[idx]:
                        uv = wind_frames[idx][district_name]
                        if isinstance(uv, (list, tuple)) and len(uv) >= 2:
                            u_val = float(uv[0])
                            v_val = float(uv[1])
                            spd_val = round(math.hypot(u_val, v_val), 2)
                            deg_val = round((math.degrees(math.atan2(-u_val, -v_val)) + 360.0) % 360.0, 1)

                    aqi_int = int(round(vals["AQI"])) if vals.get("AQI") is not None else None

                    st_obs = StationObservation(
                        station_id=sid,
                        recorded_at=dt,
                        pm25=vals.get("PM2.5"),
                        pm10=vals.get("PM10"),
                        no2=vals.get("NO2"),
                        so2=vals.get("SO2"),
                        co=vals.get("CO"),
                        o3=vals.get("O3"),
                        no=vals.get("NO"),
                        nox=vals.get("NOX"),
                        aqi=aqi_int,
                        wind_speed=spd_val,
                        wind_direction=deg_val,
                        u=u_val,
                        v=v_val,
                    )
                    self._station_obs_by_id_and_time[(sid, dt)] = st_obs
                    self._station_obs_by_time[dt].append(st_obs)
                    obs_list.append(st_obs)

                obs_list.sort(key=lambda x: x.recorded_at)
                self._station_obs_by_station[sid] = obs_list

            # District hourly observations
            for did, district in self._districts.items():
                dname = district.name
                if did != dname:
                    continue  # Process each unique district once
                dist_obs_list: List[DistrictObservation] = []

                for idx, dt in enumerate(self._timeline_timestamps):
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

                    u_val, v_val, spd_val, deg_val = None, None, None, None
                    if idx < len(wind_frames) and dname in wind_frames[idx]:
                        uv = wind_frames[idx][dname]
                        if isinstance(uv, (list, tuple)) and len(uv) >= 2:
                            u_val = float(uv[0])
                            v_val = float(uv[1])
                            spd_val = round(math.hypot(u_val, v_val), 2)
                            deg_val = round((math.degrees(math.atan2(-u_val, -v_val)) + 360.0) % 360.0, 1)

                    aqi_int = int(round(vals["AQI"])) if vals.get("AQI") is not None else None

                    dist_obs = DistrictObservation(
                        district_id=dname,
                        recorded_at=dt,
                        pm25=vals.get("PM2.5"),
                        pm10=vals.get("PM10"),
                        no2=vals.get("NO2"),
                        so2=vals.get("SO2"),
                        co=vals.get("CO"),
                        o3=vals.get("O3"),
                        aqi=aqi_int,
                        wind_speed=spd_val,
                        wind_direction=deg_val,
                        u=u_val,
                        v=v_val,
                        is_estimated=not district.is_monitored,
                    )
                    self._district_obs_by_id_and_time[(dname, dt)] = dist_obs
                    self._district_obs_by_id_and_time[(district.id, dt)] = dist_obs
                    self._district_obs_by_time[dt].append(dist_obs)
                    dist_obs_list.append(dist_obs)

                dist_obs_list.sort(key=lambda x: x.recorded_at)
                self._district_obs_by_district[dname] = dist_obs_list
                self._district_obs_by_district[district.id] = dist_obs_list

    def _index_station(self, station: Station) -> None:
        """Internal helper to index a station into lookup dictionaries."""
        self._stations[station.id] = station
        self._stations_by_name[station.name.strip().lower()] = station
        d_lower = station.district.strip().lower()
        if d_lower not in self._stations_by_district:
            self._stations_by_district[d_lower] = []
        if station not in self._stations_by_district[d_lower]:
            self._stations_by_district[d_lower].append(station)

    # -------------------------------------------------------------------------
    # Station & District Shared Resolution Implementation
    # -------------------------------------------------------------------------
    def get_by_id(self, item_id: str) -> Optional[Any]:
        with self._lock:
            s = self._stations.get(str(item_id))
            if s is not None:
                return s
            return self._districts.get(str(item_id))

    def get_station_by_id(self, station_id: str) -> Optional[Station]:
        with self._lock:
            return self._stations.get(str(station_id))

    def get_district_by_id(self, district_id: str) -> Optional[District]:
        with self._lock:
            return self._districts.get(str(district_id))

    def get_by_name(self, name: str) -> Optional[Any]:
        with self._lock:
            s = self._stations_by_name.get(name.strip().lower())
            if s is not None:
                return s
            return self._districts_by_name.get(name.strip().lower())

    def get_station_by_name(self, name: str) -> Optional[Station]:
        with self._lock:
            return self._stations_by_name.get(name.strip().lower())

    def get_district_by_name(self, name: str) -> Optional[District]:
        with self._lock:
            return self._districts_by_name.get(name.strip().lower())

    def list_all(
        self,
        station_type: Optional[str] = None,
        monitored_only: Optional[bool] = None,
    ) -> Any:
        with self._lock:
            if monitored_only is not None:
                return self.list_all_districts(monitored_only=monitored_only)
            return self.list_stations(station_type=station_type)

    def list_stations(self, station_type: Optional[str] = None) -> List[Station]:
        with self._lock:
            if station_type is None:
                return list(self._stations.values())
            return [s for s in self._stations.values() if s.station_type == station_type]

    def get_all(self) -> List[Station]:
        return self.list_stations()

    def list_by_district(self, district: str) -> List[Station]:
        with self._lock:
            return list(self._stations_by_district.get(district.strip().lower(), []))

    def list_airports(self) -> List[Station]:
        with self._lock:
            return list(self._airports.values())

    def exists(self, station_id: str) -> bool:
        with self._lock:
            return str(station_id) in self._stations

    def count(self) -> int:
        with self._lock:
            return len(self._stations)

    def count_stations(self) -> int:
        with self._lock:
            return len(self._stations)

    def add_station(self, station: Station) -> None:
        with self._lock:
            self._index_station(station)

    def add_stations(self, stations: Sequence[Station]) -> None:
        with self._lock:
            for s in stations:
                self._index_station(s)

    def add_batch(self, stations: Sequence[Station]) -> None:
        self.add_stations(stations)

    # -------------------------------------------------------------------------
    # District Specific Implementation
    # -------------------------------------------------------------------------
    def list_all_districts(self, monitored_only: bool = False) -> List[District]:
        with self._lock:
            seen: Set[str] = set()
            res: List[District] = []
            for d in self._districts.values():
                if d.name not in seen:
                    seen.add(d.name)
                    if not monitored_only or d.is_monitored:
                        res.append(d)
            return res

    def list_districts(self, monitored_only: bool = False) -> List[District]:
        return self.list_all_districts(monitored_only=monitored_only)

    def list_border_districts(self, max_border_distance_km: float = 120.0) -> List[District]:
        with self._lock:
            return [d for d in self.list_all_districts() if d.border_distance_km <= max_border_distance_km]

    def get_border_districts(self, max_distance_km: float = 120.0) -> List[District]:
        return self.list_border_districts(max_border_distance_km=max_distance_km)

    def count_districts(self) -> int:
        with self._lock:
            return len(self.list_all_districts())

    def district_count(self) -> int:
        return self.count_districts()

    def get_boundary_geometry(self, district_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._district_boundaries.get(str(district_id))

    def get_boundary(self, district_id: str) -> Optional[Dict[str, Any]]:
        return self.get_boundary_geometry(district_id)

    def get_label_placement(self, district_id: str) -> Optional[LabelPlacement]:
        with self._lock:
            key = str(district_id).strip()
            return self._label_placements.get(key) or self._label_placements.get(key.lower())

    def get_border_samples(self) -> List[List[float]]:
        with self._lock:
            return list(self._tb_samples)

    # -------------------------------------------------------------------------
    # ObservationRepository Implementation
    # -------------------------------------------------------------------------
    def get_station_observation(self, station_id: str, timestamp: datetime) -> Optional[StationObservation]:
        with self._lock:
            dt = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
            return self._station_obs_by_id_and_time.get((str(station_id), dt))

    def get_latest_station_observations(self, pollutant: Optional[str] = None) -> List[StationObservation]:
        with self._lock:
            if not self._latest_timestamp:
                return []
            return self.get_station_observations_at_timestamp(self._latest_timestamp, pollutant)

    def get_station_observations_at_timestamp(
        self, timestamp: datetime, pollutant: Optional[str] = None
    ) -> List[StationObservation]:
        with self._lock:
            dt = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
            obs = self._station_obs_by_time.get(dt, [])
            if pollutant is None:
                return list(obs)
            p_attr = pollutant.lower().replace(".", "").replace("-", "")
            filtered = []
            for o in obs:
                val = getattr(o, p_attr, None)
                if val is not None:
                    filtered.append(o)
            return filtered

    def get_station_observations_by_time(
        self, timestamp: datetime, pollutant: Optional[str] = None
    ) -> List[StationObservation]:
        return self.get_station_observations_at_timestamp(timestamp, pollutant)

    def get_station_hourly_series(
        self,
        station_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        pollutant: Optional[str] = None,
    ) -> List[StationObservation]:
        with self._lock:
            series = self._station_obs_by_station.get(str(station_id), [])
            if not series:
                return []
            start = (start_time if start_time.tzinfo else start_time.replace(tzinfo=timezone.utc)) if start_time else None
            end = (end_time if end_time.tzinfo else end_time.replace(tzinfo=timezone.utc)) if end_time else None

            times = [s.recorded_at for s in series]
            i_start = bisect_left(times, start) if start else 0
            i_end = bisect_right(times, end) if end else len(series)
            sliced = series[i_start:i_end]

            if pollutant is None:
                return list(sliced)
            p_attr = pollutant.lower().replace(".", "").replace("-", "")
            return [o for o in sliced if getattr(o, p_attr, None) is not None]

    def get_station_observations_range(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        station_id: Optional[str] = None,
    ) -> List[StationObservation]:
        if station_id:
            return self.get_station_hourly_series(station_id, start_time, end_time)
        with self._lock:
            res: List[StationObservation] = []
            for s in self._stations.values():
                res.extend(self.get_station_hourly_series(s.id, start_time, end_time))
            return res

    def get_station_observations_for_district(
        self,
        district: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[StationObservation]:
        with self._lock:
            stations = self.list_by_district(district)
            results: List[StationObservation] = []
            for s in stations:
                results.extend(self.get_station_hourly_series(s.id, start_time, end_time))
            return results

    def get_district_observation(self, district_id: str, timestamp: datetime) -> Optional[DistrictObservation]:
        with self._lock:
            dt = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
            return self._district_obs_by_id_and_time.get((str(district_id), dt))

    def get_latest_district_observations(self, pollutant: Optional[str] = None) -> List[DistrictObservation]:
        with self._lock:
            if not self._latest_timestamp:
                return []
            return self.get_district_observations_at_timestamp(self._latest_timestamp, pollutant)

    def get_district_observations_at_timestamp(
        self, timestamp: datetime, pollutant: Optional[str] = None
    ) -> List[DistrictObservation]:
        with self._lock:
            dt = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
            obs = self._district_obs_by_time.get(dt, [])
            if pollutant is None:
                return list(obs)
            p_attr = pollutant.lower().replace(".", "").replace("-", "")
            filtered = []
            for o in obs:
                val = getattr(o, p_attr, None)
                if val is not None:
                    filtered.append(o)
            return filtered

    def get_district_observations_by_time(
        self, timestamp: datetime, pollutant: Optional[str] = None
    ) -> List[DistrictObservation]:
        return self.get_district_observations_at_timestamp(timestamp, pollutant)

    def get_district_hourly_series(
        self,
        district_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        pollutant: Optional[str] = None,
    ) -> List[DistrictObservation]:
        with self._lock:
            series = self._district_obs_by_district.get(str(district_id), [])
            if not series:
                return []
            start = (start_time if start_time.tzinfo else start_time.replace(tzinfo=timezone.utc)) if start_time else None
            end = (end_time if end_time.tzinfo else end_time.replace(tzinfo=timezone.utc)) if end_time else None

            times = [s.recorded_at for s in series]
            i_start = bisect_left(times, start) if start else 0
            i_end = bisect_right(times, end) if end else len(series)
            sliced = series[i_start:i_end]

            if pollutant is None:
                return list(sliced)
            p_attr = pollutant.lower().replace(".", "").replace("-", "")
            return [o for o in sliced if getattr(o, p_attr, None) is not None]

    def get_district_observations_range(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        district_id: Optional[str] = None,
    ) -> List[DistrictObservation]:
        if district_id:
            return self.get_district_hourly_series(district_id, start_time, end_time)
        with self._lock:
            seen_names: Set[str] = set()
            res: List[DistrictObservation] = []
            for d in self.list_all():
                if d.name not in seen_names:
                    seen_names.add(d.name)
                    res.extend(self.get_district_hourly_series(d.name, start_time, end_time))
            return res

    def get_available_timestamps(self) -> List[datetime]:
        with self._lock:
            return list(self._timeline_timestamps)

    def get_historical_hours(self) -> List[datetime]:
        return self.get_available_timestamps()

    def get_timeline_timestamps(self) -> List[datetime]:
        return self.get_available_timestamps()

    def get_latest_timestamp(self) -> Optional[datetime]:
        with self._lock:
            return self._latest_timestamp

    def get_earliest_timestamp(self) -> Optional[datetime]:
        with self._lock:
            return self._earliest_timestamp

    def get_timestamp_by_index(self, index: int) -> Optional[datetime]:
        with self._lock:
            total = len(self._timeline_timestamps)
            if total == 0:
                return None
            if index < 0:
                index = total + index
            if 0 <= index < total:
                return self._timeline_timestamps[index]
            return None

    def get_hour_index(self, timestamp: datetime) -> Optional[int]:
        with self._lock:
            dt = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
            return self._time_to_index.get(dt)

    def total_hours(self) -> int:
        with self._lock:
            return len(self._timeline_timestamps)

    def add_station_observation(self, observation: StationObservation) -> None:
        self.add_station_observations([observation])

    def add_station_observations(self, observations: Sequence[StationObservation]) -> None:
        with self._lock:
            new_timestamps: Set[datetime] = set()
            for o in observations:
                # 1. Normalize timestamp to UTC directly on observation entity
                if o.recorded_at.tzinfo is None:
                    try:
                        o.recorded_at = o.recorded_at.replace(tzinfo=timezone.utc)
                    except Exception:
                        from dataclasses import replace
                        o = replace(o, recorded_at=o.recorded_at.replace(tzinfo=timezone.utc))
                else:
                    try:
                        o.recorded_at = o.recorded_at.astimezone(timezone.utc)
                    except Exception:
                        from dataclasses import replace
                        o = replace(o, recorded_at=o.recorded_at.astimezone(timezone.utc))
                dt = o.recorded_at

                key = (o.station_id, dt)
                is_existing = key in self._station_obs_by_id_and_time
                self._station_obs_by_id_and_time[key] = o

                # 2. Update _station_obs_by_time[dt] with deduplication
                if dt not in self._station_obs_by_time:
                    self._station_obs_by_time[dt] = [o]
                    new_timestamps.add(dt)
                else:
                    time_list = self._station_obs_by_time[dt]
                    if is_existing:
                        for idx, existing in enumerate(time_list):
                            if existing.station_id == o.station_id:
                                time_list[idx] = o
                                break
                        else:
                            time_list.append(o)
                    else:
                        time_list.append(o)

                # 3. Update _station_obs_by_station[station_id] maintaining sorted order without duplicates
                if o.station_id not in self._station_obs_by_station:
                    self._station_obs_by_station[o.station_id] = [o]
                else:
                    series = self._station_obs_by_station[o.station_id]
                    idx = bisect_left(
                        series,
                        dt,
                        key=lambda x: x.recorded_at if x.recorded_at.tzinfo else x.recorded_at.replace(tzinfo=timezone.utc),
                    )
                    if (
                        idx < len(series)
                        and (series[idx].recorded_at if series[idx].recorded_at.tzinfo else series[idx].recorded_at.replace(tzinfo=timezone.utc)) == dt
                    ):
                        series[idx] = o
                    else:
                        series.insert(idx, o)

            if new_timestamps:
                self._timeline_timestamps = sorted(list(self._station_obs_by_time.keys()))
                self._time_to_index = {dt: idx for idx, dt in enumerate(self._timeline_timestamps)}
                self._earliest_timestamp = self._timeline_timestamps[0]
                self._latest_timestamp = self._timeline_timestamps[-1]

            self.clear_cache()

    def add_district_observation(self, observation: DistrictObservation) -> None:
        self.add_district_observations([observation])

    def add_district_observations(self, observations: Sequence[DistrictObservation]) -> None:
        with self._lock:
            for o in observations:
                # 1. Normalize timestamp to UTC directly on observation entity
                if o.recorded_at.tzinfo is None:
                    try:
                        o.recorded_at = o.recorded_at.replace(tzinfo=timezone.utc)
                    except Exception:
                        from dataclasses import replace
                        o = replace(o, recorded_at=o.recorded_at.replace(tzinfo=timezone.utc))
                else:
                    try:
                        o.recorded_at = o.recorded_at.astimezone(timezone.utc)
                    except Exception:
                        from dataclasses import replace
                        o = replace(o, recorded_at=o.recorded_at.astimezone(timezone.utc))
                dt = o.recorded_at

                key = (o.district_id, dt)
                is_existing = key in self._district_obs_by_id_and_time
                self._district_obs_by_id_and_time[key] = o

                # 2. Update _district_obs_by_time[dt] with deduplication
                if dt not in self._district_obs_by_time:
                    self._district_obs_by_time[dt] = [o]
                else:
                    time_list = self._district_obs_by_time[dt]
                    if is_existing:
                        for idx, existing in enumerate(time_list):
                            if existing.district_id == o.district_id:
                                time_list[idx] = o
                                break
                        else:
                            time_list.append(o)
                    else:
                        time_list.append(o)

                # 3. Update _district_obs_by_district[district_id] maintaining sorted order without duplicates
                if o.district_id not in self._district_obs_by_district:
                    self._district_obs_by_district[o.district_id] = [o]
                else:
                    series = self._district_obs_by_district[o.district_id]
                    idx = bisect_left(
                        series,
                        dt,
                        key=lambda x: x.recorded_at if x.recorded_at.tzinfo else x.recorded_at.replace(tzinfo=timezone.utc),
                    )
                    if (
                        idx < len(series)
                        and (series[idx].recorded_at if series[idx].recorded_at.tzinfo else series[idx].recorded_at.replace(tzinfo=timezone.utc)) == dt
                    ):
                        series[idx] = o
                    else:
                        series.insert(idx, o)

            self.clear_cache()

    def add_user_csv_observations(self, observations: Sequence[NormalizedObservation]) -> int:
        """
        Dynamically registers user-provided stations and converts normalized CSV observations
        into domain StationObservation entries with thread-safe atomic cache invalidation.
        """
        with self._lock:
            converted_obs: List[StationObservation] = []
            for obs in observations:
                # 1. Register station if not present
                if obs.station_id not in self._stations:
                    st = Station(
                        id=obs.station_id,
                        name=obs.station_name,
                        district=obs.district,
                        latitude=obs.latitude,
                        longitude=obs.longitude,
                        station_type="user_csv",
                        has_anemometer=(obs.wind_speed_ms is not None),
                        anemometer_blacklisted=False,
                        altitude_m=None,
                        metadata={"source": "user_csv"},
                    )
                    self._index_station(st)

                # 2. Convert to domain StationObservation
                st_obs = StationObservation(
                    station_id=obs.station_id,
                    recorded_at=obs.timestamp,
                    pm25=obs.pm25_qc,
                    pm10=obs.pm10_qc,
                    no2=obs.no2_qc,
                    so2=obs.so2_qc,
                    co=obs.co_qc,
                    o3=obs.o3_qc,
                    no=obs.no_qc,
                    nox=obs.nox_qc,
                    aqi=obs.pepc_aqi,
                    wind_speed=obs.wind_speed_ms,
                    wind_direction=obs.wind_direction_deg,
                    u=obs.u_vector_ms,
                    v=obs.v_vector_ms,
                    qc_flags=len(obs.qc_flags),
                )
                converted_obs.append(st_obs)

            self.add_station_observations(converted_obs)
            return len(converted_obs)

    # -------------------------------------------------------------------------
    # AnalyticsRepository Implementation
    # -------------------------------------------------------------------------
    def get_cpf_rose(self, district_id: str, pollutant: str) -> Optional[CPFRoseResult]:
        with self._lock:
            return self._cpf_cache.get((district_id.strip(), pollutant.upper()))

    def save_cpf_rose(self, result: CPFRoseResult) -> None:
        with self._lock:
            self._cpf_cache[(result.district_id.strip(), result.pollutant.upper())] = result

    def get_advection_flux(self, timestamp: datetime, pollutant: str) -> Optional[List[AdvectionFluxLink]]:
        with self._lock:
            dt = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
            return self._flux_cache.get((dt, pollutant.upper()))

    def save_advection_flux(
        self, timestamp: datetime, pollutant: str, links: Sequence[AdvectionFluxLink]
    ) -> None:
        with self._lock:
            dt = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
            self._flux_cache[(dt, pollutant.upper())] = list(links)

    def get_transboundary_result(self, timestamp: datetime) -> Optional[TransboundaryResult]:
        with self._lock:
            dt = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
            return self._transboundary_cache.get(dt)

    def save_transboundary_result(self, result: TransboundaryResult) -> None:
        with self._lock:
            dt = result.timestamp if result.timestamp.tzinfo else result.timestamp.replace(tzinfo=timezone.utc)
            self._transboundary_cache[dt] = result

    def get_surface_grid(
        self, timestamp: datetime, pollutant: str, resolution: int
    ) -> Optional[List[SurfaceGridPoint]]:
        with self._lock:
            dt = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
            return self._surface_cache.get((dt, pollutant.upper(), resolution))

    def save_surface_grid(
        self, timestamp: datetime, pollutant: str, resolution: int, grid: Sequence[SurfaceGridPoint]
    ) -> None:
        with self._lock:
            dt = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
            self._surface_cache[(dt, pollutant.upper(), resolution)] = list(grid)

    def clear_cache(self) -> None:
        with self._lock:
            self._cpf_cache.clear()
            self._flux_cache.clear()
            self._transboundary_cache.clear()
            self._surface_cache.clear()

    def invalidate_caches(self, timestamps: Optional[List[datetime]] = None) -> None:
        self.clear_cache()
