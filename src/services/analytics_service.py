"""
AnalyticsService: 16-sector CPF polar wind rose source apportionment,
inter-district advection transport mass flux, and transboundary cross-border mass balance.
"""
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional

from src.domain.entities.models import AdvectionFluxLink, CPFRoseResult
from src.domain.interfaces.repositories import (
    AnalyticsRepository,
    DistrictRepository,
    ObservationRepository,
    StationRepository,
)
from src.domain.math.cpf import calculate_cpf_rose
from src.domain.math.flux import (
    calculate_advection_flux,
    calculate_net_transport_balance,
    calculate_receptor_coupling,
)
from src.domain.math.geodesy import haversine_distance
from src.domain.math.pepc_aqi import normalize_pollutant_key
from src.domain.math.transboundary import (
    calculate_border_normal_flux,
    calculate_district_transboundary_flux,
    calculate_transboundary_index,
)
from src.services.dto import (
    BorderDistrictTransboundaryDTO,
    BorderSampleNodeDTO,
    CPFRoseResponseDTO,
    CPFSectorDTO,
    FluxLinkDTO,
    FluxResponseDTO,
    TransboundaryResponseDTO,
)

SECTOR_LABELS_16: List[str] = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


class AnalyticsService:
    """
    Coordinates deep analytical processing for air quality source apportionment,
    inter-district mass transport flux, and international transboundary mass balance.
    """

    def __init__(
        self,
        observation_repo: Optional[ObservationRepository] = None,
        station_repo: Optional[StationRepository] = None,
        district_repo: Optional[DistrictRepository] = None,
        analytics_repo: Optional[AnalyticsRepository] = None,
        repo: Optional[Any] = None,
    ) -> None:
        self._obs_repo = observation_repo or repo
        self._station_repo = station_repo or repo
        self._district_repo = district_repo or repo
        self._analytics_repo = analytics_repo or repo

    def calculate_cpf(
        self,
        district_name: str,
        pollutant: str = "PM2.5",
        custom_threshold: Optional[float] = None,
        calm_threshold_ms: float = 0.5,
    ) -> CPFRoseResponseDTO:
        """
        Calculates 16-sector Conditional Probability Function (CPF) polar rose.
        Pools station-hour observations across all monitoring stations in the district.
        """
        pol_key = normalize_pollutant_key(pollutant)

        # Validate target district
        target_dist = self._district_repo.get_district_by_name(district_name)
        if not target_dist:
            # Fallback to search by ID or strip
            for d in self._district_repo.list_districts():
                if d.name.strip().lower() == district_name.strip().lower():
                    target_dist = d
                    break
        if not target_dist:
            raise ValueError(f"Unknown administrative district: '{district_name}'")

        # Check repository cache
        if self._analytics_repo:
            cached_rose = self._analytics_repo.get_cpf_rose(target_dist.name, pol_key)
            if cached_rose and custom_threshold is None:
                sectors_dto = [
                    CPFSectorDTO(
                        sector_index=k,
                        azimuth_deg=round(k * 22.5, 1),
                        direction_label=SECTOR_LABELS_16[k],
                        total_hours=cached_rose.sector_counts[k] if k < len(cached_rose.sector_counts) else 0,
                        exceedance_hours=cached_rose.sector_exceedances[k] if k < len(cached_rose.sector_exceedances) else 0,
                        cpf_probability=cached_rose.sectors[k],
                    )
                    for k in range(16)
                ]
                return CPFRoseResponseDTO(
                    district=target_dist.name,
                    pollutant=pol_key,
                    threshold_p75=cached_rose.threshold,
                    calm_fraction=cached_rose.calm_ratio,
                    null_hypothesis_baseline=0.25,
                    sectors=sectors_dto,
                )

        # Retrieve pooled station-hour observations
        stn_obs = self._obs_repo.get_station_observations_for_district(target_dist.name)
        obs_pool: List[Dict[str, Any]] = []

        p_attr = pol_key.lower().replace(".", "").replace("-", "")
        for so in stn_obs:
            val = so.aqi if pol_key == "AQI" else getattr(so, p_attr, None)
            if val is not None and not math.isnan(val) and val > 0:
                obs_pool.append({
                    "value": float(val),
                    "wind_speed": so.wind_speed,
                    "wind_direction": so.wind_direction,
                })

        # Fallback to district aggregated series if station observations pool is empty
        if not obs_pool:
            dist_obs = self._obs_repo.get_district_hourly_series(target_dist.name)
            for do in dist_obs:
                val = do.aqi if pol_key == "AQI" else getattr(do, p_attr, None)
                if val is not None and not math.isnan(val) and val > 0:
                    obs_pool.append({
                        "value": float(val),
                        "wind_speed": do.wind_speed,
                        "wind_direction": do.wind_direction,
                    })

        # Calculate CPF rose (Transform 5)
        rose = calculate_cpf_rose(
            observations=obs_pool,
            threshold_p75=custom_threshold,
            calm_threshold=calm_threshold_ms,
            min_samples=6,
        )

        sectors_dto = [
            CPFSectorDTO(
                sector_index=k,
                azimuth_deg=round(k * 22.5, 1),
                direction_label=SECTOR_LABELS_16[k],
                total_hours=rose["sector_counts"][k],
                exceedance_hours=rose["sector_exceedances"][k],
                cpf_probability=rose["sectors"][k],
            )
            for k in range(16)
        ]

        # Cache in repository
        if self._analytics_repo:
            cpf_entity = CPFRoseResult(
                district_id=target_dist.name,
                pollutant=pol_key,
                threshold=rose["threshold"],
                calm_ratio=rose["calm_ratio"],
                sectors=tuple(rose["sectors"]),
                sector_counts=tuple(rose["sector_counts"]),
                sector_exceedances=tuple(rose["sector_exceedances"]),
            )
            self._analytics_repo.save_cpf_rose(cpf_entity)

        return CPFRoseResponseDTO(
            district=target_dist.name,
            pollutant=pol_key,
            threshold_p75=rose["threshold"],
            calm_fraction=rose["calm_ratio"],
            null_hypothesis_baseline=0.25,
            sectors=sectors_dto,
        )

    def calculate_flux(
        self,
        pollutant: str = "PM2.5",
        timestamp: Optional[datetime] = None,
        top_k: int = 60,
    ) -> FluxResponseDTO:
        """
        Estimates inter-district physical advection flux, receptor feedback coupling,
        and net transport balances.
        MANDATORY DOMAIN GUARD: Physical advection is strictly disabled for 'AQI'.
        """
        # CRITICAL DOMAIN GUARD
        if pollutant.strip().upper() == "AQI":
            raise ValueError(
                "Advection transport mass flux is physically undefined for dimensionless ordinal index 'AQI'. "
                "Mass conservation requires conserved physical concentrations. "
                "Query a mass pollutant species such as PM2.5, PM10, NO2, SO2, CO, or O3."
            )

        pol_key = normalize_pollutant_key(pollutant)
        ts = timestamp or self._obs_repo.get_latest_timestamp()
        if ts is None:
            ts = datetime.now(timezone.utc)
        ts_utc = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)

        # Check repository cache
        if self._analytics_repo:
            cached_links = self._analytics_repo.get_advection_flux(ts_utc, pol_key)
            if cached_links is not None:
                link_dtos = [
                    FluxLinkDTO(
                        source_district=l.source_district,
                        receptor_district=l.receptor_district,
                        distance_km=l.distance_km,
                        bearing_deg=l.bearing_deg,
                        divergence_deg=l.divergence_deg,
                        flux=l.flux,
                        omega=l.omega,
                        score=l.score,
                    )
                    for l in cached_links[:top_k]
                ]
                raw_dict_links = [
                    {
                        "source_district": l.source_district,
                        "receptor_district": l.receptor_district,
                        "score": l.score,
                    }
                    for l in link_dtos
                ]
                net_bal = calculate_net_transport_balance(raw_dict_links)
                return FluxResponseDTO(
                    pollutant=pol_key,
                    timestamp=ts_utc.isoformat(),
                    total_links=len(link_dtos),
                    top_pathways=link_dtos,
                    links=link_dtos,
                    net_balance=net_bal,
                    net_balances=net_bal,
                )

        districts = self._district_repo.list_districts()
        obs_list = self._obs_repo.get_district_observations_at_timestamp(ts_utc)
        dist_obs_map = {o.district_id: o for o in obs_list}

        p_attr = pol_key.lower().replace(".", "").replace("-", "")

        flux_candidates: List[Dict[str, Any]] = []
        for src in districts:
            s_obs = dist_obs_map.get(src.name) or dist_obs_map.get(src.id)
            if not s_obs:
                continue
            val = getattr(s_obs, p_attr, None)
            if val is None or math.isnan(val) or val <= 0:
                continue

            for rcv in districts:
                if src.name == rcv.name:
                    continue
                d_km = haversine_distance(src.latitude, src.longitude, rcv.latitude, rcv.longitude)
                if d_km > 180.0:
                    continue

                flux_res = calculate_advection_flux(
                    source_station=(src.latitude, src.longitude),
                    receptor_coords=(rcv.latitude, rcv.longitude),
                    pollutant=pol_key,
                    concentration=val,
                    u_wind=s_obs.u,
                    v_wind=s_obs.v,
                    max_dist_km=180.0,
                    max_cone_deg=35.0,
                    residence_km=100.0,
                )
                if flux_res:
                    flux_candidates.append({
                        "source_district": src.name,
                        "receptor_district": rcv.name,
                        "distance_km": flux_res["distance_km"],
                        "bearing_deg": flux_res["bearing_deg"],
                        "divergence_deg": flux_res["divergence_deg"],
                        "mean_flux": flux_res["flux"],
                    })

        # Receptor coupling
        receptor_cpfs: Dict[str, Any] = {}
        for d in districts:
            if self._analytics_repo:
                cached_r = self._analytics_repo.get_cpf_rose(d.name, pol_key)
                if cached_r:
                    receptor_cpfs[d.name] = {"sectors": cached_r.sectors}

        ranked_links = calculate_receptor_coupling(
            flux_series=flux_candidates,
            receptor_cpfs=receptor_cpfs,
            max_links=top_k,
        )

        net_balances = calculate_net_transport_balance(ranked_links)

        link_dtos = [
            FluxLinkDTO(
                source_district=l["source_district"],
                receptor_district=l["receptor_district"],
                distance_km=l["distance_km"],
                bearing_deg=l["bearing_deg"],
                divergence_deg=l.get("divergence_deg", 0.0),
                flux=l["mean_flux"] if "mean_flux" in l else l["flux"],
                omega=l["omega"],
                score=l["score"],
            )
            for l in ranked_links
        ]

        # Save to repository cache
        if self._analytics_repo:
            domain_links = [
                AdvectionFluxLink(
                    source_district=ld.source_district,
                    receptor_district=ld.receptor_district,
                    distance_km=ld.distance_km,
                    bearing_deg=ld.bearing_deg,
                    divergence_deg=ld.divergence_deg,
                    flux=ld.flux,
                    omega=ld.omega,
                    score=ld.score,
                )
                for ld in link_dtos
            ]
            self._analytics_repo.save_advection_flux(ts_utc, pol_key, domain_links)

        return FluxResponseDTO(
            pollutant=pol_key,
            timestamp=ts_utc.isoformat(),
            total_links=len(link_dtos),
            top_pathways=link_dtos,
            links=link_dtos,
            net_balance=net_balances,
            net_balances=net_balances,
        )

    def calculate_transboundary(
        self,
        timestamp: Optional[datetime] = None,
        pollutant: str = "PM2.5",
    ) -> TransboundaryResponseDTO:
        """
        Computes regional cross-border inflow/outflow mass index across 120km border belt
        and 39 border normal vector nodes.
        """
        pol_key = normalize_pollutant_key(pollutant)
        ts = timestamp or self._obs_repo.get_latest_timestamp()
        if ts is None:
            ts = datetime.now(timezone.utc)
        ts_utc = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)

        border_districts = self._district_repo.list_border_districts(max_border_distance_km=120.0)
        dist_obs_list = self._obs_repo.get_district_observations_at_timestamp(ts_utc)
        dist_obs_map = {o.district_id: o for o in dist_obs_list}

        p_attr = pol_key.lower().replace(".", "").replace("-", "")

        border_inputs: List[Dict[str, Any]] = []
        for d in border_districts:
            obs = dist_obs_map.get(d.name) or dist_obs_map.get(d.id)
            c_val = getattr(obs, p_attr, 0.0) if obs else 0.0
            if c_val is None or math.isnan(c_val):
                c_val = 0.0
            u_val = obs.u if obs and obs.u is not None else 0.0
            v_val = obs.v if obs and obs.v is not None else 0.0
            is_est = obs.is_estimated if obs else not d.is_monitored

            border_inputs.append({
                "district_id": d.name,
                "name": d.name,
                "border_distance_km": d.border_distance_km,
                "india_sectors": list(d.india_inflow_sectors),
                "concentration": float(c_val),
                "u": float(u_val),
                "v": float(v_val),
                "is_estimated": is_est,
            })

        # Load 39 border samples from repository
        raw_samples = getattr(self._district_repo, "get_border_samples", lambda: [])()
        border_normals: List[Dict[str, Any]] = []
        border_sample_dtos: List[BorderSampleNodeDTO] = []

        # Find representative border wind for nodes from nearby border districts
        border_u_avg = sum(bi["u"] for bi in border_inputs) / len(border_inputs) if border_inputs else 0.0
        border_v_avg = sum(bi["v"] for bi in border_inputs) / len(border_inputs) if border_inputs else 0.0

        for idx, s in enumerate(raw_samples):
            lon, lat, nx, ny = s[0], s[1], s[2], s[3]
            phi = calculate_border_normal_flux(border_u_avg, border_v_avg, nx, ny)
            border_normals.append({"u": border_u_avg, "v": border_v_avg, "nx": nx, "ny": ny})
            border_sample_dtos.append(
                BorderSampleNodeDTO(
                    node_index=idx,
                    latitude=lat,
                    longitude=lon,
                    normal_x=nx,
                    normal_y=ny,
                    normal_flux=round(phi, 4),
                )
            )

        tb_result = calculate_transboundary_index(
            border_districts=border_inputs,
            border_normals=border_normals,
        )

        inflow_tot = tb_result["inflow_total"]
        outflow_tot = tb_result["outflow_total"]
        net_f = tb_result["net_flux"]

        if net_f > 0.05:
            status_str = "net_inflow"
        elif net_f < -0.05:
            status_str = "net_outflow"
        else:
            status_str = "neutral"

        district_detail_dtos: Dict[str, BorderDistrictTransboundaryDTO] = {}
        for bi in border_inputs:
            d_name = bi["name"]
            flux_val = tb_result["district_values"].get(d_name, 0.0)
            if flux_val > 0.0:
                mode = "inflow"
            elif flux_val < 0.0:
                mode = "outflow"
            else:
                mode = "calm" if math.hypot(bi["u"], bi["v"]) < 0.5 else "neutral"

            district_detail_dtos[d_name] = BorderDistrictTransboundaryDTO(
                district=d_name,
                border_distance_km=bi["border_distance_km"],
                inflow_sectors=bi["india_sectors"],
                transboundary_flux=flux_val,
                direction_mode=mode,
            )

        return TransboundaryResponseDTO(
            timestamp=ts_utc.isoformat(),
            pollutant=pol_key,
            inflow_total=inflow_tot,
            outflow_total=outflow_tot,
            net_transboundary_flux=net_f,
            net_flux=net_f,
            status=status_str,
            border_districts=district_detail_dtos,
            border_samples=border_sample_dtos,
            district_values=tb_result["district_values"],
            normal_fluxes=tb_result.get("normal_fluxes", []),
        )
