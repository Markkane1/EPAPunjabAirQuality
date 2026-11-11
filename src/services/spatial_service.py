"""
SpatialService: Continuous 2D surface interpolation matrices, opacity confidence tapers, and collision-free label placements.
"""
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Tuple

from src.domain.entities.models import SurfaceGridPoint
from src.domain.interfaces.repositories import (
    AnalyticsRepository,
    DistrictRepository,
    ObservationRepository,
    StationRepository,
)
from src.domain.math.geodesy import haversine_distance
from src.domain.math.idw import (
    anisotropic_idw,
    calculate_distance_opacity,
    discrete_geodesic_idw,
)
from src.domain.math.pepc_aqi import normalize_pollutant_key
from src.domain.math.projection import (
    equirectangular_project,
    equirectangular_unproject,
    greedy_label_placement,
)
from src.services.dto import LabelPlacementDTO, SurfaceFieldDTO


class SpatialService:
    """
    Computes continuous 2D IDW geostatistical surface grids,
    distance confidence opacity matrices, and district label placements.
    """

    def __init__(
        self,
        observation_repo: Optional[ObservationRepository] = None,
        station_repo: Optional[StationRepository] = None,
        district_repo: Optional[DistrictRepository] = None,
        analytics_repo: Optional[AnalyticsRepository] = None,
        repo: Optional[Any] = None,
        cache_ttl_seconds: int = 3600,
    ) -> None:
        self._obs_repo = observation_repo or repo
        self._station_repo = station_repo or repo
        self._district_repo = district_repo or repo
        self._analytics_repo = analytics_repo or repo
        self._cache_ttl = cache_ttl_seconds
        self._cache: Dict[str, Tuple[float, SurfaceFieldDTO]] = {}

    def get_surface_matrix(
        self,
        timestamp: Optional[datetime] = None,
        pollutant: str = "PM2.5",
        resolution: int = 5,
        width_px: int = 600,
        height_px: int = 450,
        use_anisotropic: bool = False,
    ) -> SurfaceFieldDTO:
        """
        Computes 2D raster field of interpolated pollutant concentrations.
        Clamps resolution between 1 and 50 px.
        """
        res = max(1, min(50, resolution))
        pol_key = normalize_pollutant_key(pollutant)

        ts = timestamp or self._obs_repo.get_latest_timestamp()
        if ts is None:
            ts = datetime.now(timezone.utc)
        ts_utc = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)

        # Cache lookup
        cache_key = f"{pol_key}:{ts_utc.isoformat()}:{res}:{width_px}x{height_px}:{use_anisotropic}"
        if cache_key in self._cache:
            saved_time, cached_dto = self._cache[cache_key]
            if (datetime.now().timestamp() - saved_time) < self._cache_ttl:
                return cached_dto

        # Fetch reporting stations for timestamp
        stn_obs = self._obs_repo.get_station_observations_at_timestamp(ts_utc)
        stations_map = {s.id: s for s in self._station_repo.list_stations()}

        active_nodes: List[Dict[str, Any]] = []
        for o in stn_obs:
            meta = stations_map.get(o.station_id)
            if not meta or meta.station_type == "airport_metar":
                continue
            val = o.aqi if pol_key == "AQI" else getattr(o, pol_key.lower().replace(".", ""), None)
            if val is not None and not math.isnan(val) and val > 0:
                px, py = equirectangular_project(meta.latitude, meta.longitude, width_px, height_px)
                active_nodes.append({
                    "station_id": o.station_id,
                    "coords": (meta.latitude, meta.longitude),
                    "coords_px": (px, py),
                    "value": float(val),
                    "u": o.u,
                    "v": o.v,
                })

        grid_w = max(1, width_px // res)
        grid_h = max(1, height_px // res)

        if not active_nodes:
            # Fallback zero grid
            empty_matrix = [[0.0] * grid_w for _ in range(grid_h)]
            empty_opacity = [[95] * grid_w for _ in range(grid_h)]
            dto = SurfaceFieldDTO(
                timestamp=ts_utc.isoformat(),
                pollutant=pol_key,
                resolution=res,
                grid_width=grid_w,
                grid_height=grid_h,
                min_val=0.0,
                max_val=0.0,
                grid_matrix=empty_matrix,
                opacity_matrix=empty_opacity,
            )
            self._cache[cache_key] = (datetime.now().timestamp(), dto)
            return dto

        matrix: List[List[float]] = []
        opacity_matrix: List[List[int]] = []
        min_v = float("inf")
        max_v = float("-inf")

        for j in range(grid_h):
            row_vals: List[float] = []
            row_opacities: List[int] = []
            py = (j + 0.5) * res
            for i in range(grid_w):
                px = (i + 0.5) * res
                if use_anisotropic:
                    val, km_min, alpha = anisotropic_idw((px, py), active_nodes)
                else:
                    lat, lon = equirectangular_unproject(px, py, width_px, height_px)
                    val = discrete_geodesic_idw((lat, lon), active_nodes, power=2.0, d0=5.0) or 0.0
                    # Compute nearest distance in km
                    min_d = min(
                        haversine_distance(lat, lon, node["coords"][0], node["coords"][1])
                        for node in active_nodes
                    )
                    alpha = calculate_distance_opacity(min_d)

                f_val = round(float(val), 2)
                row_vals.append(f_val)
                row_opacities.append(alpha)

                if f_val < min_v:
                    min_v = f_val
                if f_val > max_v:
                    max_v = f_val

            matrix.append(row_vals)
            opacity_matrix.append(row_opacities)

        dto = SurfaceFieldDTO(
            timestamp=ts_utc.isoformat(),
            pollutant=pol_key,
            resolution=res,
            grid_width=grid_w,
            grid_height=grid_h,
            min_val=min_v if min_v != float("inf") else 0.0,
            max_val=max_v if max_v != float("-inf") else 0.0,
            grid_matrix=matrix,
            opacity_matrix=opacity_matrix,
        )

        self._cache[cache_key] = (datetime.now().timestamp(), dto)
        return dto

    # Alias for get_surface_matrix
    compute_surface_grid = get_surface_matrix

    def get_district_label_placements(
        self,
        width_px: float = 1200.0,
        height_px: float = 900.0,
    ) -> List[LabelPlacementDTO]:
        """
        Computes collision-free district text labels with leader line detection.
        """
        districts = self._district_repo.list_districts()
        label_inputs: List[Dict[str, Any]] = []

        for d in districts:
            ax, ay = equirectangular_project(d.latitude, d.longitude, width_px, height_px)
            label_inputs.append({
                "district_id": d.id,
                "text": d.name,
                "anchor_x": ax,
                "anchor_y": ay,
                "width": max(48.0, len(d.name) * 7.5),
                "height": 16.0,
            })

        placements = greedy_label_placement(label_inputs)
        return [
            LabelPlacementDTO(
                district_id=p["district_id"],
                text=p["text"],
                anchor_x=p["anchor_x"],
                anchor_y=p["anchor_y"],
                placed_x=p["placed_x"],
                placed_y=p["placed_y"],
                offset_x=p["offset_x"],
                offset_y=p["offset_y"],
                has_leader_line=p["has_leader_line"],
                bounding_box=p["bounding_box"],
            )
            for p in placements
        ]
