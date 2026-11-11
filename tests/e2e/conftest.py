"""
Pytest configuration and authoritative verification fixtures for Punjab Air Quality E2E test suites.
Implements the exact mathematical reference oracle derived from docs/TRANSFORMATION_LOGIC_SPEC.md.
"""
import csv
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pytest
from pydantic import BaseModel, Field, field_validator

# -----------------------------------------------------------------------------
# Base Directories & Fixtures Path Resolution
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def load_csv_fixture():
    """Helper to parse a CSV fixture into a list of row dictionaries."""
    def _loader(filename: str) -> List[Dict[str, str]]:
        filepath = FIXTURES_DIR / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Fixture file not found: {filepath}")
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)
    return _loader


@pytest.fixture(scope="session")
def reference_data() -> Dict[str, Any]:
    """Loads authoritative expected values JSON."""
    json_path = FIXTURES_DIR / "reference_expected_outputs.json"
    with open(json_path, mode="r", encoding="utf-8") as f:
        return json.load(f)


# -----------------------------------------------------------------------------
# Pydantic v2 Canonical Schemas (Derived from DATA_PIPELINES_ARCHITECTURE.md §4)
# -----------------------------------------------------------------------------
class RawStationMeasurementContract(BaseModel):
    station_id: Union[int, str]
    station_name: str = Field(..., min_length=2, max_length=100)
    district: str = Field(..., min_length=2, max_length=50)
    timestamp: datetime
    aqi: Optional[float] = Field(None, ge=0.0, le=2000.0)
    pm25: Optional[float] = Field(None, ge=0.0, le=5000.0)
    pm10: Optional[float] = Field(None, ge=0.0, le=5000.0)
    no2: Optional[float] = Field(None, ge=0.0, le=500.0)
    so2: Optional[float] = Field(None, ge=0.0, le=500.0)
    co: Optional[float] = Field(None, ge=0.0, le=50.0)
    o3: Optional[float] = Field(None, ge=0.0, le=400.0)
    wind_speed: Optional[float] = Field(None, ge=0.0, le=30.0)
    wind_direction: Optional[float] = Field(None, ge=0.0, le=360.0)


class UserCSVRowContract(BaseModel):
    timestamp: str
    station_id: str
    station_name: str
    district: str
    latitude: float = Field(..., ge=27.0, le=35.0)
    longitude: float = Field(..., ge=69.0, le=76.0)
    pollutant: str
    value: float = Field(..., ge=0.0, le=5000.0)
    wind_speed: Optional[float] = Field(None, ge=0.0, le=30.0)
    wind_direction: Optional[float] = Field(None, ge=0.0, le=360.0)

    @field_validator("pollutant")
    @classmethod
    def validate_pollutant_name(cls, v: str) -> str:
        valid_pollutants = {
            "aqi", "pm25", "pm10", "no2", "so2", "co", "o3", "no", "nox"
        }
        clean = v.strip().lower().replace(".", "")
        if clean not in valid_pollutants:
            raise ValueError(f"Invalid pollutant: {v}. Must be one of {valid_pollutants}")
        return clean


# -----------------------------------------------------------------------------
# Authoritative Reference Oracle (TRANSFORMATION_LOGIC_SPEC.md)
# -----------------------------------------------------------------------------
class PAQReferenceOracle:
    """
    Authoritative reference oracle implementing mathematical models
    from docs/TRANSFORMATION_LOGIC_SPEC.md with zero external dependencies.
    """
    R_EARTH = 6371.0  # WGS-84 mean radius in km

    # Statutory PEPC Breakpoint Tables (Continuous half-open intervals)
    PEPC_BREAKPOINTS = {
        "PM10": [0, 75, 150, 250, 350, 450, 550],
        "PM2.5": [0.0, 15.0, 35.0, 70.0, 140.0, 250.0, 350.0],
        "SO2": [0, 60, 120, 220, 320, 800, 1600],
        "NO2": [0, 40, 80, 130, 180, 380, 580],
        "O3": [0, 65, 130, 195, 260, 450, 550],
        "CO": [0.0, 2.5, 5.0, 7.5, 10.0, 25.0, 40.0]
    }
    AQI_INDEX_TIERS = [0, 50, 100, 150, 200, 300, 400, 500]

    PEPC_COLOR_HEX = [
        (50, "#00B050"),    # Good
        (100, "#92D050"),   # Satisfactory
        (150, "#FFFF00"),   # Moderate
        (200, "#ED7D31"),   # Unhealthy (Sensitive)
        (300, "#FF0000"),   # Unhealthy
        (400, "#7030A0"),   # Very Unhealthy
        (500, "#C00000"),   # Hazardous
    ]

    @classmethod
    def haversine_distance(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Great-circle distance in km using Haversine formula (§2.1.2)."""
        phi1 = math.radians(lat1)
        lam1 = math.radians(lon1)
        phi2 = math.radians(lat2)
        lam2 = math.radians(lon2)
        dphi = phi2 - phi1
        dlam = lam2 - lam1
        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(dlam / 2.0) ** 2)
        c = 2.0 * math.asin(math.sqrt(max(0.0, min(1.0, a))))
        return cls.R_EARTH * c

    @classmethod
    def discrete_geodesic_idw(
        cls,
        target_coords: Tuple[float, float],
        monitored_nodes: List[Dict[str, Any]],
        power: float = 2.0,
        d0_km: float = 5.0
    ) -> Optional[float]:
        """Imputes missing values using Haversine metric and singularity clamping (§2.1.2)."""
        valid_nodes = [
            n for n in monitored_nodes
            if n.get("value") is not None and not math.isnan(n["value"])
        ]
        if not valid_nodes:
            return None

        w_sum = 0.0
        v_sum = 0.0
        t_lat, t_lon = target_coords

        for node in valid_nodes:
            n_lat, n_lon = node["coords"]
            d = cls.haversine_distance(t_lat, t_lon, n_lat, n_lon)
            d_eff = max(d, d0_km)
            w = 1.0 / (d_eff ** power)
            w_sum += w
            v_sum += w * float(node["value"])

        return v_sum / w_sum if w_sum > 0 else None

    @classmethod
    def polar_to_cartesian_wind(
        cls, speed_ms: float, dir_deg: float
    ) -> Optional[Tuple[float, float]]:
        """
        Converts polar wind to Cartesian flow vectors (u, v) in m/s (§2.4.2).
        Enforces physical bounds: speed in [0, 30.0], direction in [0, 360.0].
        """
        if speed_ms is None or speed_ms < 0.0 or speed_ms > 30.0:
            return None
        if dir_deg is None or dir_deg < 0.0 or dir_deg > 360.0:
            return None

        theta_rad = math.radians(dir_deg)
        u = -speed_ms * math.sin(theta_rad)
        v = -speed_ms * math.cos(theta_rad)
        return (u, v)

    @classmethod
    def cartesian_to_polar_wind(cls, u: float, v: float) -> Tuple[float, float]:
        """Reconstructs scalar speed and meteorological direction FROM from (u, v)."""
        speed = math.sqrt(u ** 2 + v ** 2)
        direction = (math.degrees(math.atan2(-u, -v)) + 360.0) % 360.0
        return (speed, direction)

    @classmethod
    def calculate_cpf_rose(
        cls,
        observations: List[Dict[str, Any]],
        threshold_p75: float,
        calm_threshold_ms: float = 0.5
    ) -> Dict[str, Any]:
        """
        Calculates 16-sector Conditional Probability Function with calm exclusion
        and small-sample suppression (Nk >= 6) (§2.5.2).
        """
        total_obs = len(observations)
        if total_obs == 0:
            return {
                "sectors": [None] * 16,
                "calm_ratio": 0.0,
                "threshold": threshold_p75
            }

        calm_count = 0
        sector_n = [0] * 16
        sector_m = [0] * 16

        for obs in observations:
            ws = obs.get("wind_speed", 0.0)
            wd = obs.get("wind_direction", 0.0)
            c = obs.get("value", 0.0)

            if ws is None or ws < calm_threshold_ms:
                calm_count += 1
                continue

            sector_idx = int(math.floor(((wd + 11.25) % 360.0) / 22.5)) % 16
            sector_n[sector_idx] += 1
            if c > threshold_p75:
                sector_m[sector_idx] += 1

        calm_ratio = calm_count / total_obs
        sectors: List[Optional[float]] = []
        for k in range(16):
            if sector_n[k] >= 6:
                sectors.append(round(sector_m[k] / sector_n[k], 4))
            else:
                sectors.append(None)  # Small-sample suppression

        return {
            "sectors": sectors,
            "calm_ratio": round(calm_ratio, 4),
            "threshold": threshold_p75
        }

    @classmethod
    def calculate_advection_flux(
        cls,
        source_coords: Tuple[float, float],
        receptor_coords: Tuple[float, float],
        concentration: float,
        u_wind: float,
        v_wind: float,
        pollutant: str,
        max_dist_km: float = 180.0,
        cone_deg: float = 35.0,
        residence_km: float = 100.0
    ) -> Optional[Dict[str, Any]]:
        """
        Calculates physical inter-district mass flux (§2.6.2).
        Strictly disallowed for dimensionless ordinal index 'AQI'.
        """
        if pollutant.strip().upper() == "AQI":
            return None  # Physical dimension guard

        d_km = cls.haversine_distance(
            source_coords[0], source_coords[1], receptor_coords[0], receptor_coords[1]
        )
        if d_km > max_dist_km or d_km <= 0.0:
            return None

        w_speed = math.sqrt(u_wind ** 2 + v_wind ** 2)
        if w_speed < 0.5:  # Calm cutoff
            return None

        # Source to receptor forward bearing
        phi_a = math.radians(source_coords[0])
        phi_b = math.radians(receptor_coords[0])
        dlam = math.radians(receptor_coords[1] - source_coords[1])
        y = math.sin(dlam) * math.cos(phi_b)
        x = math.cos(phi_a) * math.sin(phi_b) - math.sin(phi_a) * math.cos(phi_b) * math.cos(dlam)
        theta_brg = (math.degrees(math.atan2(y, x)) + 360.0) % 360.0

        # Advection vector bearing (TO)
        theta_to = (math.degrees(math.atan2(u_wind, v_wind)) + 360.0) % 360.0

        # Angular divergence delta_theta
        delta_theta = abs(((theta_to - theta_brg + 180.0) % 360.0) - 180.0)
        if delta_theta > cone_deg:
            return None

        flux_val = (
            concentration
            * w_speed
            * math.cos(math.radians(delta_theta))
            * math.exp(-d_km / residence_km)
        )
        return {
            "flux": round(flux_val, 4),
            "distance_km": round(d_km, 2),
            "bearing_deg": round(theta_brg, 2),
            "divergence_deg": round(delta_theta, 2)
        }

    @classmethod
    def pepc_calculate_aqi(cls, pollutant: str, concentration: float) -> Optional[int]:
        """
        Official PEPC continuous piecewise linear sub-index interpolation (§2.9.2).
        Applies operational ceiling cap at 500 when concentration exceeds highest bracket.
        """
        if concentration is None or concentration < 0.0:
            return None

        key = pollutant.strip().upper()
        if key == "PM25":
            key = "PM2.5"

        if key not in cls.PEPC_BREAKPOINTS:
            return None

        bps = cls.PEPC_BREAKPOINTS[key]
        tiers = cls.AQI_INDEX_TIERS

        # Operational Ceiling Cap
        if concentration > bps[-1]:
            return 500

        # Piecewise interpolation across continuous half-open intervals
        for i in range(1, len(bps)):
            bp_low = bps[i - 1]
            bp_high = bps[i]
            if bp_low < concentration <= bp_high:
                i_low = tiers[i - 1]
                i_high = tiers[i]
                aqi = ((i_high - i_low) / (bp_high - bp_low)) * (concentration - bp_low) + i_low
                return int(round(aqi))

        # Exactly zero edge case
        if concentration == 0.0:
            return 0

        return 500

    @classmethod
    def pepc_composite_aqi(
        cls, pm25_aqi: Optional[int], pm10_aqi: Optional[int]
    ) -> Optional[int]:
        """
        Composite Punjab AQI: strictly governed by particulate matter sub-indices (§2.9.3).
        composite = max(I_PM2.5, I_PM10).
        """
        valid = [i for i in [pm25_aqi, pm10_aqi] if i is not None]
        return max(valid) if valid else None

    @classmethod
    def pepc_get_color(cls, aqi: int) -> str:
        """Official PEPC category color mapping."""
        for threshold, hex_code in cls.PEPC_COLOR_HEX:
            if aqi <= threshold:
                return hex_code
        return "#C00000"

    @classmethod
    def temporal_qc_clean(
        cls,
        series: List[Optional[float]],
        ref_limit: float,
        pollutant: str
    ) -> Tuple[List[Optional[float]], int]:
        """
        Executes zero sanitization, 7h median spike filter, and 3h logger hold filter (§2.10.1).
        Enforces i >= 2 index guard on hold filter.
        """
        cleaned = [None if (v is None or v <= 0.0 or math.isnan(v)) else float(v) for v in series]
        n = len(cleaned)
        spike_count = 0

        # 1. 7-Hour Rolling Window Median Spike Filter
        for i in range(n):
            if cleaned[i] is None:
                continue
            window = [
                cleaned[j]
                for j in range(max(0, i - 3), min(n, i + 4))
                if cleaned[j] is not None
            ]
            if len(window) >= 3:
                window_sorted = sorted(window)
                mid = len(window_sorted) // 2
                median_val = (
                    window_sorted[mid]
                    if len(window_sorted) % 2 != 0
                    else (window_sorted[mid - 1] + window_sorted[mid]) / 2.0
                )
                if cleaned[i] > 4.0 * median_val and cleaned[i] > 3.0 * ref_limit:
                    cleaned[i] = None
                    spike_count += 1

        # 2. 3-Hour Logger Hold (Sensor Freeze) Filter with Index Guard (i >= 2)
        if pollutant.strip().upper() != "AQI":
            for i in range(2, n):
                if (
                    cleaned[i] is not None
                    and cleaned[i - 1] is not None
                    and cleaned[i - 2] is not None
                    and cleaned[i] == cleaned[i - 1] == cleaned[i - 2]
                ):
                    cleaned[i] = None

        return (cleaned, spike_count)

    @classmethod
    def equirectangular_project(
        cls,
        lat: float,
        lon: float,
        width_px: float = 1200.0,
        height_px: float = 900.0
    ) -> Tuple[float, float]:
        """Plate Carree with standard parallel 31 deg N (§2.11.1)."""
        lon_min, lon_max = 69.10, 75.75
        lat_min, lat_max = 27.55, 34.30
        kx = math.cos(math.radians(31.0))
        scale = width_px / ((lon_max - lon_min) * kx)
        x = (lon - lon_min) * kx * scale
        y = (lat_max - lat) * scale
        return (x, y)


@pytest.fixture(scope="session")
def reference_oracle() -> PAQReferenceOracle:
    return PAQReferenceOracle()
