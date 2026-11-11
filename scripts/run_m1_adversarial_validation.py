#!/usr/bin/env python3
"""Adversarial Empirical Challenge Harness for Milestone M1.

Exhaustively verifies:
1. Workspace archival cleanliness (zero remnants outside original System/).
2. 79 Station coordinates, IDs, names, mobile flags, and spatial plausibility.
3. 41 District boundaries, polygon ring closures, vertex bounds, area validity, station linkage.
4. 216 Continuous baseline hours, monotonic step deltas, 9 pollutants, wind fields, airports, transboundary geometry.
5. Bitwise / numeric parity against original System/index.html window.DATA.
"""
import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE_DIR = ROOT / "data" / "baseline"
ORIGINAL_SYSTEM = ROOT / "original System"


def shoelace_area(ring: list[list[float]]) -> float:
    """Calculate signed polygon area in degree coordinates."""
    area = 0.0
    n = len(ring)
    for i in range(n - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        area += (x1 * y2 - x2 * y1)
    return 0.5 * abs(area)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def run_checks():
    report = {
        "verdict": "CONFIRM",
        "passed_checks": [],
        "failed_checks": [],
        "stats": {},
    }

    def check(name: str, cond: bool, err_msg: str):
        if cond:
            report["passed_checks"].append(name)
            print(f"[PASS] {name}")
        else:
            report["failed_checks"].append(f"{name}: {err_msg}")
            report["verdict"] = "CHALLENGE_FAIL"
            print(f"[FAIL] {name}: {err_msg}")

    print("=== STARTING EMPIRICAL CHALLENGE HARNESS FOR M1 ===")

    # ---------------------------------------------------------
    # 1. Archival Remnants
    # ---------------------------------------------------------
    forbidden_names = {"index.html", "index.htm", "collector.py"}
    remnants = []
    for p in ROOT.rglob("*"):
        if ".git" in p.parts:
            continue
        rel = p.relative_to(ROOT)
        if rel.parts[0] == "original System":
            continue
        if p.name in forbidden_names:
            remnants.append(str(rel))
        elif p.is_dir() and p.name == "collector" and rel.parts[0] != "original System":
            remnants.append(str(rel))

    check("1.1 Zero legacy remnants outside 'original System/'", len(remnants) == 0, f"Found {remnants}")
    check("1.2 Archived index.html exists", (ORIGINAL_SYSTEM / "index.html").is_file(), "Missing index.html")
    check("1.3 Archived collector.py exists", (ORIGINAL_SYSTEM / "collector" / "collector.py").is_file(), "Missing collector.py")
    check("1.4 docs/ preserved at root", (ROOT / "docs").is_dir(), "Missing docs/")
    check("1.5 .agents/ preserved at root", (ROOT / ".agents").is_dir(), "Missing .agents/")

    # ---------------------------------------------------------
    # 2. Extract window.DATA from original System/index.html
    # ---------------------------------------------------------
    index_path = ORIGINAL_SYSTEM / "index.html"
    raw_data = None
    with open(index_path, "r", encoding="utf-8") as f:
        for line in f:
            if "window.DATA=" in line:
                raw_json = line.split("window.DATA=")[1].rstrip(";\n</script> ")
                raw_data = json.loads(raw_json)
                break
    check("2.1 window.DATA successfully parsed from index.html", raw_data is not None, "Failed to parse window.DATA")

    # ---------------------------------------------------------
    # 3. 79 Station Coordinates & Catalog
    # ---------------------------------------------------------
    with open(BASELINE_DIR / "stations.json", "r", encoding="utf-8") as f:
        stations = json.load(f)

    check("3.1 Station count is exactly 79", len(stations) == 79, f"Got {len(stations)}")
    check("3.2 Raw window.DATA stations count is 79", len(raw_data.get("stations", [])) == 79, f"Got {len(raw_data.get('stations', []))}")

    # Station IDs
    st_ids = [s["id"] for s in stations]
    check("3.3 All station IDs unique", len(st_ids) == len(set(st_ids)), f"Duplicate IDs in {len(st_ids)} stations")
    numeric_ids = [s["numeric_id"] for s in stations]
    check("3.4 All numeric IDs unique and 1..79", set(numeric_ids) == set(range(1, 80)), f"Numeric IDs mismatch")

    # Station names
    st_names = [s["name"] for s in stations]
    check("3.5 All station names unique", len(st_names) == len(set(st_names)), f"Duplicate names")
    check("3.6 Station names trimmed without leading/trailing whitespace", all(n == n.strip() for n in st_names), "Untrimmed names")

    # Coordinates
    lats = [s["latitude"] for s in stations]
    lons = [s["longitude"] for s in stations]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    report["stats"]["station_lat_range"] = [min_lat, max_lat]
    report["stats"]["station_lon_range"] = [min_lon, max_lon]

    check("3.7 All station lats in [27.0, 35.5] N", 27.0 <= min_lat and max_lat <= 35.5, f"Lat range: [{min_lat}, {max_lat}]")
    check("3.8 All station lons in [69.0, 76.5] E", 69.0 <= min_lon and max_lon <= 76.5, f"Lon range: [{min_lon}, {max_lon}]")

    # Alias check
    alias_match = all(s["lat"] == s["latitude"] and s["lon"] == s["longitude"] for s in stations)
    check("3.9 lat/lon aliases match latitude/longitude identically", alias_match, "Alias mismatch")

    # Coordinate uniqueness
    st_coords = list(zip(lats, lons))
    check("3.10 All 79 station coordinates are geographically distinct", len(st_coords) == len(set(st_coords)), f"{len(st_coords)} vs {len(set(st_coords))}")

    # Mobile stations
    mobile = [s for s in stations if s["mobile"]]
    fixed = [s for s in stations if not s["mobile"]]
    check("3.11 Exactly 5 mobile stations", len(mobile) == 5, f"Got {len(mobile)}")
    check("3.12 Exactly 74 fixed stations", len(fixed) == 74, f"Got {len(fixed)}")
    check("3.13 All mobile stations located in Lahore", all(s["district"] == "Lahore" for s in mobile), "Mobile station not in Lahore")

    # ---------------------------------------------------------
    # 4. 41 District Boundaries & Topology
    # ---------------------------------------------------------
    with open(BASELINE_DIR / "districts.json", "r", encoding="utf-8") as f:
        districts = json.load(f)
    with open(BASELINE_DIR / "districts_dict.json", "r", encoding="utf-8") as f:
        districts_dict = json.load(f)

    check("4.1 District count is exactly 41", len(districts) == 41, f"Got {len(districts)}")
    check("4.2 districts_dict has 41 keys matching district names", len(districts_dict) == 41 and set(districts_dict.keys()) == {d["name"] for d in districts}, "Dict mismatch")

    d_lats = [d["latitude"] for d in districts]
    d_lons = [d["longitude"] for d in districts]
    report["stats"]["district_lat_range"] = [min(d_lats), max(d_lats)]
    report["stats"]["district_lon_range"] = [min(d_lons), max(d_lons)]
    check("4.3 All district centroids in [27.0, 35.5] N", 27.0 <= min(d_lats) and max(d_lats) <= 35.5, f"Centroid lat range [{min(d_lats)}, {max(d_lats)}]")
    check("4.4 All district centroids in [69.0, 76.5] E", 69.0 <= min(d_lons) and max(d_lons) <= 76.5, f"Centroid lon range [{min(d_lons)}, {max(d_lons)}]")

    # Station coverage per district
    st_by_district = {}
    for s in stations:
        st_by_district.setdefault(s["district"], []).append(s["name"])

    all_d_have_stations = all(len(d["stations"]) >= 1 for d in districts)
    check("4.5 Every district has >= 1 station", all_d_have_stations, "District with 0 stations found")

    st_counts_match = all(d["station_count"] == len(d["stations"]) for d in districts)
    check("4.6 station_count matches len(stations) for all districts", st_counts_match, "Station count mismatch")

    sum_stations = sum(len(d["stations"]) for d in districts)
    check("4.7 Sum of district station arrays equals 79", sum_stations == 79, f"Sum is {sum_stations}")

    # Boundary polygon validation
    total_rings = 0
    total_vertices = 0
    rings_closed = True
    vertices_in_bounds = True
    rings_have_area = True

    for d in districts:
        polys = d.get("boundary", [])
        assert len(polys) >= 1, f"District {d['name']} has empty boundary"
        for poly in polys:
            for ring in poly:
                total_rings += 1
                total_vertices += len(ring)
                if len(ring) < 4 or ring[0] != ring[-1]:
                    rings_closed = False
                area = shoelace_area(ring)
                if area <= 1e-6:
                    rings_have_area = False
                for pt in ring:
                    lon, lat = pt
                    if not (69.0 <= lon <= 76.5 and 27.0 <= lat <= 35.5):
                        vertices_in_bounds = False

    report["stats"]["total_polygon_rings"] = total_rings
    report["stats"]["total_boundary_vertices"] = total_vertices
    check("4.8 All polygon boundary rings are closed (ring[0] == ring[-1])", rings_closed, "Unclosed ring found")
    check("4.9 All boundary vertices within Punjab bounds", vertices_in_bounds, "Vertex out of bounds")
    check("4.10 All polygon rings have positive non-zero area", rings_have_area, "Zero area ring found")

    # Spatial sanity: Station to district centroid distance
    max_dist = 0.0
    for s in stations:
        d = districts_dict[s["district"]]
        dist = haversine_distance(s["latitude"], s["longitude"], d["latitude"], d["longitude"])
        if dist > max_dist:
            max_dist = dist
    report["stats"]["max_station_to_district_centroid_km"] = max_dist
    check("4.11 Max station to district centroid distance < 100 km", max_dist < 100.0, f"Max distance {max_dist:.1f} km too large")

    # ---------------------------------------------------------
    # 5. 216 Continuous Baseline Hours & Pollutant Integrity
    # ---------------------------------------------------------
    with open(BASELINE_DIR / "baseline_data.json", "r", encoding="utf-8") as f:
        baseline = json.load(f)

    hours = baseline.get("hours", [])
    check("5.1 Exactly 216 hours in baseline_data.json", len(hours) == 216, f"Got {len(hours)}")

    # Monotonic 1-hour deltas
    parsed_hours = [datetime.strptime(h, "%Y-%m-%d %H:%M") for h in hours]
    start_time = parsed_hours[0]
    end_time = parsed_hours[-1]
    check("5.2 Start hour is 2026-11-01 00:00", start_time == datetime(2026, 11, 1, 0, 0), f"Got {start_time}")
    check("5.3 End hour is 2026-11-09 23:00", end_time == datetime(2026, 11, 9, 23, 0), f"Got {end_time}")

    continuous = True
    for i in range(len(parsed_hours) - 1):
        if parsed_hours[i + 1] - parsed_hours[i] != timedelta(hours=1):
            continuous = False
            break
    check("5.4 Zero gaps: strictly continuous 1-hour deltas across all 216 hours", continuous, "Discontinuity found")

    # Multi-pollutant completeness
    expected_pollutants = ["AQI", "PM10", "PM2.5", "NO2", "SO2", "CO", "O3", "NO", "NOX"]
    pol = baseline.get("pol", {})
    check("5.5 All 9 pollutants present in pol", set(pol.keys()) == set(expected_pollutants), f"Keys: {set(pol.keys())}")

    all_frames_valid = True
    all_series_valid = True
    obs_counts = {}

    for p in expected_pollutants:
        frames = pol[p].get("frames", [])
        series = pol[p].get("series", [])
        if len(frames) != 216 or len(series) != 216:
            all_frames_valid = False
            break
        valid_vals = 0
        null_vals = 0
        for f in frames:
            c = f.get("c", {})
            if len(c) != 41 or set(c.keys()) != set(districts_dict.keys()):
                all_frames_valid = False
                break
            for val in c.values():
                if val is not None:
                    if not isinstance(val, (int, float)) or val < 0 or val > 5000:
                        all_frames_valid = False
                    valid_vals += 1
                else:
                    null_vals += 1
        obs_counts[p] = {"valid": valid_vals, "null": null_vals}

    report["stats"]["pollutant_obs_counts"] = obs_counts
    check("5.6 216 frames per pollutant with exactly 41 districts each", all_frames_valid, "Invalid frames structure or values")

    # Wind fields
    wind = baseline.get("wind", [])
    check("5.7 216 wind frames", len(wind) == 216, f"Got {len(wind)}")
    wind_valid = True
    max_wind_speed = 0.0
    for frame in wind:
        if len(frame) != 41 or set(frame.keys()) != set(districts_dict.keys()):
            wind_valid = False
            break
        for u, v in frame.values():
            spd = (u * u + v * v) ** 0.5
            if spd > max_wind_speed:
                max_wind_speed = spd
            if spd > 50.0:
                wind_valid = False
    report["stats"]["max_district_wind_speed_ms"] = max_wind_speed
    check("5.8 All 216 wind frames have 41 valid district vectors (speed <= 50 m/s)", wind_valid, "Invalid wind vectors")

    # Airports
    airports = baseline.get("airports", [])
    check("5.9 Exactly 6 airports", len(airports) == 6, f"Got {len(airports)}")
    check("5.10 Expected ICAO codes (OPLA, OPFA, OPMT, OPST, OPIS, VIAR)", {ap["id"] for ap in airports} == {"OPLA", "OPFA", "OPMT", "OPST", "OPIS", "VIAR"}, "ICAO mismatch")
    airports_series_valid = all(len(ap.get("u", [])) == 216 and len(ap.get("v", [])) == 216 for ap in airports)
    check("5.11 All airports have 216 hourly u/v wind components", airports_series_valid, "Airport series length mismatch")

    # Transboundary
    tbgeo = baseline.get("tbgeo", {})
    check("5.12 Exactly 24 border districts in tbgeo", len(tbgeo.get("districts", {})) == 24, f"Got {len(tbgeo.get('districts', {}))}")
    samples = tbgeo.get("samples", [])
    check("5.13 Exactly 39 normal vector nodes in tbgeo", len(samples) == 39, f"Got {len(samples)}")
    normals_normalized = all(0.9 <= (s[2]**2 + s[3]**2)**0.5 <= 1.1 for s in samples)
    check("5.14 All 39 normal vectors are normalized (magnitude ~ 1.0)", normals_normalized, "Unnormalized normal vectors")

    # ---------------------------------------------------------
    # 6. Bitwise & Numerical Cross-Check against window.DATA
    # ---------------------------------------------------------
    # Compare raw_data['stations'] with stations.json
    raw_st = raw_data["stations"]
    st_match = True
    for i in range(79):
        if raw_st[i]["name"] != stations[i]["name"]:
            st_match = False
            break
        if abs(raw_st[i]["lat"] - stations[i]["latitude"]) > 1e-9:
            st_match = False
            break
        if abs(raw_st[i]["lon"] - stations[i]["longitude"]) > 1e-9:
            st_match = False
            break
    check("6.1 Zero-drift cross-check: stations.json strictly matches window.DATA['stations']", st_match, "Station data drift")

    # Compare raw_data['districts'] with districts.json
    raw_dist = raw_data["districts"]
    dist_match = True
    for d in districts:
        name = d["name"]
        if name not in raw_dist:
            dist_match = False
            break
        if abs(raw_dist[name]["lat"] - d["latitude"]) > 1e-9:
            dist_match = False
            break
        if abs(raw_dist[name]["lon"] - d["longitude"]) > 1e-9:
            dist_match = False
            break
        if sorted(raw_dist[name].get("stations", [])) != sorted(d["stations"]):
            dist_match = False
            break
    check("6.2 Zero-drift cross-check: districts.json strictly matches window.DATA['districts']", dist_match, "District data drift")

    # Hours match
    check("6.3 Zero-drift cross-check: baseline hours strictly match window.DATA['hours']", baseline["hours"] == raw_data["hours"], "Hours list mismatch")

    # Total check summary
    print("\n=== EMPIRICAL CHALLENGE RESULTS ===")
    print(f"Total checks: {len(report['passed_checks']) + len(report['failed_checks'])}")
    print(f"Passed: {len(report['passed_checks'])}")
    print(f"Failed: {len(report['failed_checks'])}")
    print(f"FINAL VERDICT: {report['verdict']}")
    print("\nSummary Statistics:")
    print(json.dumps(report["stats"], indent=2))

    return report


if __name__ == "__main__":
    report = run_checks()
    if report["verdict"] != "CONFIRM":
        sys.exit(1)
