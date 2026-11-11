"""
Punjab Air Quality Scientific Transformation Engine.
Provides clean architecture pure mathematical algorithms with zero framework dependencies.
"""
from src.domain.math.geodesy import (
    haversine_distance,
    forward_bearing,
    back_bearing,
    angular_divergence,
    degrees_to_sector_16,
    sector_16_to_degrees,
    SECTOR_NAMES_16,
    R_EARTH_KM,
)
from src.domain.math.wind import (
    polar_to_cartesian_wind,
    cartesian_to_polar_wind,
    wind_direction_to_bearing,
    blend_winds,
    is_anemometer_valid,
    is_calm_wind,
    is_station_blacklisted,
    MIN_WIND_SPEED_MS,
    MAX_WIND_SPEED_MS,
    CALM_WIND_THRESHOLD_MS,
    WIND_BLACKLIST_STATIONS,
)
from src.domain.math.idw import (
    discrete_geodesic_idw,
    discrete_geodesic_idw_vector,
    anisotropic_idw,
    calculate_distance_opacity,
)
from src.domain.math.cpf import (
    calculate_cpf_rose,
    calculate_pooled_p75,
    calculate_rose_geometry,
    MIN_SECTOR_SAMPLES,
    DEFAULT_ISOTROPIC_BASELINE,
)
from src.domain.math.flux import (
    calculate_advection_flux,
    calculate_receptor_coupling,
    calculate_net_transport_balance,
    MAX_TRANSPORT_DISTANCE_KM,
    MAX_TRANSPORT_CONE_DEG,
    RESIDENCE_SCALE_KM,
    ISOTROPIC_OMEGA_FALLBACK,
    MAX_PATHWAY_LINKS,
)
from src.domain.math.transboundary import (
    calculate_district_transboundary_flux,
    calculate_border_normal_flux,
    calculate_transboundary_index,
    BORDER_CORRIDOR_LIMIT_KM,
)
from src.domain.math.pepc_aqi import (
    pepc_calculate_aqi,
    pepc_composite_aqi,
    pepc_get_category,
    pepc_get_color,
    pepc_interpolate_color,
    pepc_interpolate_color_hex,
    PEPC_BREAKPOINTS,
    AQI_TIERS,
    PEPC_CATEGORIES,
)
from src.domain.math.qc import (
    temporal_qc_clean,
    check_completeness,
    subhourly_lerp,
)
from src.domain.math.projection import (
    equirectangular_project,
    equirectangular_unproject,
    check_aabb_collision,
    greedy_label_placement,
    LON_MIN_DEG,
    LON_MAX_DEG,
    LAT_MIN_DEG,
    LAT_MAX_DEG,
    STANDARD_PARALLEL_DEG,
    KX_MERIDIONAL,
)

__all__ = [
    # Geodesy
    "haversine_distance",
    "forward_bearing",
    "back_bearing",
    "angular_divergence",
    "degrees_to_sector_16",
    "sector_16_to_degrees",
    "SECTOR_NAMES_16",
    "R_EARTH_KM",
    # Wind
    "polar_to_cartesian_wind",
    "cartesian_to_polar_wind",
    "wind_direction_to_bearing",
    "blend_winds",
    "is_anemometer_valid",
    "is_calm_wind",
    "is_station_blacklisted",
    "MIN_WIND_SPEED_MS",
    "MAX_WIND_SPEED_MS",
    "CALM_WIND_THRESHOLD_MS",
    "WIND_BLACKLIST_STATIONS",
    # IDW
    "discrete_geodesic_idw",
    "discrete_geodesic_idw_vector",
    "anisotropic_idw",
    "calculate_distance_opacity",
    # CPF
    "calculate_cpf_rose",
    "calculate_pooled_p75",
    "calculate_rose_geometry",
    "MIN_SECTOR_SAMPLES",
    "DEFAULT_ISOTROPIC_BASELINE",
    # Flux
    "calculate_advection_flux",
    "calculate_receptor_coupling",
    "calculate_net_transport_balance",
    "MAX_TRANSPORT_DISTANCE_KM",
    "MAX_TRANSPORT_CONE_DEG",
    "RESIDENCE_SCALE_KM",
    "ISOTROPIC_OMEGA_FALLBACK",
    "MAX_PATHWAY_LINKS",
    # Transboundary
    "calculate_district_transboundary_flux",
    "calculate_border_normal_flux",
    "calculate_transboundary_index",
    "BORDER_CORRIDOR_LIMIT_KM",
    # PEPC AQI
    "pepc_calculate_aqi",
    "pepc_composite_aqi",
    "pepc_get_category",
    "pepc_get_color",
    "pepc_interpolate_color",
    "pepc_interpolate_color_hex",
    "PEPC_BREAKPOINTS",
    "AQI_TIERS",
    "PEPC_CATEGORIES",
    # QC
    "temporal_qc_clean",
    "check_completeness",
    "subhourly_lerp",
    # Projection
    "equirectangular_project",
    "equirectangular_unproject",
    "check_aabb_collision",
    "greedy_label_placement",
    "LON_MIN_DEG",
    "LON_MAX_DEG",
    "LAT_MIN_DEG",
    "LAT_MAX_DEG",
    "STANDARD_PARALLEL_DEG",
    "KX_MERIDIONAL",
]
