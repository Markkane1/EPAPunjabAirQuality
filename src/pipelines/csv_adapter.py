"""
User CSV Ingestion and Validation Adapter.
Parses, schema-validates, and georeferences user-provided air quality datasets.
Implements row-level dead-letter quarantine reporting, canonical coordinate repair,
wind quality control, extreme exceedance tagging, and PEPC AQI normalization.
Adheres to ORIGINAL_REQUEST.md §R2, DATA_PIPELINES_ARCHITECTURE.md §2, and TRANSFORMATION_LOGIC_SPEC.md.
"""
import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
import io
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from pydantic import ValidationError

from src.domain.math.pepc_aqi import pepc_calculate_aqi, pepc_composite_aqi
from src.domain.math.wind import is_anemometer_valid, is_station_blacklisted, polar_to_cartesian_wind
from src.domain.schemas.csv_schema import UserCSVRow
from src.domain.schemas.measurement import NormalizedObservation
from src.pipelines.fallback_engine import (
    CANONICAL_COORDINATES,
    EXCLUDED_STATIONS,
    FallbackTemplateEngine,
)

logger = logging.getLogger(__name__)

PKT = timezone(timedelta(hours=5))
UTC = timezone.utc

REQUIRED_CSV_COLUMNS: Set[str] = {
    "timestamp",
    "station_id",
    "station_name",
    "district",
    "latitude",
    "longitude",
    "pollutant",
    "value",
}


@dataclass
class QuarantineRecord:
    """Record of a failed row in the ingestion dead-letter quarantine."""
    row_number: int
    station_id: Optional[str]
    error_type: str
    error_message: str
    raw_record: Dict[str, Any]


@dataclass
class CSVIngestionResult:
    """Consolidated ingestion summary and output dataset."""
    total_rows: int
    valid_count: int
    quarantine_count: int
    observations: List[NormalizedObservation]
    quarantine_records: List[QuarantineRecord]
    file_errors: List[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.file_errors:
            return "failed"
        if self.quarantine_count == 0 and self.valid_count > 0:
            return "success"
        if self.valid_count > 0 and self.quarantine_count > 0:
            return "partial_quarantine"
        return "failed"

    @property
    def errors(self) -> List[str]:
        """Convenience property returning string descriptions of all errors."""
        errs = list(self.file_errors)
        for q in self.quarantine_records:
            errs.append(f"Row {q.row_number} [{q.station_id}]: {q.error_message}")
        return errs

    def get_merged_observations(self) -> List[NormalizedObservation]:
        """
        Merges single-pollutant rows sharing the same station_id and timestamp
        into consolidated composite observations with composite PEPC AQI.
        """
        grouped: Dict[Tuple[str, datetime], NormalizedObservation] = {}
        for obs in self.observations:
            key = (obs.station_id, obs.timestamp)
            if key not in grouped:
                grouped[key] = obs.model_copy(deep=True)
            else:
                existing = grouped[key]
                if obs.pm25_qc is not None:
                    existing.pm25_qc = obs.pm25_qc
                if obs.pm10_qc is not None:
                    existing.pm10_qc = obs.pm10_qc
                if obs.no2_qc is not None:
                    existing.no2_qc = obs.no2_qc
                if obs.so2_qc is not None:
                    existing.so2_qc = obs.so2_qc
                if obs.co_qc is not None:
                    existing.co_qc = obs.co_qc
                if obs.o3_qc is not None:
                    existing.o3_qc = obs.o3_qc
                if obs.no_qc is not None:
                    existing.no_qc = obs.no_qc
                if obs.nox_qc is not None:
                    existing.nox_qc = obs.nox_qc
                if obs.wind_speed_ms is not None and existing.wind_speed_ms is None:
                    existing.wind_speed_ms = obs.wind_speed_ms
                    existing.wind_direction_deg = obs.wind_direction_deg
                    existing.u_vector_ms = obs.u_vector_ms
                    existing.v_vector_ms = obs.v_vector_ms
                for qf in obs.qc_flags:
                    if qf not in existing.qc_flags:
                        existing.qc_flags.append(qf)

        # Recalculate composite PEPC AQI for merged observations
        merged_list: List[NormalizedObservation] = []
        for obs in grouped.values():
            pm25_aqi = pepc_calculate_aqi("PM2.5", obs.pm25_qc) if obs.pm25_qc is not None else None
            pm10_aqi = pepc_calculate_aqi("PM10", obs.pm10_qc) if obs.pm10_qc is not None else None
            if pm25_aqi is not None or pm10_aqi is not None:
                obs.pepc_aqi = pepc_composite_aqi(pm25_aqi, pm10_aqi)
            merged_list.append(obs)

        return merged_list


class UserCSVIngestionAdapter:
    """
    Adapter for processing user-supplied CSV files into clean domain observations.
    Handles coordinate repair, row-level quarantine, and normalization.
    """

    def __init__(self, fallback_engine: Optional[FallbackTemplateEngine] = None) -> None:
        self.fallback_engine = fallback_engine or FallbackTemplateEngine()

    def ingest_csv(
        self,
        source: Union[str, Path, bytes, io.StringIO, io.BytesIO],
        allow_missing_coordinate_columns: bool = False,
    ) -> CSVIngestionResult:
        """
        Parses and validates a CSV dataset from a file path, string, or byte buffer.
        """
        text_data: str = ""
        if isinstance(source, Path):
            with open(source, "r", encoding="utf-8-sig", errors="replace") as f:
                text_data = f.read()
        elif isinstance(source, str):
            # Check if it's a file path or direct CSV text
            path_candidate = Path(source)
            if "\n" not in source and path_candidate.is_file():
                with open(path_candidate, "r", encoding="utf-8-sig", errors="replace") as f:
                    text_data = f.read()
            else:
                text_data = source
        elif isinstance(source, bytes):
            text_data = source.decode("utf-8-sig", errors="replace")
        elif hasattr(source, "read"):
            content = source.read()
            if isinstance(content, bytes):
                text_data = content.decode("utf-8-sig", errors="replace")
            else:
                text_data = str(content)
        else:
            raise TypeError(f"Unsupported CSV source type: {type(source)}")

        reader = csv.DictReader(io.StringIO(text_data))
        if reader.fieldnames is None:
            return CSVIngestionResult(
                total_rows=0,
                valid_count=0,
                quarantine_count=0,
                observations=[],
                quarantine_records=[],
                file_errors=["CSV file is empty or missing headers."],
            )

        # Normalize header keys
        header_map: Dict[str, str] = {}
        cleaned_headers: Set[str] = set()
        for f in reader.fieldnames:
            if f:
                clean_f = f.strip().lower()
                header_map[clean_f] = f
                cleaned_headers.add(clean_f)

        # Check required columns
        expected_columns = (
            (REQUIRED_CSV_COLUMNS - {"latitude", "longitude"})
            if allow_missing_coordinate_columns
            else REQUIRED_CSV_COLUMNS
        )
        missing_columns = expected_columns - cleaned_headers
        if missing_columns:
            msg = f"Missing mandatory CSV columns: {sorted(list(missing_columns))}"
            logger.error(msg)
            return CSVIngestionResult(
                total_rows=0,
                valid_count=0,
                quarantine_count=0,
                observations=[],
                quarantine_records=[],
                file_errors=[msg],
            )

        total_rows = 0
        valid_observations: List[NormalizedObservation] = []
        quarantine_records: List[QuarantineRecord] = []

        for row_idx, raw_row in enumerate(reader, start=2):  # 1-indexed, line 2 is first data row
            total_rows += 1
            # Normalize dictionary keys
            clean_row: Dict[str, Any] = {}
            for col_clean, col_orig in header_map.items():
                raw_val = raw_row.get(col_orig)
                val = raw_val.strip() if raw_val is not None else ""
                clean_row[col_clean] = val if val != "" else None

            sid = str(clean_row.get("station_id") or "")
            sname = str(clean_row.get("station_name") or "")

            # 1. Check station exclusion rule (e.g. OneNetwork Station 25)
            lower_name = sname.lower()
            lower_id = sid.lower()
            lower_dist = str(clean_row.get("district") or "").lower()
            if any(exc in lower_name or exc in lower_id or exc in lower_dist for exc in EXCLUDED_STATIONS):
                quarantine_records.append(
                    QuarantineRecord(
                        row_number=row_idx,
                        station_id=sid,
                        error_type="STATION_EXCLUDED",
                        error_message=f"Station '{sname}' lacks verifiable physical coordinates and is excluded.",
                        raw_record=raw_row,
                    )
                )
                continue

            # 2. Coordinate resolution & canonical lookup
            lat_val = clean_row.get("latitude")
            lon_val = clean_row.get("longitude")

            # Check if coordinates need repair or registry lookup
            corrected_coords = self._resolve_or_correct_coords(sname, sid, lat_val, lon_val)
            if corrected_coords is None:
                quarantine_records.append(
                    QuarantineRecord(
                        row_number=row_idx,
                        station_id=sid,
                        error_type="COORDINATES_MISSING_OR_UNRESOLVABLE",
                        error_message=f"Latitude and longitude missing or invalid for station '{sname}', and not in registry.",
                        raw_record=raw_row,
                    )
                )
                continue

            clean_row["latitude"] = corrected_coords[0]
            clean_row["longitude"] = corrected_coords[1]

            # 3. Pydantic schema validation
            try:
                row_model = UserCSVRow(
                    timestamp=clean_row["timestamp"],
                    station_id=clean_row["station_id"],
                    station_name=clean_row["station_name"],
                    district=clean_row["district"],
                    latitude=float(clean_row["latitude"]),
                    longitude=float(clean_row["longitude"]),
                    pollutant=clean_row["pollutant"],
                    value=float(clean_row["value"]),
                    wind_speed=float(clean_row["wind_speed"]) if clean_row.get("wind_speed") is not None else None,
                    wind_direction=float(clean_row["wind_direction"]) if clean_row.get("wind_direction") is not None else None,
                    pollutant_flags=clean_row.get("pollutant_flags"),
                )
            except (ValidationError, ValueError, TypeError) as exc:
                quarantine_records.append(
                    QuarantineRecord(
                        row_number=row_idx,
                        station_id=sid,
                        error_type="VALIDATION_ERROR",
                        error_message=str(exc),
                        raw_record=raw_row,
                    )
                )
                continue

            # 4. Domain Normalization & QC
            obs = self._normalize_valid_row(row_model)
            if obs:
                valid_observations.append(obs)
            else:
                quarantine_records.append(
                    QuarantineRecord(
                        row_number=row_idx,
                        station_id=sid,
                        error_type="QC_PURGED",
                        error_message="Value purged by zero/negative quality control check.",
                        raw_record=raw_row,
                    )
                )

        return CSVIngestionResult(
            total_rows=total_rows,
            valid_count=len(valid_observations),
            quarantine_count=len(quarantine_records),
            observations=valid_observations,
            quarantine_records=quarantine_records,
        )

    def _resolve_or_correct_coords(
        self,
        station_name: str,
        station_id: str,
        lat_raw: Any,
        lon_raw: Any,
    ) -> Optional[Tuple[float, float]]:
        """
        Applies canonical lookup table and station registry fallback.
        Corrects corrupt GPS entries (e.g. Sahiwal 0,0 -> 30.6682, 73.1114).
        """
        sname_lower = station_name.strip().lower()

        # Check canonical correction catalog first
        for key, coords in CANONICAL_COORDINATES.items():
            if key in sname_lower:
                return coords

        # Parse raw coordinates if supplied
        if lat_raw is not None and lon_raw is not None:
            try:
                lat = float(lat_raw)
                lon = float(lon_raw)
                # Check for registry 0, 0 error
                if abs(lat) < 0.001 and abs(lon) < 0.001:
                    # Look up in baseline catalog
                    return self.fallback_engine.resolve_station_coords(station_id, station_name)
                # Bounds check
                if 27.0 <= lat <= 35.0 and 69.0 <= lon <= 76.0:
                    return (lat, lon)
                # Out of bounds -> return None to trigger quarantine
                return None
            except (ValueError, TypeError):
                pass

        # Fall back to baseline station catalog
        return self.fallback_engine.resolve_station_coords(station_id, station_name)

    def _normalize_valid_row(self, row: UserCSVRow) -> Optional[NormalizedObservation]:
        """
        Normalizes a validated UserCSVRow into a NormalizedObservation domain model.
        """
        # Step 0 QC: Purge zero and negative values
        val = row.value
        if val <= 0.0 or math.isnan(val) or math.isinf(val):
            return None

        # Parse timestamp to UTC
        dt = self._parse_timestamp(row.timestamp)

        # Wind QC and kinematics
        qc_flags: List[str] = []
        ws = row.wind_speed
        wd = row.wind_direction
        u_vec: Optional[float] = None
        v_vec: Optional[float] = None

        if is_station_blacklisted(row.station_name):
            ws = None
            wd = None
            qc_flags.append("WIND_BLACKLIST_WAZIRABAD")
        elif ws is not None and wd is not None:
            if is_anemometer_valid(ws, wd, row.station_name):
                u_vec, v_vec = polar_to_cartesian_wind(ws, wd)
            else:
                ws = None
                wd = None
                qc_flags.append("ANEMOMETER_BOUNDS_PURGED")

        # Extreme exceedance tagging
        pol = row.pollutant
        if pol == "pm25" and val > 1000.0:
            qc_flags.append("QC_EXCEEDANCE_EXTREME")
        elif pol == "pm10" and val > 1500.0:
            qc_flags.append("QC_EXCEEDANCE_EXTREME")

        # PEPC AQI calculation
        pepc_aqi_val: Optional[int] = None
        if pol == "aqi":
            pepc_aqi_val = int(round(val))
        elif pol in ("pm25", "pm10", "no2", "so2", "co", "o3"):
            pol_key = {
                "pm25": "PM2.5",
                "pm10": "PM10",
                "no2": "NO2",
                "so2": "SO2",
                "co": "CO",
                "o3": "O3",
            }.get(pol, pol.upper())
            pepc_aqi_val = pepc_calculate_aqi(pol_key, val)

        return NormalizedObservation(
            timestamp=dt,
            station_id=row.station_id,
            station_name=row.station_name,
            district=row.district,
            latitude=row.latitude,
            longitude=row.longitude,
            pm25_qc=val if pol == "pm25" else None,
            pm10_qc=val if pol == "pm10" else None,
            no2_qc=val if pol == "no2" else None,
            so2_qc=val if pol == "so2" else None,
            co_qc=val if pol == "co" else None,
            o3_qc=val if pol == "o3" else None,
            no_qc=val if pol == "no" else None,
            nox_qc=val if pol == "nox" else None,
            pepc_aqi=pepc_aqi_val,
            wind_speed_ms=ws,
            wind_direction_deg=wd,
            u_vector_ms=u_vec,
            v_vector_ms=v_vec,
            meteorology_source="user_csv",
            qc_flags=qc_flags,
            is_estimated=False,
        )

    def _parse_timestamp(self, ts_str: str) -> datetime:
        """Parses ISO-8601 or YYYY-MM-DD HH:MM string to UTC datetime."""
        clean = ts_str.strip()
        try:
            if clean.endswith("Z"):
                clean = clean[:-1] + "+00:00"
            dt = datetime.fromisoformat(clean)
            if dt.tzinfo is None:
                # Naive timestamps in Punjab assumed PKT
                dt = dt.replace(tzinfo=PKT)
            return dt.astimezone(UTC)
        except Exception:
            for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M"):
                try:
                    dt = datetime.strptime(clean, fmt)
                    return dt.replace(tzinfo=PKT).astimezone(UTC)
                except ValueError:
                    continue
        # Fallback to current UTC if unparseable
        return datetime.now(UTC)
