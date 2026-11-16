"""
Global pytest configuration and cleanup fixtures for Punjab Air Quality test suite.
Ensures database and cache isolation across unit, integration, and E2E test runs.
"""
from datetime import datetime, timezone
import os
import pytest

BASELINE_CUTOFF = datetime(2026, 11, 10, 14, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="session", autouse=True)
def clean_db_session_start():
    """Purge any stale user_csv and future test rows before and after test session."""
    _purge_test_db_artifacts()
    yield
    _purge_test_db_artifacts()


@pytest.fixture(autouse=True)
def cleanup_test_artifacts_per_test():
    """Ensure dynamic test data does not leak across test cases."""
    yield
    _purge_test_db_artifacts()


def _purge_test_db_artifacts():
    """Removes user_csv stations and any post-baseline test observations from persistent store."""
    try:
        from src.infrastructure.database.connection import DatabaseManager
        from src.infrastructure.database.models import (
            SpatialStationModel,
            StationHourlyObservationModel,
            DistrictHourlyAggregateModel,
        )

        db = DatabaseManager()
        with db.get_session() as s:
            # 1. Purge user_csv stations
            csv_ids = [
                m.station_id
                for m in s.query(SpatialStationModel.station_id)
                .filter(SpatialStationModel.station_type == "user_csv")
                .all()
            ]
            if csv_ids:
                s.query(StationHourlyObservationModel).filter(
                    StationHourlyObservationModel.station_id.in_(csv_ids)
                ).delete(synchronize_session=False)
                s.query(SpatialStationModel).filter(
                    SpatialStationModel.station_type == "user_csv"
                ).delete(synchronize_session=False)

            # 2. Purge any post-baseline timestamps inserted by test cases
            s.query(StationHourlyObservationModel).filter(
                StationHourlyObservationModel.recorded_at > BASELINE_CUTOFF
            ).delete(synchronize_session=False)
            s.query(DistrictHourlyAggregateModel).filter(
                DistrictHourlyAggregateModel.recorded_at > BASELINE_CUTOFF
            ).delete(synchronize_session=False)

            s.commit()
    except Exception:
        # Ignore if database is not configured or in baseline memory mode
        pass
