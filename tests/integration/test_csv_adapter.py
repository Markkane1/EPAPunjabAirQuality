"""
Integration test suite for UserCSVIngestionAdapter and CSV schema contracts.
Verifies:
1. Parsing valid CSV datasets (tests/fixtures/valid_station_observations.csv) with 100% validity and zero quarantine.
2. Composite observation merging with multi-pollutant consolidation and PEPC AQI calculation.
3. Detecting missing mandatory header columns (tests/fixtures/invalid_missing_columns.csv).
4. Row-level quarantine of out-of-bounds coordinates, values >5000, invalid wind speeds, and unknown pollutants (tests/fixtures/invalid_out_of_bounds.csv).
5. Non-halting error isolation: malformed rows do not halt ingestion of valid rows.
6. Canonical GIS coordinate correction (e.g. Sahiwal 0,0 -> 30.6682, 73.1114).
7. Wazirabad anemometer blacklist purge and flag enforcement.
8. Extreme episodic crisis peak preservation with QC_EXCEEDANCE_EXTREME tagging.
9. Multiple input types: file Path, text string, BytesIO, StringIO.
"""
import io
from pathlib import Path
import pytest

from src.pipelines.csv_adapter import UserCSVIngestionAdapter

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"


class TestUserCSVIngestionAdapter:
    """Verifies user CSV ingestion engine adhering to Clean Architecture and robust QC."""

    def test_valid_station_observations_fixture(self):
        adapter = UserCSVIngestionAdapter()
        csv_path = FIXTURES_DIR / "valid_station_observations.csv"
        result = adapter.ingest_csv(csv_path)

        assert result.status == "success"
        assert result.total_rows == 15
        assert result.valid_count == 15
        assert result.quarantine_count == 0
        assert len(result.observations) == 15

        # Check normalization of first observation (Town Hall, Lahore, PM2.5)
        first_obs = result.observations[0]
        assert first_obs.station_name == "Town Hall"
        assert first_obs.district == "Lahore"
        assert first_obs.pm25_qc == 185.4
        assert first_obs.wind_speed_ms == 2.5
        assert first_obs.wind_direction_deg == 90.0
        # Wind vector u pointing west for wind from 90 deg (East)
        assert first_obs.u_vector_ms is not None and first_obs.u_vector_ms < 0.0
        assert first_obs.pepc_aqi is not None

    def test_merged_composite_station_observations(self):
        adapter = UserCSVIngestionAdapter()
        csv_path = FIXTURES_DIR / "valid_station_observations.csv"
        result = adapter.ingest_csv(csv_path)

        merged = result.get_merged_observations()
        # 15 rows where PK_LHR_001 has two rows (PM2.5 and PM10) -> exactly 14 merged observations
        assert len(merged) == 14

        # Find PK_LHR_001
        town_hall = next(m for m in merged if m.station_id == "PK_LHR_001")
        assert town_hall.pm25_qc == 185.4
        assert town_hall.pm10_qc == 290.1
        # Composite AQI = max(pepc_aqi(PM2.5=185.4 -> 241), pepc_aqi(PM10=290.1 -> 170)) = 241
        assert town_hall.pepc_aqi == 241

    def test_invalid_missing_columns_reporting(self):
        adapter = UserCSVIngestionAdapter()
        csv_path = FIXTURES_DIR / "invalid_missing_columns.csv"
        result = adapter.ingest_csv(csv_path)

        assert result.status == "failed"
        assert len(result.file_errors) > 0
        assert any("Missing mandatory CSV columns" in err for err in result.file_errors)
        assert result.valid_count == 0

    def test_invalid_out_of_bounds_quarantine(self):
        adapter = UserCSVIngestionAdapter()
        csv_path = FIXTURES_DIR / "invalid_out_of_bounds.csv"
        result = adapter.ingest_csv(csv_path)

        assert result.status == "failed"
        assert result.valid_count == 0
        assert result.quarantine_count == 6
        assert len(result.quarantine_records) == 6

        # Verify specific quarantine reasons for each out-of-bounds row
        q_recs = result.quarantine_records

        # Row 2: PK_OOB_001 (Lat 45.5 out of [27.0, 35.0])
        assert q_recs[0].row_number == 2
        assert q_recs[0].station_id == "PK_OOB_001"
        assert q_recs[0].error_type == "COORDINATES_MISSING_OR_UNRESOLVABLE"

        # Row 3: PK_OOB_002 (Lon 85.2 out of [69.0, 76.0])
        assert q_recs[1].row_number == 3
        assert q_recs[1].station_id == "PK_OOB_002"
        assert q_recs[1].error_type == "COORDINATES_MISSING_OR_UNRESOLVABLE"

        # Row 4: PK_OOB_003 (Value 6500.0 > 5000.0)
        assert q_recs[2].row_number == 4
        assert q_recs[2].station_id == "PK_OOB_003"
        assert "value" in q_recs[2].error_message.lower()

        # Row 5: PK_OOB_004 (Wind speed -5.0 < 0)
        assert q_recs[3].row_number == 5
        assert q_recs[3].station_id == "PK_OOB_004"
        assert "wind_speed" in q_recs[3].error_message.lower()

        # Row 6: PK_OOB_005 (Wind speed 45.0 > 30)
        assert q_recs[4].row_number == 6
        assert q_recs[4].station_id == "PK_OOB_005"
        assert "wind_speed" in q_recs[4].error_message.lower()

        # Row 7: PK_OOB_006 (Invalid pollutant 'toxic_dust')
        assert q_recs[5].row_number == 7
        assert q_recs[5].station_id == "PK_OOB_006"
        assert "pollutant" in q_recs[5].error_message.lower()

    def test_non_halting_error_isolation(self):
        """Valid rows must be processed and returned even when errors exist on other rows."""
        csv_content = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value,wind_speed,wind_direction\n"
            "2026-11-10T12:00:00Z,PK_01,Good Station,Lahore,31.5204,74.3587,pm25,120.0,2.0,90.0\n"
            "2026-11-10T12:00:00Z,PK_02,Bad Pollutant,Lahore,31.5204,74.3587,unobtainium,50.0,2.0,90.0\n"
            "2026-11-10T12:00:00Z,PK_03,Good Station 2,Faisalabad,31.4187,73.0791,pm10,210.0,1.5,180.0\n"
            "2026-11-10T12:00:00Z,PK_04,Excluded Node,OneNetwork Station 25,31.5,74.3,pm25,100.0,2.0,90.0\n"
        )
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(csv_content)

        assert res.status == "partial_quarantine"
        assert res.total_rows == 4
        assert res.valid_count == 2
        assert res.quarantine_count == 2
        assert len(res.observations) == 2
        valid_ids = [obs.station_id for obs in res.observations]
        assert valid_ids == ["PK_01", "PK_03"]

    def test_canonical_coordinate_correction(self):
        """Corrupt GPS registry values (e.g. Sahiwal 0,0) must be canonically repaired."""
        csv_content = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            "2026-11-10T12:00:00Z,PK_SWL_001,Sahiwal,Sahiwal,0.0000,0.0000,pm25,140.0\n"
        )
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(csv_content)

        assert res.status == "success"
        assert res.valid_count == 1
        obs = res.observations[0]
        # Should be corrected to canonical Sahiwal coordinates (30.6682, 73.1114)
        assert abs(obs.latitude - 30.6682) < 0.001
        assert abs(obs.longitude - 73.1114) < 0.001

    def test_wazirabad_vane_blacklist_purged(self):
        """Wazirabad AQMS station winds must be purged due to 140 deg physical vane offset."""
        csv_content = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value,wind_speed,wind_direction\n"
            "2026-11-10T12:00:00Z,PK_WAZ_001,Wazirabad AQMS,Gujranwala,32.4428,74.1197,pm25,150.0,5.0,180.0\n"
        )
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(csv_content)

        assert res.status == "success"
        assert res.valid_count == 1
        obs = res.observations[0]
        assert obs.wind_speed_ms is None
        assert obs.wind_direction_deg is None
        assert "WIND_BLACKLIST_WAZIRABAD" in obs.qc_flags

    def test_extreme_episodic_smog_peak_tagging(self):
        """Concentrations > 1000 for PM2.5 or > 1500 for PM10 must be admitted and tagged QC_EXCEEDANCE_EXTREME."""
        csv_content = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            "2026-11-10T12:00:00Z,PK_CRISIS_01,Lahore Smog Epicenter,Lahore,31.5204,74.3587,pm25,1250.0\n"
            "2026-11-10T12:00:00Z,PK_CRISIS_02,Multan Dust Storm,Multan,30.1984,71.4687,pm10,1850.0\n"
        )
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(csv_content)

        assert res.valid_count == 2
        assert res.observations[0].pm25_qc == 1250.0
        assert "QC_EXCEEDANCE_EXTREME" in res.observations[0].qc_flags
        assert res.observations[1].pm10_qc == 1850.0
        assert "QC_EXCEEDANCE_EXTREME" in res.observations[1].qc_flags

    def test_input_modalities_support(self):
        """Ensures file path, raw string, io.StringIO, and bytes are all supported."""
        raw_text = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            "2026-11-10T12:00:00Z,PK_01,Lahore Station,Lahore,31.5204,74.3587,pm25,120.0\n"
        )
        adapter = UserCSVIngestionAdapter()

        # 1. String
        r1 = adapter.ingest_csv(raw_text)
        assert r1.valid_count == 1

        # 2. io.StringIO
        r2 = adapter.ingest_csv(io.StringIO(raw_text))
        assert r2.valid_count == 1

        # 3. bytes
        r3 = adapter.ingest_csv(raw_text.encode("utf-8"))
        assert r3.valid_count == 1

        # 4. io.BytesIO
        r4 = adapter.ingest_csv(io.BytesIO(raw_text.encode("utf-8")))
        assert r4.valid_count == 1

    def test_allow_missing_coordinate_columns_option(self):
        """Tests ingestion when coordinate columns are missing but station is in baseline registry."""
        raw_text = (
            "timestamp,station_id,station_name,district,pollutant,value\n"
            "2026-11-10T12:00:00Z,24,Safari Park-LHR,Lahore,pm25,120.0\n"
        )
        adapter = UserCSVIngestionAdapter()
        # Default rejects missing coordinate columns
        r_fail = adapter.ingest_csv(raw_text)
        assert r_fail.status == "failed"

        # With allow_missing_coordinate_columns=True, resolves from registry
        r_pass = adapter.ingest_csv(raw_text, allow_missing_coordinate_columns=True)
        assert r_pass.status == "success"
        assert r_pass.valid_count == 1
        obs = r_pass.observations[0]
        assert obs.station_name == "Safari Park-LHR"
        assert obs.latitude > 27.0
        assert obs.longitude > 69.0
