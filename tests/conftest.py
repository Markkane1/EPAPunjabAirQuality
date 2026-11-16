"""
Session cleanup for leaked CSV stations and post-baseline rows.

E2E ingestion persists user_csv stations in PostgreSQL. The integration
suite expects the statutory station catalog (85 rows). This file lives
under tests/ so the repository root stays free of pytest hooks.
"""
from datetime import datetime, timezone

import pytest

BASELINE_CUTOFF = datetime(2026, 11, 10, 14, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="session", autouse=True)
def clean_db_session_start():
    """Purge stale user_csv and future test rows before and after the session."""
    _purge_test_db_artifacts()
    yield
    _purge_test_db_artifacts()


@pytest.fixture(autouse=True)
def cleanup_test_artifacts_per_test():
    """Drop dynamic test rows after each test so later cases see the catalog."""
    yield
    _purge_test_db_artifacts()


def _purge_test_db_artifacts():
    """Remove user_csv stations and any observations after the baseline cutoff."""
    try:
        from src.infrastructure.database.connection import DatabaseManager
        from src.infrastructure.database.models import (
            SpatialStationModel,
            StationHourlyObservationModel,
            DistrictHourlyAggregateModel,
        )

        db = DatabaseManager()
        with db.get_session() as s:
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

            s.query(StationHourlyObservationModel).filter(
                StationHourlyObservationModel.recorded_at > BASELINE_CUTOFF
            ).delete(synchronize_session=False)
            s.query(DistrictHourlyAggregateModel).filter(
                DistrictHourlyAggregateModel.recorded_at > BASELINE_CUTOFF
            ).delete(synchronize_session=False)
            s.commit()
    except Exception:
        pass
