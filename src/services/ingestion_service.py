"""
IngestionService: User CSV data ingestion, quarantine isolation, and repository synchronization.
"""
from datetime import datetime, timezone
import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from src.domain.entities.models import Station, StationObservation
from src.domain.interfaces.repositories import (
    AnalyticsRepository,
    DistrictRepository,
    ObservationRepository,
    StationRepository,
)
from src.pipelines.csv_adapter import CSVIngestionResult, UserCSVIngestionAdapter
from src.services.dto import IngestionReportDTO, QuarantinedRowDTO


class IngestionService:
    """
    Coordinates ingestion of custom user-uploaded CSV air quality datasets,
    enforcing Pydantic schemas, dead-letter quarantine isolation, and repository synchronization.
    """

    def __init__(
        self,
        observation_repo: Optional[ObservationRepository] = None,
        station_repo: Optional[StationRepository] = None,
        district_repo: Optional[DistrictRepository] = None,
        analytics_repo: Optional[AnalyticsRepository] = None,
        repo: Optional[Any] = None,
        csv_adapter: Optional[UserCSVIngestionAdapter] = None,
    ) -> None:
        self._obs_repo = observation_repo or repo
        self._station_repo = station_repo or repo
        self._district_repo = district_repo or repo
        self._analytics_repo = analytics_repo or repo
        self._adapter = csv_adapter or UserCSVIngestionAdapter()

    def ingest_csv_data(
        self,
        file_source: Union[str, Path, bytes, io.IOBase],
        filename: Optional[str] = None,
        allow_missing_coords: bool = False,
    ) -> IngestionReportDTO:
        """
        Executes complete ingestion pipeline:
        1. Validates and parses raw CSV input via UserCSVIngestionAdapter.
        2. Isolates invalid rows into Dead-Letter Quarantine records.
        3. Dynamically registers newly discovered stations.
        4. Merges single-pollutant rows into composite domain observations.
        5. Persists observations to repository.
        6. Invalidates affected time-slice and spatial surface caches.
        """
        fname = filename or "uploaded_dataset.csv"
        result: CSVIngestionResult = self._adapter.ingest_csv(
            file_source,
            allow_missing_coordinate_columns=allow_missing_coords,
        )

        quarantined_dtos = [
            QuarantinedRowDTO(
                row_number=q.row_number,
                station_id=q.station_id,
                error_type=q.error_type,
                error_message=q.error_message,
                raw_record=q.raw_record,
            )
            for q in result.quarantine_records
        ]

        if result.valid_count == 0:
            status_str = "failed"
            return IngestionReportDTO(
                status=status_str,
                filename=fname,
                total_rows=result.total_rows,
                valid_rows=0,
                valid_count=0,
                quarantine_count=result.quarantine_count,
                quarantined_rows=result.quarantine_count,
                merged_observations_count=0,
                quarantined_records=quarantined_dtos,
                quarantine_records=quarantined_dtos,
                errors=result.errors,
                affected_stations=[],
                affected_districts=[],
                timestamps_ingested=[],
            )

        # Merge rows into consolidated multi-pollutant observations
        merged_obs = result.get_merged_observations()

        affected_stations: Set[str] = set()
        affected_districts: Set[str] = set()
        affected_timestamps: Set[str] = set()

        for obs in merged_obs:
            affected_stations.add(obs.station_name or obs.station_id)
            affected_districts.add(obs.district)
            affected_timestamps.add(obs.timestamp.isoformat())

        # Persist to repository
        if hasattr(self._obs_repo, "add_user_csv_observations"):
            self._obs_repo.add_user_csv_observations(merged_obs)

        # Clear/invalidate caches
        if self._analytics_repo:
            self._analytics_repo.clear_cache()

        status_str = "success" if result.quarantine_count == 0 else "partial_quarantine"

        return IngestionReportDTO(
            status=status_str,
            filename=fname,
            total_rows=result.total_rows,
            valid_rows=result.valid_count,
            valid_count=result.valid_count,
            quarantine_count=result.quarantine_count,
            quarantined_rows=result.quarantine_count,
            merged_observations_count=len(merged_obs),
            quarantined_records=quarantined_dtos,
            quarantine_records=quarantined_dtos,
            errors=result.errors,
            affected_stations=sorted(list(affected_stations)),
            affected_districts=sorted(list(affected_districts)),
            timestamps_ingested=sorted(list(affected_timestamps)),
        )

    def process_csv_upload(
        self,
        file_bytes: bytes,
        filename: str,
        allow_missing_coords: bool = False,
    ) -> IngestionReportDTO:
        """Helper for multipart upload route."""
        return self.ingest_csv_data(
            file_source=file_bytes,
            filename=filename,
            allow_missing_coords=allow_missing_coords,
        )
