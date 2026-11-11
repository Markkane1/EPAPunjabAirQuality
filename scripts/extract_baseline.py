#!/usr/bin/env python3
"""Baseline data extractor for Punjab Air Quality Information System.

Extracts structured baseline datasets from original System/index.html:
- data/baseline/stations.json: 79 stations across 41 districts
- data/baseline/districts.json: 41 districts with centroids, monitoring status, and boundaries
- data/baseline/airports.json: 6 airports with coordinates and wind vectors
- data/baseline/baseline_data.json: Full 216-hour historical dataset
"""
import json
import os
import re
import sys
from pathlib import Path

# Portal ID mappings from legacy collector.py
PMAP = {
    "10": "DHQ Sheikhupura", "12": "FMDRC-LHR", "13": "GCU Faisalabad", "15": "Govt. Teaching Hospital Shahdara-LHR",
    "18": "Kahna Nau Hospital-LHR", "19": "LWMC-LHR", "27": "Gulberg III Lahore - Mobile 1", "22": "PKLI-LHR",
    "23": "Punjab University-LHR", "24": "Safari Park-LHR", "177": "Nankana Sahib", "171": "Sahiwal", "178": "Jhang",
    "25": "UET-LHR", "30": "Egerton Road - Mobile 4", "169": "Pakpattan",
    "20": "M. Nawaz Sharif University of Engineering & Technology Multan", "29": "Wagha Border LHR - Mobile 3",
    "33": "DC Office Narowal", "170": "Okara", "34": "DC Office Hafizabad", "28": "Lathepur LHR - Mobile 2",
    "37": "DC Office Khanewal", "172": "Wazirabad", "3": "BZU Multan", "5": "DC Office Faisalabad", "174": "Rajanpur",
    "175": "Vehari", "31": "BHU Jandiala Kalsan LHR - Mobile 5", "180": "Kot Addu", "35": "DC Office Gujrat",
    "21": "NTU Faisalabad", "179": "Attok", "173": "Mandi Bahauddin", "181": "Bhakkar", "2": "BISE Sargodha",
    "6": "DC Office Gujranwala", "39": "DC Office Rahim Yar Khan", "184": "Khushab", "185": "Mianwali",
    "9": "DC Office Sialkot", "38": "DC Office Muzaffargarh", "14": "GCW Gujranwala", "4": "DC Office DG Khan",
    "8": "DC Office Sargodha", "16": "IUB (Baghdad Campus) Bahawalpur", "17": "IUB (Khawaja Fareed Campus) Bahawalpur",
    "176": "Jhelum", "11": "Drug Testing Laboratory Rawalpindi", "7": "DC Office Rawalpindi", "36": "DC Office Chakwal",
    "183": "Talagang", "1": "ARID University Rawalpindi", "186": "Murree", "32": "DC Office Kasur"
}
NAME_TO_PMAP = {v: k for k, v in PMAP.items()}


def find_index_html(root_dir: Path) -> Path:
    candidates = [
        root_dir / "original System" / "index.html",
        root_dir / "original System" / "index.HTML",
        root_dir / "index.html",
    ]
    for c in candidates:
        if c.is_file():
            return c
    raise FileNotFoundError(f"Could not locate index.html in {root_dir} or {root_dir / 'original System'}")


def load_window_data(html_path: Path) -> dict:
    print(f"Reading {html_path}...")
    with open(html_path, "r", encoding="utf-8") as f:
        for line in f:
            if "window.DATA=" in line:
                raw_json = line.split("window.DATA=")[1].rstrip(";\n</script> ")
                return json.loads(raw_json)
    raise ValueError(f"Could not find 'window.DATA=' in {html_path}")


def extract_baseline(root_dir: Path = None):
    if root_dir is None:
        root_dir = Path(__file__).resolve().parent.parent

    html_path = find_index_html(root_dir)
    data = load_window_data(html_path)

    out_dir = root_dir / "data" / "baseline"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. stations.json (79 stations)
    stations_raw = data.get("stations", [])
    coordsrc = data.get("coordsrc", {})
    qa_raw = data.get("qa", {})

    stations = []
    for idx, s in enumerate(stations_raw):
        name = s["name"]
        district = s.get("d", "")
        lat = float(s["lat"])
        lon = float(s["lon"])
        mobile = bool(s.get("mobile", False))
        portal_id = NAME_TO_PMAP.get(name)
        station_id = portal_id if portal_id is not None else f"st_{idx + 1:02d}"

        station_record = {
            "id": station_id,
            "station_id": station_id,
            "numeric_id": idx + 1,
            "name": name,
            "district": district,
            "d": district,
            "latitude": lat,
            "longitude": lon,
            "lat": lat,
            "lon": lon,
            "mobile": mobile,
            "network_type": "mobile" if mobile else "fixed",
            "coord_source": coordsrc.get(name, "Unknown"),
            "qa_summary": qa_raw.get(name, {}),
        }
        stations.append(station_record)

    stations_file = out_dir / "stations.json"
    with open(stations_file, "w", encoding="utf-8") as f:
        json.dump(stations, f, indent=2)
    print(f"Wrote {len(stations)} stations to {stations_file}")

    # 2. districts.json (41 districts)
    districts_raw = data.get("districts", {})
    adm_raw = data.get("adm", {})

    districts = []
    districts_dict = {}
    for idx, (d_name, d_info) in enumerate(sorted(districts_raw.items())):
        lat = float(d_info["lat"])
        lon = float(d_info["lon"])
        est = bool(d_info.get("est", False))
        st_list = d_info.get("stations", [])
        adm_info = adm_raw.get(d_name, {})
        label = adm_info.get("label", [lon, lat])
        polys = adm_info.get("polys", [])

        district_record = {
            "id": idx + 1,
            "name": d_name,
            "district": d_name,
            "latitude": lat,
            "longitude": lon,
            "lat": lat,
            "lon": lon,
            "centroid": [lat, lon],
            "est": est,
            "is_monitored": not est,
            "stations": st_list,
            "station_count": len(st_list),
            "label": label,
            "boundary": polys,
            "polys": polys,
        }
        districts.append(district_record)
        districts_dict[d_name] = district_record

    districts_file = out_dir / "districts.json"
    with open(districts_file, "w", encoding="utf-8") as f:
        json.dump(districts, f, indent=2)
    print(f"Wrote {len(districts)} districts to {districts_file}")

    # Also save districts_dict.json for O(1) map access
    districts_dict_file = out_dir / "districts_dict.json"
    with open(districts_dict_file, "w", encoding="utf-8") as f:
        json.dump(districts_dict, f, indent=2)

    # 3. airports.json (6 airports)
    airports_raw = data.get("airports", [])
    airports = []
    for ap in airports_raw:
        airport_record = {
            "id": ap["id"],
            "icao": ap["id"],
            "name": ap["name"],
            "latitude": float(ap["lat"]),
            "longitude": float(ap["lon"]),
            "lat": float(ap["lat"]),
            "lon": float(ap["lon"]),
            "u": ap.get("u", []),
            "v": ap.get("v", []),
            "hr": ap.get("hr", []),
        }
        airports.append(airport_record)

    airports_file = out_dir / "airports.json"
    with open(airports_file, "w", encoding="utf-8") as f:
        json.dump(airports, f, indent=2)
    print(f"Wrote {len(airports)} airports to {airports_file}")

    # 4. baseline_data.json (216-hour structured historical dataset)
    baseline_payload = {
        "meta": data.get("meta", {}),
        "hours": data.get("hours", []),
        "districts": districts_dict,
        "stations": stations,
        "airports": airports,
        "pol": data.get("pol", {}),
        "wind": data.get("wind", []),
        "tbgeo": data.get("tbgeo", {}),
        "ecm": data.get("ecm", {}),
        "coordsrc": data.get("coordsrc", {}),
        "qa": data.get("qa", {}),
        "network": data.get("network", []),
        "skipped": data.get("skipped", {}),
        "wsrc": data.get("wsrc", []),
        "wscale": data.get("wscale", []),
    }

    baseline_file = out_dir / "baseline_data.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(baseline_payload, f)
    print(f"Wrote complete baseline payload ({len(baseline_payload['hours'])} hours) to {baseline_file}")

    return {
        "stations_count": len(stations),
        "districts_count": len(districts),
        "airports_count": len(airports),
        "hours_count": len(baseline_payload["hours"]),
    }


if __name__ == "__main__":
    results = extract_baseline()
    print("Baseline extraction completed successfully:")
    print(json.dumps(results, indent=2))
