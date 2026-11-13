"""
Redis 7.2 Cache Adapter implementing domain AnalyticsRepository interface.
Caches 16-sector CPF wind roses, inter-district transport flux links, transboundary results,
and precalculated IDW surface grids with automatic TTL eviction and invalidation.
"""
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.domain.entities.models import (
    AdvectionFluxLink,
    CPFRoseResult,
    SurfaceGridPoint,
    TransboundaryResult,
)
from src.domain.interfaces.repositories import AnalyticsRepository
from src.infrastructure.cache.redis_manager import RedisCacheManager

logger = logging.getLogger("paq.cache.analytics")


class RedisAnalyticsRepository(AnalyticsRepository):
    """
    High-speed cache implementation backed by Redis 7.2.
    Replaces in-memory _surface_cache, _cpf_cache, _flux_cache with scalable distributed storage.
    """

    def __init__(self, cache_manager: Optional[RedisCacheManager] = None) -> None:
        self.cache = cache_manager or RedisCacheManager.get_instance()
        # In-memory local fallback buffer
        self._local_cpf: Dict[Tuple[str, str], CPFRoseResult] = {}
        self._local_flux: Dict[Tuple[str, str], List[AdvectionFluxLink]] = {}
        self._local_tb: Dict[str, TransboundaryResult] = {}
        self._local_surface: Dict[Tuple[str, str, int], List[SurfaceGridPoint]] = {}

    def _format_ts(self, ts: datetime) -> str:
        """Formats datetime to canonical UTC ISO string for key namespacing."""
        dt = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
        return dt.strftime("%Y%m%d%H")

    # =========================================================================
    # 1. 16-Sector CPF Polar Wind Rose Analytics Cache
    # =========================================================================

    def get_cpf_rose(self, district_id: str, pollutant: str) -> Optional[CPFRoseResult]:
        """
        Retrieves cached 16-sector CPF wind rose analysis for a district.
        Key pattern: paq:cpf:{district_id}:{pollutant}
        """
        did = district_id.strip().lower()
        pol = pollutant.upper()
        key = f"paq:cpf:{did}:{pol}"

        data = self.cache.get_json(key)
        if data:
            try:
                return CPFRoseResult(
                    district_id=data["district_id"],
                    pollutant=data["pollutant"],
                    threshold=float(data["threshold"]),
                    calm_ratio=float(data["calm_ratio"]),
                    sectors=tuple(data["sectors"]),
                    sector_counts=tuple(data.get("sector_counts", [])),
                    sector_exceedances=tuple(data.get("sector_exceedances", [])),
                )
            except Exception as e:
                logger.warning(f"Error parsing cached CPF rose for {key}: {e}")

        # Local fallback
        return self._local_cpf.get((did, pol))

    def save_cpf_rose(self, result: CPFRoseResult) -> None:
        """
        Caches CPF wind rose analysis result with 24-hour TTL (docs/SYSTEM_ARCHITECTURE.md §4.3).
        """
        did = result.district_id.strip().lower()
        pol = result.pollutant.upper()
        key = f"paq:cpf:{did}:{pol}"

        data = {
            "district_id": result.district_id,
            "pollutant": result.pollutant,
            "threshold": result.threshold,
            "calm_ratio": result.calm_ratio,
            "sectors": list(result.sectors),
            "sector_counts": list(result.sector_counts),
            "sector_exceedances": list(result.sector_exceedances),
        }
        # 24-hour TTL: 86400 seconds
        self.cache.set_json(key, data, ttl_seconds=86400)
        self._local_cpf[(did, pol)] = result

    # =========================================================================
    # 2. Inter-District Advection Transport Mass Flux Links Cache
    # =========================================================================

    def get_advection_flux(self, timestamp: datetime, pollutant: str) -> Optional[List[AdvectionFluxLink]]:
        """
        Retrieves cached transport flux link vectors.
        Key pattern: paq:flux:{YYYYMMDDHH}:{pollutant}
        """
        ts_str = self._format_ts(timestamp)
        pol = pollutant.upper()
        key = f"paq:flux:{ts_str}:{pol}"

        data = self.cache.get_json(key)
        if data and isinstance(data, list):
            try:
                return [
                    AdvectionFluxLink(
                        source_district=link["source_district"],
                        receptor_district=link["receptor_district"],
                        distance_km=float(link["distance_km"]),
                        bearing_deg=float(link["bearing_deg"]),
                        divergence_deg=float(link["divergence_deg"]),
                        flux=float(link["flux"]),
                        omega=float(link.get("omega", 0.25)),
                        score=float(link.get("score", 0.0)),
                    )
                    for link in data
                ]
            except Exception as e:
                logger.warning(f"Error parsing cached flux for {key}: {e}")

        return self._local_flux.get((ts_str, pol))

    def save_advection_flux(
        self, timestamp: datetime, pollutant: str, links: Sequence[AdvectionFluxLink]
    ) -> None:
        """
        Caches transport flux link vectors with 7-day TTL.
        """
        ts_str = self._format_ts(timestamp)
        pol = pollutant.upper()
        key = f"paq:flux:{ts_str}:{pol}"

        data = [
            {
                "source_district": link.source_district,
                "receptor_district": link.receptor_district,
                "distance_km": link.distance_km,
                "bearing_deg": link.bearing_deg,
                "divergence_deg": link.divergence_deg,
                "flux": link.flux,
                "omega": link.omega,
                "score": link.score,
            }
            for link in links
        ]
        self.cache.set_json(key, data, ttl_seconds=604800)
        self._local_flux[(ts_str, pol)] = list(links)

    # =========================================================================
    # 3. Transboundary Cross-Border Mass Balance Cache
    # =========================================================================

    def get_transboundary_result(self, timestamp: datetime) -> Optional[TransboundaryResult]:
        """
        Retrieves cached cross-border transboundary mass balance index.
        Key pattern: paq:transboundary:{YYYYMMDDHH}
        """
        ts_str = self._format_ts(timestamp)
        key = f"paq:transboundary:{ts_str}"

        data = self.cache.get_json(key)
        if data:
            try:
                dt = datetime.fromisoformat(data["timestamp"])
                return TransboundaryResult(
                    timestamp=dt,
                    inflow_total=float(data["inflow_total"]),
                    outflow_total=float(data["outflow_total"]),
                    net_flux=float(data["net_flux"]),
                    district_values=data.get("district_values", {}),
                    normal_fluxes=data.get("normal_fluxes", []),
                )
            except Exception as e:
                logger.warning(f"Error parsing cached transboundary for {key}: {e}")

        return self._local_tb.get(ts_str)

    def save_transboundary_result(self, result: TransboundaryResult) -> None:
        """
        Caches transboundary mass balance result with 7-day TTL.
        """
        ts_str = self._format_ts(result.timestamp)
        key = f"paq:transboundary:{ts_str}"

        data = {
            "timestamp": result.timestamp.isoformat(),
            "inflow_total": result.inflow_total,
            "outflow_total": result.outflow_total,
            "net_flux": result.net_flux,
            "district_values": result.district_values,
            "normal_fluxes": result.normal_fluxes,
        }
        self.cache.set_json(key, data, ttl_seconds=604800)
        self._local_tb[ts_str] = result

    # =========================================================================
    # 4. Continuous IDW Surface Grid Cache
    # =========================================================================

    def get_surface_grid(
        self, timestamp: datetime, pollutant: str, resolution: int
    ) -> Optional[List[SurfaceGridPoint]]:
        """
        Retrieves cached continuous IDW surface grid points.
        Key pattern: paq:surface:{pollutant}:{YYYYMMDDHH}:{resolution}
        """
        ts_str = self._format_ts(timestamp)
        pol = pollutant.upper()
        key = f"paq:surface:{pol}:{ts_str}:{resolution}"

        data = self.cache.get_json(key)
        if data and isinstance(data, list):
            try:
                return [
                    SurfaceGridPoint(
                        x=float(pt["x"]),
                        y=float(pt["y"]),
                        value=float(pt["value"]),
                        nearest_station_km=float(pt["nearest_station_km"]),
                        alpha=int(pt["alpha"]),
                    )
                    for pt in data
                ]
            except Exception as e:
                logger.warning(f"Error parsing cached surface grid for {key}: {e}")

        return self._local_surface.get((ts_str, pol, resolution))

    def save_surface_grid(
        self, timestamp: datetime, pollutant: str, resolution: int, grid: Sequence[SurfaceGridPoint]
    ) -> None:
        """
        Caches continuous surface grid points with 7-day TTL (or 900s for static snapshot).
        """
        ts_str = self._format_ts(timestamp)
        pol = pollutant.upper()
        key = f"paq:surface:{pol}:{ts_str}:{resolution}"

        data = [
            {
                "x": pt.x,
                "y": pt.y,
                "value": pt.value,
                "nearest_station_km": pt.nearest_station_km,
                "alpha": pt.alpha,
            }
            for pt in grid
        ]
        self.cache.set_json(key, data, ttl_seconds=604800)
        self._local_surface[(ts_str, pol, resolution)] = list(grid)

    # =========================================================================
    # 5. Cache Invalidation
    # =========================================================================

    def clear_cache(self) -> None:
        """
        Purges all analytical caches upon dynamic dataset updates (e.g. CSV ingestion).
        """
        self.cache.clear_pattern("paq:surface:*")
        self.cache.clear_pattern("paq:flux:*")
        self.cache.clear_pattern("paq:cpf:*")
        self.cache.clear_pattern("paq:transboundary:*")

        self._local_cpf.clear()
        self._local_flux.clear()
        self._local_tb.clear()
        self._local_surface.clear()
        logger.info("Purged all Redis analytical caches.")
