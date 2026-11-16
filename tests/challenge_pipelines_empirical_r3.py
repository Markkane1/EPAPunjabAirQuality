"""
Empirical Challenge & Stress Harness: Milestone 3 Pipelines & Cross-Border Anchor Cities
Author: Challenger 2 (challenger_pipelines_r3_2)
Date: 2026-11-15

Mandatory Verification Probes:
1. Live Data Mandate & Upstream Telemetry Probing (Zero Synthetic Mocks).
2. Degraded State Contract Fault Injection across all 7 workers.
3. Cross-Border Anchor Cities Mathematical Differentiation & Seeder 24h Variance.
"""

import asyncio
import os
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import httpx
from datetime import datetime, timezone

from src.infrastructure.repositories.baseline_repository import BaselineRepository
from src.pipelines.epa_punjab import EPAPunjabIngestionWorker
from src.pipelines.metar import MetarIngestionWorker
from src.pipelines.synop import SynopIngestionWorker
from src.pipelines.open_meteo import OpenMeteoIngestionWorker
from src.pipelines.firms import FirmsIngestionWorker
from src.pipelines.iqair import IQAirIngestionWorker, TARGET_CROSS_BORDER_CITIES
from src.pipelines.cams import CamsIngestionWorker
from src.pipelines.scheduler import PipelineOrchestrator


async def probe_task1_live_telemetry():
    print("=" * 80)
    print("PROBE 1: LIVE DATA MANDATE & UPSTREAM ENDPOINTS")
    print("=" * 80)

    # 1.1 Probing public live upstream endpoints
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        # NOAA METAR
        r_metar = await client.get("https://aviationweather.gov/api/data/metar?ids=OPLA,OPIS,OPKC&format=json")
        assert r_metar.status_code == 200, f"METAR live probe failed: {r_metar.status_code}"
        metar_data = r_metar.json()
        assert len(metar_data) >= 1, "METAR returned empty live list"
        print(f"  [PASS] NOAA METAR live telemetry verified: {len(metar_data)} station reports fetched.")

        # ECMWF IFS Open-Meteo 10m Wind
        r_wind = await client.get("https://api.open-meteo.com/v1/forecast?latitude=31.5497&longitude=74.3436&current=temperature_2m,wind_speed_10m,wind_direction_10m")
        assert r_wind.status_code == 200, f"ECMWF IFS live probe failed: {r_wind.status_code}"
        assert "wind_speed_10m" in r_wind.json().get("current", {}), "ECMWF IFS missing live wind"
        print(f"  [PASS] ECMWF IFS Open-Meteo live telemetry verified: wind speed {r_wind.json()['current']['wind_speed_10m']} m/s.")

        # Copernicus CAMS Global Atmospheric Domain
        r_cams = await client.get("https://air-quality-api.open-meteo.com/v1/air-quality?latitude=31.634&longitude=74.8723&current=pm2_5,pm10,wind_speed_10m,wind_direction_10m&domains=cams_global")
        assert r_cams.status_code == 200, f"CAMS Global live probe failed: {r_cams.status_code}"
        cams_cur = r_cams.json().get("current", {})
        assert "pm2_5" in cams_cur, "CAMS Global missing pm2_5"
        print(f"  [PASS] Copernicus CAMS Global live telemetry verified: PM2.5 = {cams_cur['pm2_5']} ug/m3.")

        # Cross-Border Live Telemetry (Open-Meteo)
        r_cb = await client.get("https://air-quality-api.open-meteo.com/v1/air-quality?latitude=31.6340&longitude=74.8723&current=pm10,pm2_5,us_aqi")
        assert r_cb.status_code == 200, f"Cross-border live probe failed: {r_cb.status_code}"
        cb_cur = r_cb.json().get("current", {})
        assert "us_aqi" in cb_cur, "Cross-border missing us_aqi"
        print(f"  [PASS] Cross-Border Live telemetry verified: Amritsar AQI = {cb_cur['us_aqi']}.")

        # NASA FIRMS VIIRS NRT Feed
        firms_key = os.getenv("NASA_FIRMS_MAP_KEY", "")
        if firms_key and firms_key != "MOCK_NASA_FIRMS_KEY":
            r_firms = await client.get(f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{firms_key}/VIIRS_NOAA20_NRT/69,27,76,34/1")
            assert r_firms.status_code == 200, f"NASA FIRMS live probe failed: {r_firms.status_code}"
            assert len(r_firms.text) > 1000, f"NASA FIRMS payload too short: {len(r_firms.text)} bytes"
            print(f"  [PASS] NASA FIRMS VIIRS NRT live satellite feed verified: {len(r_firms.text)} bytes telemetry.")

    # 1.2 Asserting default worker_mode and orchestrator mode
    wf = FirmsIngestionWorker()
    wi = IQAirIngestionWorker()
    wc = CamsIngestionWorker()
    assert wf.worker_mode == "live", f"FIRMS worker_mode expected 'live', got {wf.worker_mode}"
    assert wi.worker_mode == "live", f"IQAir worker_mode expected 'live', got {wi.worker_mode}"
    assert wc.worker_mode == "live", f"CAMS worker_mode expected 'live', got {wc.worker_mode}"
    print("  [PASS] FirmsIngestionWorker, IQAirIngestionWorker, and CamsIngestionWorker default worker_mode == 'live'.")

    repo = BaselineRepository()
    orch = PipelineOrchestrator(repo)
    assert orch.mode == "live", f"PipelineOrchestrator expected 'live', got {orch.mode}"
    status = orch.get_status()
    expected_streams = [
        "STR-01-EPAPUNJAB",
        "STR-02-METAR",
        "STR-03-SYNOP",
        "STR-04-ECMWF-IFS",
        "STR-05-FIRMS",
        "STR-06-IQAIR",
        "STR-07-CAMS",
    ]
    assert status["live_enabled_streams"] == expected_streams, f"Enabled streams mismatch: {status['live_enabled_streams']}"
    assert len(status["live_stream_status"]) == 7, f"Expected 7 live streams in live_stream_status, got {len(status['live_stream_status'])}"
    for s_id in ["epa_punjab", "metar", "synop", "open_meteo", "firms", "iqair", "cams"]:
        assert s_id in status["live_stream_status"], f"Missing stream {s_id} in live_stream_status"
        assert s_id in orch.workers, f"Missing worker {s_id} in orchestrator.workers"
    print("  [PASS] PipelineOrchestrator defaults mode='live' and registers all 7 streams (STR-01 to STR-07).")


async def probe_task2_fault_injection():
    print("=" * 80)
    print("PROBE 2: DEGRADED STATE CONTRACT FAULT INJECTION")
    print("=" * 80)

    def failing_transport(request):
        raise httpx.ConnectTimeout("Simulated upstream network timeout / transport connection failure")

    mock_transport = httpx.MockTransport(failing_transport)

    workers = [
        ("EPA Punjab (STR-01)", EPAPunjabIngestionWorker(client=httpx.AsyncClient(transport=mock_transport))),
        ("NOAA METAR (STR-02)", MetarIngestionWorker(client=httpx.AsyncClient(transport=mock_transport))),
        ("WMO SYNOP (STR-03)", SynopIngestionWorker(client=httpx.AsyncClient(transport=mock_transport))),
        ("ECMWF IFS (STR-04)", OpenMeteoIngestionWorker(client=httpx.AsyncClient(transport=mock_transport))),
        ("NASA FIRMS (STR-05)", FirmsIngestionWorker(client=httpx.AsyncClient(transport=mock_transport), api_key="test_key")),
        ("IQAir (STR-06)", IQAirIngestionWorker(client=httpx.AsyncClient(transport=mock_transport))),
        ("CAMS (STR-07)", CamsIngestionWorker(client=httpx.AsyncClient(transport=mock_transport))),
    ]

    for name, w in workers:
        res = await w.run()
        assert w.is_healthy is False, f"{name}: is_healthy expected False, got {w.is_healthy}"
        assert w.status in ("degraded", "unavailable"), f"{name}: status expected 'degraded'/'unavailable', got {w.status}"
        assert res == [] or res is None, f"{name}: expected [] or None, got fabricated data: {res}"
        assert w.degraded_reason is not None, f"{name}: degraded_reason must be populated"
        print(f"  [PASS] {name}: healthy={w.is_healthy}, status='{w.status}', result={res}, reason='{w.degraded_reason[:50]}...'")

    # Circuit breaker verification
    w_cb = MetarIngestionWorker(client=httpx.AsyncClient(transport=mock_transport))
    for _ in range(5):
        await w_cb.run()
    assert w_cb.circuit_breaker_open is True, "Circuit breaker failed to trip after 5 failures"
    assert w_cb.status == "unavailable", f"Status expected 'unavailable', got {w_cb.status}"
    res_tripped = await w_cb.run()
    assert res_tripped == [], f"Circuit breaker trip must return [], got {res_tripped}"
    print("  [PASS] Circuit breaker trip verified: enters 'unavailable' state and blocks calls with empty return.")


def probe_task3_cross_border_anchor_cities():
    print("=" * 80)
    print("PROBE 3: CROSS-BORDER ANCHOR CITIES MATHEMATICAL DIFFERENTIATION")
    print("=" * 80)

    repo = BaselineRepository()
    cb = repo.get_cross_border()

    assert len(cb) >= 6, f"Expected at least 6 cross border cities, found {len(cb)}"
    city_names = [c["city"] for c in cb]
    expected = ["Amritsar", "Firozpur", "Jalandhar", "Ludhiana", "Bathinda", "Delhi NCR"]
    for exp in expected:
        assert exp in city_names, f"Expected city {exp} not found in {city_names}"
    print(f"  [PASS] All canonical cross-border anchor cities present within {len(cb)} regional monitoring nodes: {expected}")

    # Station IDs
    station_ids = [c["station_id"] for c in cb]
    assert len(set(station_ids)) == len(cb), f"Duplicate station IDs found: {len(set(station_ids))} unique vs {len(cb)} total"
    expected_ids = ["IN_ASR_001", "IN_FZP_001", "IN_JAL_001", "IN_LDH_001", "IN_BTI_001", "IN_DEL_001"]
    for exp_id in expected_ids:
        assert exp_id in station_ids, f"Expected station ID {exp_id} not found in {station_ids}"
    print(f"  [PASS] Distinct station IDs verified across all {len(cb)} cities")

    # Latitudes and Longitudes
    coords = [(c["latitude"], c["longitude"]) for c in cb]
    assert len(set(coords)) == len(cb), f"Duplicate coordinates detected: {len(set(coords))} unique vs {len(cb)} total"
    print(f"  [PASS] Distinct coordinates verified across all {len(cb)} nodes")

    # Baseline AQI, PM2.5, PM10
    aqis = [c["aqi"] for c in cb]
    pm25s = [c["pm25"] for c in cb]
    pm10s = [c["pm10"] for c in cb]

    assert len(set(aqis)) >= 6, f"Low AQI variation detected across cities: {len(set(aqis))} distinct"
    assert len(set(pm25s)) >= 6, f"Low PM2.5 variation detected across cities: {len(set(pm25s))} distinct"
    assert len(set(pm10s)) >= 6, f"Low PM10 variation detected across cities: {len(set(pm10s))} distinct"

    variance_aqi = float(np.var(aqis))
    assert variance_aqi > 0, f"AQI variance across cities must be non-zero, got {variance_aqi}"
    print(f"  [PASS] Baseline metrics distinct across {len(cb)} cities. Non-zero AQI variance: {variance_aqi:.2f}")

    # Seeder 24-hour simulation mathematical variance & zero collisions
    for idx in range(24):
        hour_aqis = []
        for c_info in TARGET_CROSS_BORDER_CITIES:
            base_aqi = float(c_info.get("base_aqi", 250.0))
            amp = float(c_info.get("diurnal_amp", 30.0))
            phase = float(c_info.get("phase_offset", 0.0))
            c_aqi = max(50.0, base_aqi + amp * math.sin((idx + phase) / 4.0))
            hour_aqis.append(round(c_aqi, 1))

        assert len(set(hour_aqis)) >= 6, f"Seeder collision detected at hour {idx}: {len(set(hour_aqis))} unique"
        var_h = float(np.var(hour_aqis))
        assert var_h > 500.0, f"Low variance at hour {idx}: {var_h}"

    print(f"  [PASS] Seeder 24-hour mathematical differentiation verified across {len(TARGET_CROSS_BORDER_CITIES)} cities.")


async def main():
    print("STARTING EMPIRICAL CHALLENGE HARNESS: PIPELINES & ANCHOR CITIES...")
    await probe_task1_live_telemetry()
    await probe_task2_fault_injection()
    probe_task3_cross_border_anchor_cities()
    print("=" * 80)
    print("ALL EMPIRICAL CHALLENGE PROBES PASSED WITH 100% SUCCESS RATE!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
