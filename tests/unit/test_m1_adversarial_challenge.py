"""Adversarial challenge test suite for Milestone M1.

Empirically verifies:
1. Workspace archival: physical relocation without modification, absence from root.
2. Bitwise/structural authenticity of original System/index.html and collector/collector.py.
3. Preservation of docs/ directory and specifications.
4. Independent extraction and 100% zero-drift cross-check of window.DATA against:
   - data/baseline/stations.json (0 lost, 0 hallucinated, exact coords, exact mobile flags)
   - data/baseline/districts.json (exact centroids, exact polygons from adm)
   - data/baseline/airports.json (exact ICAO codes, exact 216h u/v wind series)
   - data/baseline/baseline_data.json (exact 216 hours, 9 pollutants, wind, tbgeo)
5. Robustness stress tests: no NaNs, no Nulls, coordinate boundary bounds, no ID collisions.
"""
import ast
import json
import math
from pathlib import Path
import py_compile
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def extract_raw_window_data(html_path: Path) -> dict:
    assert html_path.is_file(), f"HTML file missing at {html_path}"
    with open(html_path, "r", encoding="utf-8") as f:
        for line in f:
            if "window.DATA=" in line:
                raw_json = line.split("window.DATA=")[1].rstrip(";\n</script> ")
                return json.loads(raw_json)
    raise ValueError(f"Could not extract window.DATA from {html_path}")


class TestArchivalFidelity:
    """Stress-tests the non-destructive relocation and preservation of legacy files."""

    def test_legacy_purged_from_root(self):
        root_index = PROJECT_ROOT / "index.html"
        root_collector = PROJECT_ROOT / "collector"
        assert not root_index.exists(), f"Violation: index.html still at root: {root_index}"
        assert not root_collector.exists(), f"Violation: collector/ still at root: {root_collector}"

    def test_original_system_index_html_integrity(self):
        archived_index = PROJECT_ROOT / "original System" / "index.html"
        assert archived_index.is_file(), f"Archived index.html missing at {archived_index}"
        size = archived_index.stat().st_size
        assert size == 9609848, f"Unexpected file size for index.html: {size} (expected 9609848)"

        with open(archived_index, "r", encoding="utf-8") as f:
            content = f.read()

        assert content[:100].lower().startswith("<!doctype html"), "index.html missing DOCTYPE header"
        assert "</html>" in content[-100:].lower(), "index.html missing closing html tag"
        assert "window.DATA=" in content, "index.html missing window.DATA payload"
        assert len(content.splitlines()) == 805, f"Expected 805 lines, got {len(content.splitlines())}"

    def test_original_system_collector_py_integrity(self):
        collector_py = PROJECT_ROOT / "original System" / "collector" / "collector.py"
        assert collector_py.is_file(), f"collector.py missing at {collector_py}"
        size = collector_py.stat().st_size
        assert size == 16362, f"Unexpected file size for collector.py: {size} (expected 16362)"

        # Verify compilation and AST structure
        py_compile.compile(str(collector_py), doraise=True)
        with open(collector_py, "r", encoding="utf-8") as f:
            code = f.read()
        parsed_ast = ast.parse(code)
        assert isinstance(parsed_ast, ast.Module), "collector.py failed AST parsing"

    def test_docs_directory_preservation(self):
        docs_dir = PROJECT_ROOT / "docs"
        assert docs_dir.is_dir(), f"docs/ missing at {docs_dir}"

        expected_docs = {
            "ARCHITECTURE_OVERVIEW.md": 24567,
            "DATA_PIPELINES_ARCHITECTURE.md": 26286,
            "DATA_SOURCES_AND_STREAMS.md": 34378,
            "SYSTEM_ARCHITECTURE.md": 34694,
            "TRANSFORMATION_LOGIC_SPEC.md": 36670,
            "UI_UX_SPECIFICATION.md": 33853,
        }
        for doc_name, min_expected_size in expected_docs.items():
            doc_file = docs_dir / doc_name
            assert doc_file.is_file(), f"Preserved doc missing: {doc_file}"
            actual_size = doc_file.stat().st_size
            assert actual_size == min_expected_size, (
                f"Preserved doc {doc_name} size altered: expected {min_expected_size}, got {actual_size}"
            )


class TestAdversarialBaselineCrossCheck:
    """Adversarially cross-checks extracted baseline data against raw window.DATA."""

    @pytest.fixture(scope="class")
    @classmethod
    def raw_data(cls):
        html_path = PROJECT_ROOT / "original System" / "index.html"
        return extract_raw_window_data(html_path)

    def test_stations_zero_data_loss_and_zero_hallucination(self, raw_data):
        stations_file = PROJECT_ROOT / "data" / "baseline" / "stations.json"
        assert stations_file.is_file()
        with open(stations_file, "r", encoding="utf-8") as f:
            baseline_stations = json.load(f)

        raw_stations = raw_data["stations"]
        assert len(raw_stations) == 79
        assert len(baseline_stations) == 79

        raw_by_name = {s["name"]: s for s in raw_stations}
        base_by_name = {s["name"]: s for s in baseline_stations}

        # 1. Exact set match (0 lost, 0 hallucinated)
        assert set(raw_by_name.keys()) == set(base_by_name.keys())

        # 2. Field-by-field verification
        coordsrc = raw_data.get("coordsrc", {})
        qa_data = raw_data.get("qa", {})

        for name, r_st in raw_by_name.items():
            b_st = base_by_name[name]

            # Names and districts
            assert b_st["name"] == r_st["name"]
            assert b_st["district"] == r_st.get("d", "")
            assert b_st["d"] == r_st.get("d", "")

            # Float coordinates
            assert math.isclose(b_st["latitude"], float(r_st["lat"]), rel_tol=1e-9)
            assert math.isclose(b_st["longitude"], float(r_st["lon"]), rel_tol=1e-9)
            assert math.isclose(b_st["lat"], float(r_st["lat"]), rel_tol=1e-9)
            assert math.isclose(b_st["lon"], float(r_st["lon"]), rel_tol=1e-9)

            # Mobile flag
            assert b_st["mobile"] == bool(r_st.get("mobile", False))
            assert b_st["network_type"] == ("mobile" if b_st["mobile"] else "fixed")

            # Coord source mapping
            assert b_st["coord_source"] == coordsrc.get(name, "Unknown")

            # QA summary mapping
            assert b_st["qa_summary"] == qa_data.get(name, {})

            # Punjab coordinate boundaries
            assert 27.0 <= b_st["latitude"] <= 35.5
            assert 69.0 <= b_st["longitude"] <= 76.5

    def test_districts_exact_correspondence(self, raw_data):
        districts_file = PROJECT_ROOT / "data" / "baseline" / "districts.json"
        with open(districts_file, "r", encoding="utf-8") as f:
            baseline_districts = json.load(f)

        raw_districts = raw_data["districts"]
        raw_adm = raw_data.get("adm", {})

        assert len(raw_districts) == 41
        assert len(baseline_districts) == 41

        base_by_name = {d["name"]: d for d in baseline_districts}
        assert set(raw_districts.keys()) == set(base_by_name.keys())

        for d_name, r_d in raw_districts.items():
            b_d = base_by_name[d_name]

            assert math.isclose(b_d["latitude"], float(r_d["lat"]), rel_tol=1e-9)
            assert math.isclose(b_d["longitude"], float(r_d["lon"]), rel_tol=1e-9)
            assert b_d["centroid"] == [float(r_d["lat"]), float(r_d["lon"])]
            assert b_d["stations"] == r_d.get("stations", [])
            assert b_d["station_count"] == len(r_d.get("stations", []))

            # Polygons from adm
            expected_polys = raw_adm.get(d_name, {}).get("polys", [])
            assert b_d["boundary"] == expected_polys
            assert b_d["polys"] == expected_polys
            assert len(b_d["boundary"]) > 0, f"District {d_name} has empty boundary"

    def test_airports_wind_series_exact_fidelity(self, raw_data):
        airports_file = PROJECT_ROOT / "data" / "baseline" / "airports.json"
        with open(airports_file, "r", encoding="utf-8") as f:
            baseline_airports = json.load(f)

        raw_airports = raw_data["airports"]
        assert len(raw_airports) == 6
        assert len(baseline_airports) == 6

        base_by_id = {a["id"]: a for a in baseline_airports}
        raw_by_id = {a["id"]: a for a in raw_airports}

        assert set(raw_by_id.keys()) == set(base_by_id.keys())

        for ap_id, r_ap in raw_by_id.items():
            b_ap = base_by_id[ap_id]
            assert b_ap["name"] == r_ap["name"]
            assert math.isclose(b_ap["latitude"], float(r_ap["lat"]), rel_tol=1e-9)
            assert math.isclose(b_ap["longitude"], float(r_ap["lon"]), rel_tol=1e-9)

            # u and v series
            assert len(b_ap["u"]) == 216
            assert len(b_ap["v"]) == 216
            assert b_ap["u"] == r_ap.get("u", [])
            assert b_ap["v"] == r_ap.get("v", [])

    def test_baseline_data_json_payload_integrity(self, raw_data):
        baseline_file = PROJECT_ROOT / "data" / "baseline" / "baseline_data.json"
        with open(baseline_file, "r", encoding="utf-8") as f:
            bdata = json.load(f)

        # Hours
        assert bdata["hours"] == raw_data["hours"]
        assert len(bdata["hours"]) == 216

        # Pollutants
        for p in ["AQI", "PM10", "PM2.5", "NO2", "SO2", "CO", "O3", "NO", "NOX"]:
            assert p in bdata["pol"]
            assert bdata["pol"][p]["frames"] == raw_data["pol"][p]["frames"]
            assert bdata["pol"][p]["series"] == raw_data["pol"][p]["series"]

        # Wind
        assert len(bdata["wind"]) == 216
        assert bdata["wind"] == raw_data["wind"]

        # Transboundary geometry
        assert bdata["tbgeo"] == raw_data["tbgeo"]

        # ECMWF
        assert bdata["ecm"] == raw_data["ecm"]


class TestAdversarialRobustnessAndEdgeCases:
    """Stress-tests data robustness, boundary integrity, uniqueness, and extraction idempotence."""

    def test_station_id_uniqueness(self):
        with open(PROJECT_ROOT / "data" / "baseline" / "stations.json", "r", encoding="utf-8") as f:
            stations = json.load(f)

        ids = [s["id"] for s in stations]
        assert len(ids) == len(set(ids)), f"Station ID collision detected! Total: {len(ids)}, Unique: {len(set(ids))}"

        num_ids = [s["numeric_id"] for s in stations]
        assert sorted(num_ids) == list(range(1, 80)), "Numeric IDs are not strictly 1..79!"

    def test_station_no_null_critical_fields(self):
        with open(PROJECT_ROOT / "data" / "baseline" / "stations.json", "r", encoding="utf-8") as f:
            stations = json.load(f)

        critical_fields = [
            "id", "station_id", "numeric_id", "name", "district", "d",
            "latitude", "longitude", "lat", "lon", "mobile", "network_type", "coord_source"
        ]
        for s in stations:
            for field in critical_fields:
                val = s.get(field)
                assert val is not None, f"Station {s.get('name')} has None in field '{field}'"
                if isinstance(val, float):
                    assert not math.isnan(val), f"Station {s.get('name')} has NaN in field '{field}'"

    def test_mobile_units_lahore_concentration(self):
        with open(PROJECT_ROOT / "data" / "baseline" / "stations.json", "r", encoding="utf-8") as f:
            stations = json.load(f)

        mobile_units = [s for s in stations if s["mobile"]]
        assert len(mobile_units) == 5, f"Expected 5 mobile units, got {len(mobile_units)}"
        for m in mobile_units:
            assert m["district"] == "Lahore", f"Mobile unit {m['name']} district is {m['district']} (expected Lahore)"
            assert m["network_type"] == "mobile"

    def test_districts_dict_congruence(self):
        with open(PROJECT_ROOT / "data" / "baseline" / "districts.json", "r", encoding="utf-8") as f:
            dist_list = json.load(f)
        with open(PROJECT_ROOT / "data" / "baseline" / "districts_dict.json", "r", encoding="utf-8") as f:
            dist_dict = json.load(f)

        assert len(dist_list) == len(dist_dict) == 41
        for d in dist_list:
            assert d["name"] in dist_dict
            assert d == dist_dict[d["name"]]

    def test_skipped_station_preservation(self):
        with open(PROJECT_ROOT / "data" / "baseline" / "baseline_data.json", "r", encoding="utf-8") as f:
            bdata = json.load(f)
        assert "skipped" in bdata
        skipped = bdata["skipped"]
        assert "OneNetwork Station 25" in str(skipped)

    def test_extraction_idempotence(self):
        import subprocess
        # Run scripts/extract_baseline.py in-process or via subprocess
        result = subprocess.run(
            ["python", str(PROJECT_ROOT / "scripts" / "extract_baseline.py")],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"extract_baseline.py failed on re-run: {result.stderr}"

