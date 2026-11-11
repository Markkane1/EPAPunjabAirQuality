"""
FallbackTemplateEngine seeded from baseline datasets in data/baseline/.
Provides schema-conforming fallback station measurements, district observations,
and meteorological vectors when live external feeds fail or operate offline.
Adheres to ORIGINAL_REQUEST.md §R2, DATA_SOURCES_AND_STREAMS.md §5 & §6.
"""
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from src.domain.entities.models import DistrictObservation
from src.domain.schemas.measurement import RawStationMeasurement


CANONICAL_COORDINATES: Dict[str, Tuple[float, float]] = {
    "gulberg iii": (31.5097, 74.3478),
    "dc office sialkot": (32.4945, 74.5372),
    "wazirabad": (32.4428, 74.1197),
    "sahiwal": (30.6682, 73.1114),
    "rajanpur": (29.1044, 70.3297),
    "talagang": (32.9283, 72.4189),
    "khushab": (32.2955, 72.3522),
    "safari park-lhr": (31.3821, 74.2238),
}

EXCLUDED_STATIONS: Set[str] = {
    "onenetwork station 25",
    "onenetwork 25",
    "station 25",
    "onenetwork",
}

# WMO ID to baseline airport or district mapping for SYNOP fallback
WMO_FALLBACK_MAP: Dict[str, Dict[str, Any]] = {
    "41640": {"name": "Lahore PBO", "airport": "OPLA", "district": "Lahore"},
    "41641": {"name": "Lahore Airport", "airport": "OPLA", "district": "Lahore"},
    "41571": {"name": "Islamabad", "airport": "OPIS", "district": "Rawalpindi"},
    "41598": {"name": "Jhelum", "airport": "OPIS", "district": "Jhelum"},
    "41600": {"name": "Sialkot", "airport": "OPST", "district": "Sialkot"},
    "41675": {"name": "Multan", "airport": "OPMT", "district": "Multan"},
    "41700": {"name": "Bahawalpur", "airport": "OPBW", "district": "Bahawalpur"},
}

ALL_12_AERODROMES: Dict[str, Dict[str, Any]] = {
    "OPLA": {"name": "Allama Iqbal International Airport", "lat": 31.522, "lon": 74.404, "base_icao": "OPLA"},
    "OPFA": {"name": "Faisalabad International Airport", "lat": 31.365, "lon": 72.995, "base_icao": "OPFA"},
    "OPMT": {"name": "Multan International Airport", "lat": 30.203, "lon": 71.419, "base_icao": "OPMT"},
    "OPST": {"name": "Sialkot International Airport", "lat": 32.535, "lon": 74.364, "base_icao": "OPST"},
    "OPIS": {"name": "Islamabad International Airport", "lat": 33.565, "lon": 72.852, "base_icao": "OPIS"},
    "OPRN": {"name": "Benazir Bhutto International (PAF Chaklala)", "lat": 33.616, "lon": 73.099, "base_icao": "OPIS"},
    "OPRK": {"name": "Shaikh Zayed International Airport", "lat": 28.384, "lon": 70.280, "base_icao": "OPMT"},
    "OPBW": {"name": "Bahawalpur Airport", "lat": 29.348, "lon": 71.718, "base_icao": "OPMT"},
    "OPDG": {"name": "Dera Ghazi Khan Airport", "lat": 29.961, "lon": 70.486, "base_icao": "OPMT"},
    "OPSR": {"name": "PAF Base Mushaf", "lat": 32.049, "lon": 72.666, "base_icao": "OPFA"},
    "OPMI": {"name": "PAF Base Mianwali", "lat": 32.563, "lon": 71.524, "base_icao": "OPFA"},
    "VIAR": {"name": "Sri Guru Ram Dass Jee Intl Airport", "lat": 31.709, "lon": 74.797, "base_icao": "VIAR"},
}


class FallbackTemplateEngine:
    """
    Template engine seeded from extracted historical and spatial artifacts
    (stations.json, districts.json, airports.json, baseline_data.json).
    Guarantees that when external endpoints return 404, 500, or network timeouts,
    schema-conforming data is immediately generated with is_estimated = True.
    """

    def __init__(self, baseline_dir: Optional[Union[str, Path]] = None) -> None:
        if baseline_dir is None:
            # Resolve relative to project root
            base_path = Path(__file__).resolve().parent.parent.parent / "data" / "baseline"
        else:
            base_path = Path(baseline_dir)

        self.baseline_dir = base_path
        self._load_datasets()

    def _load_datasets(self) -> None:
        """Load and index baseline JSON files."""
        stations_path = self.baseline_dir / "stations.json"
        districts_path = self.baseline_dir / "districts.json"
        districts_dict_path = self.baseline_dir / "districts_dict.json"
        airports_path = self.baseline_dir / "airports.json"
        baseline_path = self.baseline_dir / "baseline_data.json"

        with open(stations_path, "r", encoding="utf-8") as f:
            self._stations: List[Dict[str, Any]] = json.load(f)

        with open(districts_path, "r", encoding="utf-8") as f:
            self._districts: List[Dict[str, Any]] = json.load(f)

        if districts_dict_path.is_file():
            with open(districts_dict_path, "r", encoding="utf-8") as f:
                self._districts_dict: Dict[str, Any] = json.load(f)
        else:
            self._districts_dict = {d["name"]: d for d in self._districts}

        with open(airports_path, "r", encoding="utf-8") as f:
            self._airports: List[Dict[str, Any]] = json.load(f)

        with open(baseline_path, "r", encoding="utf-8") as f:
            self._baseline_data: Dict[str, Any] = json.load(f)

        # Index stations by id and by normalized name
        self._stations_by_id: Dict[str, Dict[str, Any]] = {}
        self._stations_by_name: Dict[str, Dict[str, Any]] = {}
        for s in self._stations:
            sid = str(s.get("id") or s.get("station_id") or "")
            if sid:
                self._stations_by_id[sid] = s
            sname = str(s.get("name") or "").strip().lower()
            if sname:
                self._stations_by_name[sname] = s

        # Index airports by icao id
        self._airports_by_id: Dict[str, Dict[str, Any]] = {
            a["id"].upper(): a for a in self._airports if "id" in a
        }

        # Index hours
        self._hours: List[str] = self._baseline_data.get("hours", [])

    @property
    def stations(self) -> List[Dict[str, Any]]:
        return self._stations

    @property
    def districts(self) -> List[Dict[str, Any]]:
        return self._districts

    @property
    def districts_dict(self) -> Dict[str, Any]:
        return self._districts_dict

    @property
    def airports(self) -> List[Dict[str, Any]]:
        return self._airports

    @property
    def hours(self) -> List[str]:
        return self._hours

    def resolve_station_coords(
        self, station_id: Optional[str], station_name: Optional[str]
    ) -> Optional[Tuple[float, float]]:
        """
        Resolves canonical GIS coordinates using the correction catalog (DATA_SOURCES_AND_STREAMS.md §5).
        Returns None if station is in EXCLUDED_STATIONS (e.g. OneNetwork Station 25).
        """
        sname_clean = (station_name or "").strip().lower()
        sid_clean = (station_id or "").strip().lower()

        # Check exclusion
        for exc in EXCLUDED_STATIONS:
            if exc in sname_clean or exc in sid_clean:
                return None

        # Check canonical correction table
        for key, coords in CANONICAL_COORDINATES.items():
            if key in sname_clean:
                return coords

        # Check baseline stations
        station_meta = self.get_station(station_id or station_name or "")
        if station_meta:
            lat = station_meta.get("latitude") or station_meta.get("lat")
            lon = station_meta.get("longitude") or station_meta.get("lon")
            if lat is not None and lon is not None:
                # Sanity check within Punjab bounds
                if 27.0 <= float(lat) <= 35.0 and 69.0 <= float(lon) <= 76.0:
                    return (float(lat), float(lon))

        return None

    def get_station(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Look up station by ID or by name."""
        if not identifier:
            return None
        ident_str = str(identifier).strip()
        if ident_str in self._stations_by_id:
            return self._stations_by_id[ident_str]
        ident_lower = ident_str.lower()
        if ident_lower in self._stations_by_name:
            return self._stations_by_name[ident_lower]
        for name, s in self._stations_by_name.items():
            if ident_lower in name or name in ident_lower:
                return s
        return None

    def get_district(self, name: str) -> Optional[Dict[str, Any]]:
        """Look up district by name."""
        if not name:
            return None
        return self._districts_dict.get(name.strip())

    def get_airport(self, icao: str) -> Optional[Dict[str, Any]]:
        """Look up airport by 4-letter ICAO code across all 12 regional aerodromes."""
        if not icao:
            return None
        code = icao.strip().upper()
        if code in self._airports_by_id:
            return self._airports_by_id[code]
        if code in ALL_12_AERODROMES:
            meta = ALL_12_AERODROMES[code]
            base_ap = self._airports_by_id.get(meta["base_icao"]) or self._airports[0]
            return {
                "id": code,
                "icao": code,
                "name": meta["name"],
                "latitude": meta["lat"],
                "longitude": meta["lon"],
                "lat": meta["lat"],
                "lon": meta["lon"],
                "u": base_ap.get("u", [0.0] * len(self._hours)),
                "v": base_ap.get("v", [0.0] * len(self._hours)),
            }
        return None

    def _normalize_hour_idx(self, hour_idx: int) -> int:
        """Clamps or wraps hour_idx into [0, 215]."""
        total = len(self._hours)
        if total == 0:
            return 0
        if hour_idx < 0:
            hour_idx = total + hour_idx
        return max(0, min(total - 1, hour_idx))

    def get_station_measurement_fallback(
        self,
        station_identifier: str,
        hour_idx: int = -1,
        timestamp: Optional[datetime] = None,
    ) -> Optional[RawStationMeasurement]:
        """
        Generates a schema-conforming RawStationMeasurement for a station from baseline data.
        Marked with is_estimated = True and qc_flags.
        """
        station = self.get_station(station_identifier)
        if not station:
            return None

        h_idx = self._normalize_hour_idx(hour_idx)
        if timestamp is None:
            ts_str = self._hours[h_idx]
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        else:
            dt = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)

        s_name = station["name"]
        district = station.get("district", "Lahore")

        max_statutory_bounds: Dict[str, float] = {
            "AQI": 2000.0,
            "PM2.5": 5000.0,
            "PM10": 5000.0,
            "NO2": 500.0,
            "SO2": 500.0,
            "CO": 50.0,
            "O3": 400.0,
            "NO": 5000.0,
            "NOX": 5000.0,
        }

        # Extract pollutant readings for this station
        def _get_val(pol_name: str) -> Optional[float]:
            pol_dict = self._baseline_data.get("pol", {}).get(pol_name, {})
            station_series = pol_dict.get("stations", {}).get(s_name)
            raw_v = None
            if station_series and h_idx < len(station_series):
                raw_v = station_series[h_idx]
            elif h_idx < len(pol_dict.get("frames", [])) and "c" in pol_dict["frames"][h_idx]:
                raw_v = pol_dict["frames"][h_idx]["c"].get(district)

            if raw_v is None:
                return None
            try:
                fv = float(raw_v)
                bound = max_statutory_bounds.get(pol_name, 5000.0)
                if fv <= 0.0 or math.isnan(fv) or math.isinf(fv) or fv > bound:
                    return None
                return fv
            except (ValueError, TypeError):
                return None

        # Extract wind from district wind
        wind_speed: Optional[float] = None
        wind_direction: Optional[float] = None
        wind_frames = self._baseline_data.get("wind", [])
        if h_idx < len(wind_frames) and district in wind_frames[h_idx]:
            uv = wind_frames[h_idx][district]
            if isinstance(uv, (list, tuple)) and len(uv) >= 2:
                u, v = float(uv[0]), float(uv[1])
                spd = math.hypot(u, v)
                deg = (math.degrees(math.atan2(-u, -v)) + 360.0) % 360.0
                if spd >= 0.0:
                    wind_speed = round(spd, 2)
                    wind_direction = round(deg, 1)

        sid = station.get("id") or station.get("station_id") or "1"
        try:
            sid_val = int(sid)
        except (ValueError, TypeError):
            sid_val = str(sid)

        return RawStationMeasurement(
            station_id=sid_val,
            station_name=s_name,
            district=district,
            timestamp=dt,
            aqi=_get_val("AQI"),
            pm25=_get_val("PM2.5"),
            pm10=_get_val("PM10"),
            no2=_get_val("NO2"),
            so2=_get_val("SO2"),
            co=_get_val("CO"),
            o3=_get_val("O3"),
            no=_get_val("NO"),
            nox=_get_val("NOX"),
            wind_speed=wind_speed,
            wind_direction=wind_direction,
            pollutant_flags=None,
            qc_flags=["FALLBACK_BASELINE_ESTIMATION"],
            is_estimated=True,
        )

    def get_all_station_measurements_fallback(
        self, hour_idx: int = -1, timestamp: Optional[datetime] = None
    ) -> List[RawStationMeasurement]:
        """Returns schema-conforming fallback measurements for all 79 stations."""
        h_idx = self._normalize_hour_idx(hour_idx)
        results: List[RawStationMeasurement] = []
        for s in self._stations:
            meas = self.get_station_measurement_fallback(
                s["name"], hour_idx=h_idx, timestamp=timestamp
            )
            if meas:
                results.append(meas)
        return results

    def get_district_observation_fallback(
        self,
        district_name: str,
        hour_idx: int = -1,
        timestamp: Optional[datetime] = None,
    ) -> Optional[DistrictObservation]:
        """
        Generates a schema-conforming DistrictObservation from baseline frames.
        Marked with is_estimated = True.
        """
        dmeta = self.get_district(district_name)
        if not dmeta:
            return None

        h_idx = self._normalize_hour_idx(hour_idx)
        if timestamp is None:
            ts_str = self._hours[h_idx]
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        else:
            dt = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)

        def _get_district_pol(pol_name: str) -> Optional[float]:
            pol_dict = self._baseline_data.get("pol", {}).get(pol_name, {})
            frames = pol_dict.get("frames", [])
            if h_idx < len(frames) and "c" in frames[h_idx]:
                val = frames[h_idx]["c"].get(district_name)
                return float(val) if val is not None and val > 0.0 else None
            return None

        # Wind extraction
        u: Optional[float] = None
        v: Optional[float] = None
        wind_speed: Optional[float] = None
        wind_direction: Optional[float] = None
        wind_frames = self._baseline_data.get("wind", [])
        if h_idx < len(wind_frames) and district_name in wind_frames[h_idx]:
            uv = wind_frames[h_idx][district_name]
            if isinstance(uv, (list, tuple)) and len(uv) >= 2:
                u = round(float(uv[0]), 3)
                v = round(float(uv[1]), 3)
                spd = math.hypot(u, v)
                deg = (math.degrees(math.atan2(-u, -v)) + 360.0) % 360.0
                wind_speed = round(spd, 2)
                wind_direction = round(deg, 1)

        aqi_val = _get_district_pol("AQI")
        aqi_int = int(round(aqi_val)) if aqi_val is not None else None

        return DistrictObservation(
            district_id=district_name,
            recorded_at=dt,
            pm25=_get_district_pol("PM2.5"),
            pm10=_get_district_pol("PM10"),
            no2=_get_district_pol("NO2"),
            so2=_get_district_pol("SO2"),
            co=_get_district_pol("CO"),
            o3=_get_district_pol("O3"),
            aqi=aqi_int,
            wind_speed=wind_speed,
            wind_direction=wind_direction,
            u=u,
            v=v,
            is_estimated=True,
        )

    def get_airport_metar_fallback(
        self, icao: str, hour_idx: int = -1
    ) -> Optional[Dict[str, Any]]:
        """
        Generates fallback METAR report from airports.json.
        Converts (u, v) into knots and m/s, marked with is_estimated = True.
        """
        airport = self.get_airport(icao)
        if not airport:
            return None

        h_idx = self._normalize_hour_idx(hour_idx)
        u_series = airport.get("u", [])
        v_series = airport.get("v", [])

        u = float(u_series[h_idx]) if h_idx < len(u_series) else 0.0
        v = float(v_series[h_idx]) if h_idx < len(v_series) else 0.0

        spd_ms = math.hypot(u, v)
        dir_deg = (math.degrees(math.atan2(-u, -v)) + 360.0) % 360.0 if spd_ms > 0.01 else None
        spd_kt = round(spd_ms / 0.514444, 1)

        ts_str = self._hours[h_idx]
        obs_time = datetime.strptime(ts_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).isoformat()

        return {
            "icaoId": icao.upper(),
            "station_id": icao.upper(),
            "name": airport.get("name", icao),
            "obsTime": obs_time,
            "latitude": airport.get("latitude") or airport.get("lat"),
            "longitude": airport.get("longitude") or airport.get("lon"),
            "wdir": round(dir_deg) if dir_deg is not None else None,
            "wspd": spd_kt,
            "wind_speed_ms": round(spd_ms, 2),
            "wind_direction_deg": round(dir_deg, 1) if dir_deg is not None else None,
            "u": round(u, 3),
            "v": round(v, 3),
            "visib": 6.0,  # statute miles standard
            "visibility_m": 9656.0,
            "wxString": "HZ",  # Default seasonal haze
            "rawOb": f"METAR {icao.upper()} 091200Z {int(dir_deg or 0):03d}{int(spd_kt):02d}KT 9999 HZ NSC 22/14 Q1015 NOSIG=",
            "is_estimated": True,
            "source": "baseline_airports",
        }

    def get_open_meteo_fallback(self, hour_idx: int = -1) -> List[Dict[str, Any]]:
        """
        Generates fallback Open-Meteo ECMWF wind forecasts for 41 district centroids.
        Includes calibrated wind vectors with K_R = 0.22686 applied.
        """
        h_idx = self._normalize_hour_idx(hour_idx)
        wind_frames = self._baseline_data.get("wind", [])
        frame = wind_frames[h_idx] if h_idx < len(wind_frames) else {}

        k_r = 0.22686
        results: List[Dict[str, Any]] = []
        for d in self._districts:
            dname = d["name"]
            uv = frame.get(dname, [0.0, 0.0])
            u, v = float(uv[0]), float(uv[1])
            spd = math.hypot(u, v)
            deg = (math.degrees(math.atan2(-u, -v)) + 360.0) % 360.0 if spd > 0.01 else 0.0

            results.append({
                "district": dname,
                "latitude": d.get("latitude") or d.get("lat"),
                "longitude": d.get("longitude") or d.get("lon"),
                "wind_speed_10m": round(spd, 2),
                "wind_direction_10m": round(deg, 1),
                "u_calibrated": round(u * k_r, 4),
                "v_calibrated": round(v * k_r, 4),
                "k_r": k_r,
                "is_estimated": True,
                "source": "baseline_ecmwf",
            })
        return results

    def get_synop_fallback(self, wmo_id: str, hour_idx: int = -1) -> Dict[str, Any]:
        """
        Generates fallback SYNOP observation for WMO station mapped to baseline.
        """
        mapping = WMO_FALLBACK_MAP.get(wmo_id, {"name": f"WMO-{wmo_id}", "airport": "OPLA", "district": "Lahore"})
        airport_fallback = self.get_airport_metar_fallback(mapping["airport"], hour_idx=hour_idx)

        h_idx = self._normalize_hour_idx(hour_idx)
        ts_str = self._hours[h_idx]
        obs_time = datetime.strptime(ts_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).isoformat()

        spd_ms = airport_fallback["wind_speed_ms"] if airport_fallback else 1.5
        dir_deg = airport_fallback["wind_direction_deg"] if airport_fallback else 180.0

        return {
            "wmo_id": str(wmo_id),
            "station_name": mapping["name"],
            "district": mapping["district"],
            "timestamp": obs_time,
            "wind_speed_ms": spd_ms,
            "wind_direction_deg": dir_deg,
            "is_estimated": True,
            "source": "baseline_synop",
        }
