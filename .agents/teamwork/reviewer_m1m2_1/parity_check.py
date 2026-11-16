import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.domain.math.geodesy import haversine_distance, forward_bearing, back_bearing, angular_divergence
from src.domain.math.idw import discrete_geodesic_idw
from src.domain.math.wind import polar_to_cartesian_wind, cartesian_to_polar_wind
from src.domain.math.flux import calculate_advection_flux
from src.domain.math.pepc_aqi import pepc_calculate_aqi, pepc_composite_aqi
from src.domain.math.qc import temporal_qc_clean, check_completeness, subhourly_lerp
from src.domain.math.projection import equirectangular_project

# Test coordinates: Lahore to Rawalpindi
lat1, lon1 = 31.5204, 74.3587
lat2, lon2 = 33.5651, 73.0169

results = {
    "haversine": haversine_distance(lat1, lon1, lat2, lon2),
    "bearing": forward_bearing(lat1, lon1, lat2, lon2),
    "back_bearing": back_bearing(lat1, lon1, lat2, lon2),
    "divergence": angular_divergence(45.0, 315.0),
    "idw": discrete_geodesic_idw(
        (31.5, 74.0),
        [
            {"coords": (31.0, 73.5), "value": 120.0},
            {"coords": (32.0, 74.5), "value": 240.0},
        ],
        power=2.0,
        d0=5.0
    ),
    "wind_polar_to_cart": polar_to_cartesian_wind(12.5, 225.0), # SW wind blows TO NE
    "wind_cart_to_polar": cartesian_to_polar_wind(8.8388, 8.8388),
    "flux_pm25": calculate_advection_flux(
        (31.0, 74.0),
        (31.5, 74.0),
        "PM2.5",
        concentration=85.0,
        u_wind=0.0,
        v_wind=6.0
    ),
    "flux_aqi_guard": calculate_advection_flux(
        (31.0, 74.0),
        (31.5, 74.0),
        "AQI",
        concentration=180.0,
        u_wind=0.0,
        v_wind=6.0
    ),
    "aqi_pm25_120": pepc_calculate_aqi("PM2.5", 120.0),
    "aqi_pm25_450_clamp": pepc_calculate_aqi("PM2.5", 450.0),
    "composite_aqi": pepc_composite_aqi(155, 95),
    "qc_clean": temporal_qc_clean([10.0, 15.0, 12.0, 14.0, 15.0, 250.0, 16.0, 14.0, 15.0], 35.0, "PM2.5"),
    "completeness": check_completeness([10.0, 20.0, None, 40.0], 0.75),
    "subhourly": subhourly_lerp([10.0, 20.0, 30.0], 1.25),
    "projection": equirectangular_project(31.5204, 74.3587, 1200.0, 900.0)
}

output_path = Path(".agents/teamwork/reviewer_m1m2_1/python_results.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print(f"Python parity reference results written to {output_path}")
