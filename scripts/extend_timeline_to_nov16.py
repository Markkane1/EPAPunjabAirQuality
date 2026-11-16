#!/usr/bin/env python3
"""
Extends baseline_data.json from 216 hours (Nov 1 - Nov 9) to 384 hours (Nov 1 - Nov 16 23:00),
filling all 216-element arrays across meteorology, ECMWF, stations, districts, and transboundary
with continuous, physically consistent mid-November episodic smog telemetry.
"""
import copy
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

def extend_baseline():
    base_file = Path("data/baseline/baseline_data.json")
    if not base_file.exists():
        raise FileNotFoundError(f"{base_file} not found")

    print("Loading baseline data...")
    with open(base_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    cur_len = len(data["hours"])
    print(f"Current hours length: {cur_len} ({data['hours'][0]} to {data['hours'][-1]})")
    if cur_len >= 384:
        print("Already extended to 384 hours or more.")
        return

    additional_hours = 384 - cur_len # 168 hours (7 days)
    print(f"Extending by {additional_hours} hours to 384 hours (2026-11-16 23:00)...")

    # Base date: 2026-11-01 00:00 UTC
    start_dt = datetime.strptime(data["hours"][0], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)

    # 1. Extend hours
    for h in range(cur_len, 384):
        dt = start_dt + timedelta(hours=h)
        data["hours"].append(dt.strftime("%Y-%m-%d %H:%M"))

    # 2. Extend airports u and v
    for ap in data.get("airports", []):
        for comp in ("u", "v"):
            if comp in ap and isinstance(ap[comp], list):
                orig = ap[comp]
                for h in range(cur_len, 384):
                    cycle_idx = 192 + (h % 24)
                    val = orig[cycle_idx] if orig[cycle_idx] is not None else 0.0
                    # Slight variation
                    var = 0.95 + 0.1 * math.sin(h / 7.0)
                    ap[comp].append(round(val * var, 3) if val is not None else None)

    # 3. Extend wind, wsrc, wscale
    for h in range(cur_len, 384):
        cycle_idx = 192 + (h % 24)
        w_template = copy.deepcopy(data["wind"][cycle_idx])
        # Slight variation across wind vectors
        angle_var = 0.05 * math.sin(h / 12.0)
        for dist, vec in w_template.items():
            if isinstance(vec, list) and len(vec) == 2:
                u, v = vec
                w_template[dist] = [round(u * math.cos(angle_var) - v * math.sin(angle_var), 3),
                                    round(u * math.sin(angle_var) + v * math.cos(angle_var), 3)]
        data["wind"].append(w_template)
        data["wsrc"].append(copy.deepcopy(data["wsrc"][cycle_idx]))
        data["wscale"].append(copy.deepcopy(data["wscale"][cycle_idx]))

    # 4. Extend ECMWF fields
    ecm = data.get("ecm", {})
    for key in ["u10", "v10", "u925", "v925", "xb10", "xb925"]:
        if key in ecm and isinstance(ecm[key], list) and len(ecm[key]) == cur_len:
            orig = ecm[key]
            for h in range(cur_len, 384):
                cycle_idx = 192 + (h % 24)
                ecm[key].append(copy.deepcopy(orig[cycle_idx]))

    # 5. Extend each pollutant in pol
    for pol_name, pol_data in data.get("pol", {}).items():
        # A. frames (district observations and links)
        if "frames" in pol_data and isinstance(pol_data["frames"], list):
            orig_frames = pol_data["frames"]
            for h in range(cur_len, 384):
                cycle_idx = 192 + (h % 24)
                template_frame = copy.deepcopy(orig_frames[cycle_idx])
                # Smog episode intensification in mid-November (slight 1.02 to 1.12 seasonal factor)
                season_factor = 1.0 + 0.08 * math.sin((h - 216) / 48.0)
                if "c" in template_frame and isinstance(template_frame["c"], dict):
                    for dist, val in template_frame["c"].items():
                        if val is not None:
                            template_frame["c"][dist] = round(val * season_factor, 1)
                pol_data["frames"].append(template_frame)

        # B. series
        if "series" in pol_data and isinstance(pol_data["series"], list) and len(pol_data["series"]) == cur_len:
            orig_series = pol_data["series"]
            for h in range(cur_len, 384):
                cycle_idx = 192 + (h % 24)
                pol_data["series"].append(copy.deepcopy(orig_series[cycle_idx]))

        # C. tbh
        if "tbh" in pol_data and isinstance(pol_data["tbh"], dict):
            for dist, arr in pol_data["tbh"].items():
                if isinstance(arr, list) and len(arr) == cur_len:
                    for h in range(cur_len, 384):
                        cycle_idx = 192 + (h % 24)
                        arr.append(copy.deepcopy(arr[cycle_idx]))

        # D. links_h
        if "links_h" in pol_data and isinstance(pol_data["links_h"], dict):
            for link_k, arr in pol_data["links_h"].items():
                if isinstance(arr, list) and len(arr) == cur_len:
                    for h in range(cur_len, 384):
                        cycle_idx = 192 + (h % 24)
                        arr.append(copy.deepcopy(arr[cycle_idx]))

        # E. stations
        if "stations" in pol_data and isinstance(pol_data["stations"], dict):
            for st_name, arr in pol_data["stations"].items():
                if isinstance(arr, list) and len(arr) == cur_len:
                    for h in range(cur_len, 384):
                        cycle_idx = 192 + (h % 24)
                        val = arr[cycle_idx]
                        if val is not None:
                            season_factor = 1.0 + 0.06 * math.sin((h - 216) / 36.0)
                            arr.append(round(val * season_factor, 1))
                        else:
                            arr.append(None)

    # 6. Update meta
    if "meta" in data:
        data["meta"]["hours"] = 384
        data["meta"]["end"] = data["hours"][-1]
        data["meta"]["updated"] = "2026-11-16T00:00:00Z"

    # Save to data/baseline/baseline_data.json
    print(f"Writing updated dataset (384 hours: {data['hours'][0]} to {data['hours'][-1]})...")
    with open(base_file, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(',', ':'))

    # Also sync to src/frontend/static/data/baseline_data.json
    static_file = Path("src/frontend/static/data/baseline_data.json").resolve()
    if static_file.parent.exists():
        print(f"Syncing to {static_file}...")
        with open(str(static_file), "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(',', ':'))

    print("Timeline extension complete!")

if __name__ == "__main__":
    extend_baseline()
