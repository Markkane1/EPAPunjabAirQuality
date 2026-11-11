"""Automated verification test suite for Milestone M1.

Verifies:
1. Workspace archival: index.html and collector/ relocated under 'original System/',
   docs/ and .agents/ preserved at project root, legacy files purged from root.
2. Legacy collector script syntax integrity.
3. Baseline extraction:
   - stations.json: exactly 79 stations across 41 districts with valid coordinates.
   - districts.json: exactly 41 districts with centroids, monitoring flags, and polygon boundaries.
   - airports.json: exactly 6 airports with coordinates and 216-hour wind vectors.
   - baseline_data.json: complete 216-hour historical dataset with all 9 pollutants and wind fields.
"""
import json
import py_compile
from pathlib import Path
import pytest

# Determine project root relative to this test file
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestWorkspaceArchival:
    """Verifies Requirement R1: Archival of legacy artifacts."""

    def test_original_system_directory_exists(self):
        orig_sys = PROJECT_ROOT / "original System"
        assert orig_sys.is_dir(), f"'original System' directory missing at {orig_sys}"

    def test_index_html_relocated(self):
        archived_index = PROJECT_ROOT / "original System" / "index.html"
        assert archived_index.is_file(), f"Archived index.html missing at {archived_index}"
        assert archived_index.stat().st_size > 9_000_000, "Archived index.html appears incomplete or empty"

        root_index = PROJECT_ROOT / "index.html"
        assert not root_index.exists(), f"Legacy index.html still present in project root: {root_index}"

    def test_collector_relocated(self):
        archived_collector = PROJECT_ROOT / "original System" / "collector"
        assert archived_collector.is_dir(), f"Archived collector dir missing at {archived_collector}"

        collector_script = archived_collector / "collector.py"
        assert collector_script.is_file(), f"collector.py missing at {collector_script}"
        assert collector_script.stat().st_size > 10_000, "collector.py appears incomplete"

        root_collector = PROJECT_ROOT / "collector"
        assert not root_collector.exists(), f"Legacy collector/ still present in project root: {root_collector}"

    def test_docs_and_agents_preserved_at_root(self):
        docs_dir = PROJECT_ROOT / "docs"
        assert docs_dir.is_dir(), f"docs/ missing from root at {docs_dir}"

        expected_docs = [
            "ARCHITECTURE_OVERVIEW.md",
            "DATA_SOURCES_AND_STREAMS.md",
            "TRANSFORMATION_LOGIC_SPEC.md",
            "DATA_PIPELINES_ARCHITECTURE.md",
            "SYSTEM_ARCHITECTURE.md",
            "UI_UX_SPECIFICATION.md",
        ]
        for doc in expected_docs:
            doc_path = docs_dir / doc
            assert doc_path.is_file(), f"Specification doc missing: {doc_path}"
            assert doc_path.stat().st_size > 0, f"Specification doc is empty: {doc_path}"

        agents_dir = PROJECT_ROOT / ".agents"
        assert agents_dir.is_dir(), f".agents/ missing from root at {agents_dir}"

    def test_collector_py_syntax(self):
        collector_script = PROJECT_ROOT / "original System" / "collector" / "collector.py"
        py_compile.compile(str(collector_script), doraise=True)


@pytest.fixture(scope="module")
def baseline_dir():
    bdir = PROJECT_ROOT / "data" / "baseline"
    assert bdir.is_dir(), f"Baseline data directory missing at {bdir}"
    return bdir


class TestBaselineDatasets:
    """Verifies Requirement R2 baseline data extraction into data/baseline/."""

    def test_stations_json(self, baseline_dir):
        stations_file = baseline_dir / "stations.json"
        assert stations_file.is_file(), f"stations.json missing at {stations_file}"

        with open(stations_file, "r", encoding="utf-8") as f:
            stations = json.load(f)

        assert isinstance(stations, list), "stations.json must contain a list of stations"
        assert len(stations) == 79, f"Expected exactly 79 stations, got {len(stations)}"

        # Check unique station names
        names = [s["name"] for s in stations]
        assert len(names) == len(set(names)), "Station names must be unique"

        # Check district coverage (all 41 districts represented)
        districts_in_stations = {s["district"] for s in stations}
        assert len(districts_in_stations) == 41, (
            f"Expected stations across 41 districts, got {len(districts_in_stations)}"
        )

        # Check coordinate bounds (Punjab: lat ~27-35, lon ~69-76)
        for s in stations:
            assert "id" in s and s["id"], f"Station missing id: {s}"
            assert "name" in s and s["name"], f"Station missing name: {s}"
            assert 27.0 <= s["latitude"] <= 35.5, f"Station {s['name']} lat out of bounds: {s['latitude']}"
            assert 69.0 <= s["longitude"] <= 76.5, f"Station {s['name']} lon out of bounds: {s['longitude']}"
            assert s["network_type"] in ("fixed", "mobile"), f"Invalid network type: {s.get('network_type')}"

        # Mobile stations count (5 mobile monitoring units in Lahore)
        mobile_count = sum(1 for s in stations if s["mobile"])
        assert mobile_count == 5, f"Expected 5 mobile monitoring stations, got {mobile_count}"

    def test_districts_json(self, baseline_dir):
        districts_file = baseline_dir / "districts.json"
        assert districts_file.is_file(), f"districts.json missing at {districts_file}"

        with open(districts_file, "r", encoding="utf-8") as f:
            districts = json.load(f)

        assert isinstance(districts, list), "districts.json must contain a list of districts"
        assert len(districts) == 41, f"Expected exactly 41 districts, got {len(districts)}"

        names = [d["name"] for d in districts]
        assert len(names) == len(set(names)), "District names must be unique"

        for d in districts:
            assert "name" in d and d["name"], f"District missing name: {d}"
            assert 27.0 <= d["latitude"] <= 35.5, f"District {d['name']} lat out of bounds: {d['latitude']}"
            assert 69.0 <= d["longitude"] <= 76.5, f"District {d['name']} lon out of bounds: {d['longitude']}"
            assert d["est"] is False, f"Expected est=False in final baseline dataset for {d['name']}"
            assert isinstance(d["stations"], list) and len(d["stations"]) >= 1, (
                f"District {d['name']} has no assigned stations"
            )
            assert isinstance(d["boundary"], list) and len(d["boundary"]) > 0, (
                f"District {d['name']} has empty boundary polygon"
            )

        # Also verify districts_dict.json exists and has 41 keys
        districts_dict_file = baseline_dir / "districts_dict.json"
        assert districts_dict_file.is_file(), f"districts_dict.json missing at {districts_dict_file}"
        with open(districts_dict_file, "r", encoding="utf-8") as f:
            districts_dict = json.load(f)
        assert len(districts_dict) == 41
        assert set(districts_dict.keys()) == set(names)

    def test_airports_json(self, baseline_dir):
        airports_file = baseline_dir / "airports.json"
        assert airports_file.is_file(), f"airports.json missing at {airports_file}"

        with open(airports_file, "r", encoding="utf-8") as f:
            airports = json.load(f)

        assert isinstance(airports, list), "airports.json must contain a list of airports"
        assert len(airports) == 6, f"Expected exactly 6 airports, got {len(airports)}"

        expected_ids = {"OPLA", "OPFA", "OPMT", "OPST", "OPIS", "VIAR"}
        actual_ids = {ap["id"] for ap in airports}
        assert actual_ids == expected_ids, f"Airport IDs mismatch: expected {expected_ids}, got {actual_ids}"

        for ap in airports:
            assert 27.0 <= ap["latitude"] <= 35.5, f"Airport {ap['id']} lat out of bounds"
            assert 69.0 <= ap["longitude"] <= 76.5, f"Airport {ap['id']} lon out of bounds"
            assert len(ap["u"]) == 216, f"Airport {ap['id']} u wind series must have 216 hours"
            assert len(ap["v"]) == 216, f"Airport {ap['id']} v wind series must have 216 hours"

    def test_baseline_data_json(self, baseline_dir):
        baseline_file = baseline_dir / "baseline_data.json"
        assert baseline_file.is_file(), f"baseline_data.json missing at {baseline_file}"

        with open(baseline_file, "r", encoding="utf-8") as f:
            bdata = json.load(f)

        # Verify 216 hours
        hours = bdata.get("hours", [])
        assert len(hours) == 216, f"Expected 216 hourly timestamps, got {len(hours)}"
        assert hours[0] == "2026-11-01 00:00", f"Start timestamp mismatch: {hours[0]}"
        assert hours[-1] == "2026-11-09 23:00", f"End timestamp mismatch: {hours[-1]}"

        # Verify meta
        meta = bdata.get("meta", {})
        assert meta.get("nstations") == 79
        assert meta.get("ndistricts") == 41

        # Verify pollutants (all 9 pollutants present)
        pol = bdata.get("pol", {})
        expected_pol = ["AQI", "PM10", "PM2.5", "NO2", "SO2", "CO", "O3", "NO", "NOX"]
        for p in expected_pol:
            assert p in pol, f"Pollutant {p} missing from baseline_data.json"
            assert len(pol[p]["frames"]) == 216, f"Pollutant {p} frames count != 216"
            assert len(pol[p]["series"]) == 216, f"Pollutant {p} series count != 216"

        # Verify wind
        wind = bdata.get("wind", [])
        assert len(wind) == 216, f"Expected 216 wind frames, got {len(wind)}"
        assert len(wind[0]) == 41, f"Expected 41 districts in wind frame 0, got {len(wind[0])}"

        # Verify transboundary geometry
        tbgeo = bdata.get("tbgeo", {})
        assert len(tbgeo.get("districts", {})) == 24, "Expected 24 border districts in tbgeo"
        assert len(tbgeo.get("samples", [])) == 39, "Expected 39 normal vector samples in tbgeo"
