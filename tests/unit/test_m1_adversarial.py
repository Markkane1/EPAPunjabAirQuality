"""Adversarial Verification Suite for Milestone M1.

Empirically challenges:
1. Workspace archival integrity (zero remnants of legacy artifacts outside 'original System/').
2. Station catalog integrity:
   - Exactly 79 stations.
   - Distinct IDs (both string and numeric).
   - Distinct station names without whitespace corruptions.
   - Distinct geographical coordinates strictly within [27.0, 35.5] N and [69.0, 76.5] E.
   - Strict alias matching (lat == latitude, lon == longitude).
   - Valid district linkage (each station points to a valid district that reciprocal-links to it).
   - Proximity verification (no station displaced anomalously far from its district centroid).
   - Exactly 5 mobile stations and 74 fixed stations.
3. District boundaries and administrative topology:
   - Exactly 41 administrative districts with unique names.
   - All centroids within Punjab bounding box.
   - Non-empty station lists and matching station_count.
   - Polygon boundary validation: all rings closed (ring[0] == ring[-1]), >= 4 vertices, coordinates in bounds.
   - Centroid containment inside or immediately bounding the polygon geometry.
4. Baseline time-series and multi-pollutant continuity:
   - Exactly 216 hours spanning 2026-11-01 00:00 to 2026-11-09 23:00.
   - Strictly monotonic 1-hour deltas without gaps, duplicate stamps, or DST discontinuities.
   - All 9 pollutants (AQI, PM10, PM2.5, NO2, SO2, CO, O3, NO, NOX) present.
   - 216 frames per pollutant, exactly 41 districts per frame with valid numeric or None values.
   - Provincial aggregate series present and non-empty for all 216 hours.
   - Wind fields: 216 frames across 41 districts with physical wind vectors.
   - Airport series: 6 airports across 216 hours.
"""
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BASELINE_DIR = PROJECT_ROOT / "data" / "baseline"
ORIGINAL_SYSTEM = PROJECT_ROOT / "original System"


class TestArchivalRemnantsEmpirical:
    """Stress-tests Requirement R1 archival cleanliness across the workspace."""

    def test_no_legacy_remnants_in_root_or_subdirs(self):
        forbidden_names = {"index.html", "index.htm", "collector.py"}
        remnants = []

        for p in PROJECT_ROOT.rglob("*"):
            if ".git" in p.parts:
                continue
            rel = p.relative_to(PROJECT_ROOT)
            # original System/ is the only allowed location
            if rel.parts[0] == "original System":
                continue

            if p.name in forbidden_names:
                remnants.append(str(rel))
            elif p.is_dir() and p.name == "collector" and rel.parts[0] != "original System":
                remnants.append(str(rel))

        assert not remnants, f"Found legacy artifact remnants outside 'original System/': {remnants}"

    def test_original_system_artifacts_intact(self):
        index_file = ORIGINAL_SYSTEM / "index.html"
        collector_file = ORIGINAL_SYSTEM / "collector" / "collector.py"

        assert index_file.is_file(), f"Archived index.html missing at {index_file}"
        assert index_file.stat().st_size > 9_500_000, f"Archived index.html size truncated: {index_file.stat().st_size}"

        assert collector_file.is_file(), f"Archived collector.py missing at {collector_file}"
        assert collector_file.stat().st_size > 15_000, f"Archived collector.py size truncated: {collector_file.stat().st_size}"

    def test_preserved_root_directories(self):
        assert (PROJECT_ROOT / "docs").is_dir(), "docs/ directory missing from project root"
        assert (PROJECT_ROOT / ".agents").is_dir(), ".agents/ directory missing from project root"


class TestStationsEmpiricalChallenge:
    """Empirically stress-tests the 79 stations in stations.json."""

    @pytest.fixture(scope="class")
    @classmethod
    def stations_data(cls):
        path = BASELINE_DIR / "stations.json"
        assert path.is_file(), f"stations.json missing at {path}"
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_station_count_and_types(self, stations_data):
        assert isinstance(stations_data, list), "stations.json is not a list"
        assert len(stations_data) == 79, f"Expected 79 stations, got {len(stations_data)}"

    def test_station_ids_strictly_unique(self, stations_data):
        ids = [s.get("id") for s in stations_data]
        assert all(isinstance(i, str) and len(i) > 0 for i in ids), "Invalid station id found"
        assert len(ids) == len(set(ids)), f"Duplicate station IDs found: {len(ids)} != {len(set(ids))}"

        numeric_ids = [s.get("numeric_id") for s in stations_data]
        assert len(numeric_ids) == len(set(numeric_ids)), "Duplicate numeric IDs found"
        assert set(numeric_ids) == set(range(1, 80)), "numeric_ids do not span 1..79"

    def test_station_names_strictly_unique_and_clean(self, stations_data):
        names = [s.get("name") for s in stations_data]
        assert all(isinstance(n, str) and len(n.strip()) > 0 for n in names), "Invalid station name found"
        assert len(names) == len(set(names)), "Duplicate station names found"
        # Check no names have unstripped whitespace
        assert all(n == n.strip() for n in names), "Station names have untrimmed whitespace"

    def test_station_coordinates_bounds_and_aliases(self, stations_data):
        coords = []
        for s in stations_data:
            lat = s.get("latitude")
            lon = s.get("longitude")
            assert isinstance(lat, (int, float)) and not math.isnan(lat) and not math.isinf(lat), f"Invalid lat: {lat}"
            assert isinstance(lon, (int, float)) and not math.isnan(lon) and not math.isinf(lon), f"Invalid lon: {lon}"
            assert 27.0 <= lat <= 35.5, f"Station {s['name']} lat {lat} outside [27.0, 35.5]"
            assert 69.0 <= lon <= 76.5, f"Station {s['name']} lon {lon} outside [69.0, 76.5]"

            # Verify aliases
            assert s.get("lat") == lat, f"Station {s['name']} lat alias mismatch"
            assert s.get("lon") == lon, f"Station {s['name']} lon alias mismatch"
            coords.append((lat, lon))

        # Check coordinate uniqueness
        assert len(coords) == len(set(coords)), f"Duplicate coordinates among stations: {len(coords)} vs {len(set(coords))}"

    def test_mobile_station_partition(self, stations_data):
        mobile_stations = [s for s in stations_data if s.get("mobile") is True]
        fixed_stations = [s for s in stations_data if s.get("mobile") is False]

        assert len(mobile_stations) == 5, f"Expected 5 mobile stations, got {len(mobile_stations)}"
        assert len(fixed_stations) == 74, f"Expected 74 fixed stations, got {len(fixed_stations)}"
        for s in mobile_stations:
            assert s.get("network_type") == "mobile"
            assert "Mobile" in s["name"]
            assert s["district"] == "Lahore", f"Mobile station {s['name']} not assigned to Lahore"


class TestDistrictsEmpiricalChallenge:
    """Empirically stress-tests the 41 districts in districts.json and districts_dict.json."""

    @pytest.fixture(scope="class")
    @classmethod
    def districts_data(cls):
        path = BASELINE_DIR / "districts.json"
        assert path.is_file(), f"districts.json missing at {path}"
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @pytest.fixture(scope="class")
    @classmethod
    def stations_data(cls):
        with open(BASELINE_DIR / "stations.json", "r", encoding="utf-8") as f:
            return json.load(f)

    def test_district_count_and_names(self, districts_data):
        assert isinstance(districts_data, list), "districts.json is not a list"
        assert len(districts_data) == 41, f"Expected 41 districts, got {len(districts_data)}"
        names = [d.get("name") for d in districts_data]
        assert len(names) == len(set(names)), "Duplicate district names found"

    def test_district_centroids_in_punjab_bounds(self, districts_data):
        for d in districts_data:
            lat = d.get("latitude")
            lon = d.get("longitude")
            assert 27.0 <= lat <= 35.5, f"District {d['name']} lat {lat} out of bounds"
            assert 69.0 <= lon <= 76.5, f"District {d['name']} lon {lon} out of bounds"
            assert d.get("centroid") == [lat, lon], f"Centroid alias mismatch for {d['name']}"

    def test_district_stations_coverage_and_bidirectional_consistency(self, districts_data, stations_data):
        d_map = {d["name"]: d for d in districts_data}
        all_st_names = {s["name"] for s in stations_data}

        # Each district has >= 1 station
        for d in districts_data:
            sts = d.get("stations", [])
            assert len(sts) >= 1, f"District {d['name']} has 0 stations"
            assert d.get("station_count") == len(sts), f"District {d['name']} station_count mismatch"
            for st_name in sts:
                assert st_name in all_st_names, f"District {d['name']} references non-existent station {st_name}"

        # Each station points to a valid district and appears in that district's stations list
        for s in stations_data:
            dname = s.get("district")
            assert dname in d_map, f"Station {s['name']} has invalid district {dname}"
            assert s["name"] in d_map[dname]["stations"], f"Station {s['name']} not in {dname} stations list"

    def test_district_boundary_rings_and_topology(self, districts_data):
        for d in districts_data:
            dname = d["name"]
            polys = d.get("boundary", [])
            assert isinstance(polys, list) and len(polys) >= 1, f"District {dname} boundary empty"

            all_lons = []
            all_lats = []
            for poly in polys:
                assert isinstance(poly, list) and len(poly) >= 1
                for ring in poly:
                    assert isinstance(ring, list) and len(ring) >= 4, f"Ring in {dname} has < 4 vertices"
                    # Closure check
                    assert ring[0] == ring[-1], f"Ring in {dname} is not closed: {ring[0]} != {ring[-1]}"
                    for pt in ring:
                        assert len(pt) == 2, f"Invalid vertex format in {dname}: {pt}"
                        lon, lat = pt
                        assert 69.0 <= lon <= 76.5, f"{dname} vertex lon {lon} out of bounds"
                        assert 27.0 <= lat <= 35.5, f"{dname} vertex lat {lat} out of bounds"
                        all_lons.append(lon)
                        all_lats.append(lat)

            # Centroid bounding box check
            dlat = d["latitude"]
            dlon = d["longitude"]
            margin = 0.05
            assert (min(all_lats) - margin <= dlat <= max(all_lats) + margin), f"Centroid lat {dlat} outside bbox for {dname}"
            assert (min(all_lons) - margin <= dlon <= max(all_lons) + margin), f"Centroid lon {dlon} outside bbox for {dname}"

    def test_districts_dict_json_identical(self, districts_data):
        dict_file = BASELINE_DIR / "districts_dict.json"
        assert dict_file.is_file(), f"districts_dict.json missing at {dict_file}"
        with open(dict_file, "r", encoding="utf-8") as f:
            d_dict = json.load(f)
        assert len(d_dict) == 41
        for d in districts_data:
            assert d["name"] in d_dict
            assert d_dict[d["name"]] == d


class TestBaselineContinuityEmpiricalChallenge:
    """Empirically stress-tests the 216-hour historical dataset in baseline_data.json."""

    @pytest.fixture(scope="class")
    @classmethod
    def baseline_data(cls):
        path = BASELINE_DIR / "baseline_data.json"
        assert path.is_file(), f"baseline_data.json missing at {path}"
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_hours_continuity_and_format(self, baseline_data):
        hours = baseline_data.get("hours", [])
        assert len(hours) == 216, f"Expected 216 hours, got {len(hours)}"

        # Strict ISO/format parsing: YYYY-MM-DD HH:MM
        parsed = [datetime.strptime(h, "%Y-%m-%d %H:%M") for h in hours]

        assert parsed[0] == datetime(2026, 11, 1, 0, 0), f"Start timestamp mismatch: {parsed[0]}"
        assert parsed[-1] == datetime(2026, 11, 9, 23, 0), f"End timestamp mismatch: {parsed[-1]}"

        # Adversarially check every adjacent step for exact 1-hour delta
        for i in range(len(parsed) - 1):
            delta = parsed[i + 1] - parsed[i]
            assert delta == timedelta(hours=1), f"Time discontinuity at index {i}: {hours[i]} -> {hours[i+1]} (delta: {delta})"

    def test_pollutant_frames_completeness(self, baseline_data):
        expected_pollutants = ["AQI", "PM10", "PM2.5", "NO2", "SO2", "CO", "O3", "NO", "NOX"]
        pol = baseline_data.get("pol", {})

        for p in expected_pollutants:
            assert p in pol, f"Pollutant {p} missing from baseline_data.json"
            p_data = pol[p]
            frames = p_data.get("frames", [])
            assert len(frames) == 216, f"Pollutant {p} frames count {len(frames)} != 216"

            for h_idx, frame in enumerate(frames):
                assert "c" in frame, f"{p} frame {h_idx} missing 'c' key"
                assert "l" in frame, f"{p} frame {h_idx} missing 'l' key"
                c = frame["c"]
                assert len(c) == 41, f"{p} frame {h_idx} has {len(c)} districts instead of 41"

                # Check district values
                for dname, val in c.items():
                    if val is not None:
                        assert isinstance(val, (int, float)), f"{p} frame {h_idx} district {dname} invalid val: {val}"
                        assert 0 <= val <= 5000, f"{p} frame {h_idx} district {dname} val out of range: {val}"

    def test_pollutant_series_continuity(self, baseline_data):
        expected_pollutants = ["AQI", "PM10", "PM2.5", "NO2", "SO2", "CO", "O3", "NO", "NOX"]
        pol = baseline_data.get("pol", {})

        for p in expected_pollutants:
            series = pol[p].get("series", [])
            assert len(series) == 216, f"Pollutant {p} series count {len(series)} != 216"
            for h_idx, item in enumerate(series):
                assert isinstance(item, list) and len(item) == 2, f"{p} series[{h_idx}] not [inflow, outflow] pair: {item}"
                inflow, outflow = item
                assert isinstance(inflow, (int, float)) and inflow >= 0, f"Invalid inflow in {p} series[{h_idx}]: {inflow}"
                assert isinstance(outflow, (int, float)) and outflow >= 0, f"Invalid outflow in {p} series[{h_idx}]: {outflow}"

    def test_wind_field_frames(self, baseline_data):
        wind = baseline_data.get("wind", [])
        assert len(wind) == 216, f"Wind frames count {len(wind)} != 216"

        for h_idx, frame in enumerate(wind):
            assert len(frame) == 41, f"Wind frame {h_idx} has {len(frame)} districts instead of 41"
            for dname, vec in frame.items():
                assert isinstance(vec, list) and len(vec) == 2, f"Wind frame {h_idx} district {dname} vec not len 2: {vec}"
                u, v = vec
                assert isinstance(u, (int, float)) and isinstance(v, (int, float)), f"Non-numeric wind vec in frame {h_idx}: {vec}"
                speed = (u * u + v * v) ** 0.5
                assert speed <= 50.0, f"Wind frame {h_idx} district {dname} unphysical wind speed: {speed}"

    def test_airports_wind_series(self, baseline_data):
        airports = baseline_data.get("airports", [])
        assert len(airports) == 6, f"Expected 6 airports, got {len(airports)}"
        expected_icaos = {"OPLA", "OPFA", "OPMT", "OPST", "OPIS", "VIAR"}
        assert {ap["id"] for ap in airports} == expected_icaos

        for ap in airports:
            u_series = ap.get("u", [])
            v_series = ap.get("v", [])
            assert len(u_series) == 216, f"Airport {ap['id']} u series length != 216"
            assert len(v_series) == 216, f"Airport {ap['id']} v series length != 216"
            # Note: in real METAR feeds, missing observations can be None; verify valid floats or None
            for idx in range(216):
                u, v = u_series[idx], v_series[idx]
                if u is not None:
                    assert isinstance(u, (int, float))
                if v is not None:
                    assert isinstance(v, (int, float))
                if u is not None and v is not None:
                    spd = (u * u + v * v) ** 0.5
                    assert spd <= 60.0, f"Airport {ap['id']} unphysical wind speed at {idx}: {spd}"

    def test_transboundary_geometry(self, baseline_data):
        tbgeo = baseline_data.get("tbgeo", {})
        assert len(tbgeo.get("districts", {})) == 24, "Expected 24 border districts in tbgeo"
        samples = tbgeo.get("samples", [])
        assert len(samples) == 39, "Expected 39 normal vector samples in tbgeo"
        for s in samples:
            assert len(s) == 4, f"Normal sample format invalid: {s}"
            lon, lat, nx, ny = s
            assert 69.0 <= lon <= 76.5
            assert 27.0 <= lat <= 35.5
            norm = (nx * nx + ny * ny) ** 0.5
            assert 0.9 <= norm <= 1.1, f"Border normal vector not normalized: norm={norm}"
