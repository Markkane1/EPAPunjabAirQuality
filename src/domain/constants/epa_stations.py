"""
EPA Punjab Live AQMS Station Directory and Coordinate Mapping.
Compiled from live dashboard bundle and live API investigation (13 November 2026).
Defines all 38 monitoring stations across 19 city districts in Punjab.
"""
from typing import Any, Dict, List, Optional

EPA_STATIONS_CATALOG: Dict[str, Dict[str, Any]] = {
    "Safari Park-LHR": {
        "api_id": "Safari Park-LHR",
        "display_name": "Safari Park-LHR",
        "city": "Lahore",
        "district": "Lahore",
        "latitude": 31.382314774885888,
        "longitude": 74.21817281534902,
        "station_type": "fixed",
    },
    "Kahna Nau Hospital-LHR": {
        "api_id": "Kahna Nau Hospital-LHR",
        "display_name": "Kahna Nau Hospital-LHR",
        "city": "Lahore",
        "district": "Lahore",
        "latitude": 31.370968642952125,
        "longitude": 74.36509796071374,
        "station_type": "fixed",
    },
    "PKLI-LHR": {
        "api_id": "PKLI-LHR",
        "display_name": "PKLI-LHR",
        "city": "Lahore",
        "district": "Lahore",
        "latitude": 31.455944217196357,
        "longitude": 74.4637726464879,
        "station_type": "fixed",
    },
    "FMDRC-LHR": {
        "api_id": "FMDRC-LHR",
        "display_name": "FMDRC-LHR",
        "city": "Lahore",
        "district": "Lahore",
        "latitude": 31.535903137206997,
        "longitude": 74.43518804649057,
        "station_type": "fixed",
    },
    "UET-LHR": {
        "api_id": "UET-LHR",
        "display_name": "UET-LHR",
        "city": "Lahore",
        "district": "Lahore",
        "latitude": 31.579825674297712,
        "longitude": 74.35500334094795,
        "station_type": "fixed",
    },
    "LWMC-LHR": {
        "api_id": "LWMC-LHR",
        "display_name": "LWMC-LHR",
        "city": "Lahore",
        "district": "Lahore",
        "latitude": 31.463797290721757,
        "longitude": 74.22594175216207,
        "station_type": "fixed",
    },
    "Punjab University-LHR": {
        "api_id": "Punjab University-LHR",
        "display_name": "Punjab University-LHR",
        "city": "Lahore",
        "district": "Lahore",
        "latitude": 31.47965946421483,
        "longitude": 74.26608653889994,
        "station_type": "fixed",
    },
    "Govt. Teaching Hospital Shahdara-LHR": {
        "api_id": "Govt. Teaching Hospital Shahdara-LHR",
        "display_name": "Govt. Teaching Hospital Shahdara-LHR",
        "city": "Lahore",
        "district": "Lahore",
        "latitude": 31.638126385663895,
        "longitude": 74.28518245233634,
        "station_type": "fixed",
    },
    "DHQ Sheikhupura": {
        "api_id": "DHQ Sheikhupura",
        "display_name": "DHQ Sheikhupura",
        "city": "Sheikhupura",
        "district": "Sheikhupura",
        "latitude": 31.711907268506444,
        "longitude": 73.97887262744989,
        "station_type": "fixed",
    },
    "Mobile 1": {
        "api_id": "Mobile 1",
        "display_name": "Raja Jang Kasur - Mobile 1",
        "city": "Mobile AQMS",
        "district": "Kasur",
        "latitude": 31.22242652245513,
        "longitude": 74.25888348097924,
        "station_type": "mobile",
    },
    "Mobile 2": {
        "api_id": "Mobile 2",
        "display_name": "Lathepur LHR - Mobile 2",
        "city": "Mobile AQMS",
        "district": "Lahore",
        "latitude": 31.717597503919553,
        "longitude": 74.38945645216268,
        "station_type": "mobile",
    },
    "Mobile 3": {
        "api_id": "Mobile 3",
        "display_name": "Wagha Border LHR - Mobile 3",
        "city": "Mobile AQMS",
        "district": "Lahore",
        "latitude": 31.60217088224592,
        "longitude": 74.54493878284885,
        "station_type": "mobile",
    },
    "Mobile 4": {
        "api_id": "Mobile 4",
        "display_name": "Egerton Road - Mobile 4",
        "city": "Mobile AQMS",
        "district": "Lahore",
        "latitude": 31.560766512188792,
        "longitude": 74.33078657301355,
        "station_type": "mobile",
    },
    "Mobile 5": {
        "api_id": "Mobile 5",
        "display_name": "BHU Jandiala Kalsan LHR - Mobile 5",
        "city": "Mobile AQMS",
        "district": "Lahore",
        "latitude": 31.84868154529122,
        "longitude": 74.51479796751337,
        "station_type": "mobile",
    },
    "DC Office Faisalabad": {
        "api_id": "DC Office Faisalabad",
        "display_name": "DC Office Faisalabad",
        "city": "Faisalabad",
        "district": "Faisalabad",
        "latitude": 31.425448762788633,
        "longitude": 73.08115579440872,
        "station_type": "fixed",
    },
    "GCU Faisalabad": {
        "api_id": "GCU Faisalabad",
        "display_name": "GCU Faisalabad",
        "city": "Faisalabad",
        "district": "Faisalabad",
        "latitude": 31.416246064561182,
        "longitude": 73.07000252883559,
        "station_type": "fixed",
    },
    "NTU Faisalabad": {
        "api_id": "NTU Faisalabad",
        "display_name": "NTU Faisalabad",
        "city": "Faisalabad",
        "district": "Faisalabad",
        "latitude": 31.462112827887097,
        "longitude": 73.14854729999999,
        "station_type": "fixed",
    },
    "GCW Gujranwala": {
        "api_id": "GCW Gujranwala",
        "display_name": "GCW Gujranwala",
        "city": "Gujranwala",
        "district": "Gujranwala",
        "latitude": 32.25587012731105,
        "longitude": 74.15945324463222,
        "station_type": "fixed",
    },
    "DC Office Gujranwala": {
        "api_id": "DC Office Gujranwala",
        "display_name": "DC Office Gujranwala",
        "city": "Gujranwala",
        "district": "Gujranwala",
        "latitude": 32.17468001795155,
        "longitude": 74.19513105997787,
        "station_type": "fixed",
    },
    "BZU Multan": {
        "api_id": "BZU Multan",
        "display_name": "BZU Multan",
        "city": "Multan",
        "district": "Multan",
        "latitude": 30.262345863388603,
        "longitude": 71.51253806752977,
        "station_type": "fixed",
    },
    "M. Nawaz Sharif University of Engineering & Technology Multan": {
        "api_id": "M. Nawaz Sharif University of Engineering & Technology Multan",
        "display_name": "M. Nawaz Sharif University of Engineering & Technology Multan",
        "city": "Multan",
        "district": "Multan",
        "latitude": 30.029109580383068,
        "longitude": 71.54151150235819,
        "station_type": "fixed",
    },
    "IUB (Baghdad Campus) Bahawalpur": {
        "api_id": "IUB (Baghdad Campus) Bahawalpur",
        "display_name": "IUB (Baghdad Campus) Bahawalpur",
        "city": "Bahawalpur",
        "district": "Bahawalpur",
        "latitude": 29.376832580609566,
        "longitude": 71.76267240237333,
        "station_type": "fixed",
    },
    "IUB (Khawaja Fareed Campus) Bahawalpur": {
        "api_id": "IUB (Khawaja Fareed Campus) Bahawalpur",
        "display_name": "IUB (Khawaja Fareed Campus) Bahawalpur",
        "city": "Bahawalpur",
        "district": "Bahawalpur",
        "latitude": 29.397708118736162,
        "longitude": 71.69163577353685,
        "station_type": "fixed",
    },
    "DC Office Sargodha": {
        "api_id": "DC Office Sargodha",
        "display_name": "DC Office Sargodha",
        "city": "Sargodha",
        "district": "Sargodha",
        "latitude": 32.07161053848134,
        "longitude": 72.67279475998042,
        "station_type": "fixed",
    },
    "BISE Sargodha": {
        "api_id": "BISE Sargodha",
        "display_name": "BISE Sargodha",
        "city": "Sargodha",
        "district": "Sargodha",
        "latitude": 32.0355877857731,
        "longitude": 72.70063274138406,
        "station_type": "fixed",
    },
    "DC Office Sialkot": {
        "api_id": "DC Office Sialkot",
        "display_name": "DC Office Sialkot",
        "city": "Sialkot",
        "district": "Sialkot",
        "latitude": 32.50525590601202,
        "longitude": 74.53303397614911,
        "station_type": "fixed",
    },
    "DC Office Kasur": {
        "api_id": "DC Office Kasur",
        "display_name": "DC Office Kasur",
        "city": "Kasur",
        "district": "Kasur",
        "latitude": 31.11611,
        "longitude": 74.46725,
        "station_type": "fixed",
    },
    "DC Office Narowal": {
        "api_id": "DC Office Narowal",
        "display_name": "DC Office Narowal",
        "city": "Narowal",
        "district": "Narowal",
        "latitude": 32.09704,
        "longitude": 74.89411,
        "station_type": "fixed",
    },
    "DC Office Hafizabad": {
        "api_id": "DC Office Hafizabad",
        "display_name": "DC Office Hafizabad",
        "city": "Hafizabad",
        "district": "Hafizabad",
        "latitude": 32.07171,
        "longitude": 73.71436,
        "station_type": "fixed",
    },
    "DC Office Gujrat": {
        "api_id": "DC Office Gujrat",
        "display_name": "DC Office Gujrat",
        "city": "Gujrat",
        "district": "Gujrat",
        "latitude": 32.58559,
        "longitude": 74.07833,
        "station_type": "fixed",
    },
    "DC Office Chakwal": {
        "api_id": "DC Office Chakwal",
        "display_name": "DC Office Chakwal",
        "city": "Chakwal",
        "district": "Chakwal",
        "latitude": 32.92564,
        "longitude": 72.80549,
        "station_type": "fixed",
    },
    "DC Office Khanewal": {
        "api_id": "DC Office Khanewal",
        "display_name": "DC Office Khanewal",
        "city": "Khanewal",
        "district": "Khanewal",
        "latitude": 30.30231,
        "longitude": 71.92921,
        "station_type": "fixed",
    },
    "DC Office Muzaffargarh": {
        "api_id": "DC Office Muzaffargarh",
        "display_name": "DC Office Muzaffargarh",
        "city": "Muzaffargarh",
        "district": "Muzaffargarh",
        "latitude": 30.07608,
        "longitude": 71.19038,
        "station_type": "fixed",
    },
    "DC Office Rahim Yar Khan": {
        "api_id": "DC Office Rahim Yar Khan",
        "display_name": "DC Office Rahim Yar Khan",
        "city": "Rahim Yar Khan",
        "district": "Rahim Yar Khan",
        "latitude": 28.42323,
        "longitude": 70.31827,
        "station_type": "fixed",
    },
    "DC Office DG Khan": {
        "api_id": "DC Office DG Khan",
        "display_name": "DC Office DG Khan",
        "city": "DG Khan",
        "district": "DG Khan",
        "latitude": 30.051792633623844,
        "longitude": 70.62966164154528,
        "station_type": "fixed",
    },
    "DC Office Rawalpindi": {
        "api_id": "DC Office Rawalpindi",
        "display_name": "DC Office Rawalpindi",
        "city": "Rawalpindi",
        "district": "Rawalpindi",
        "latitude": 33.58462459856753,
        "longitude": 73.06891569999999,
        "station_type": "fixed",
    },
    "ARID University Rawalpindi": {
        "api_id": "ARID University Rawalpindi",
        "display_name": "ARID University Rawalpindi",
        "city": "Rawalpindi",
        "district": "Rawalpindi",
        "latitude": 33.65061773446243,
        "longitude": 73.08067117116441,
        "station_type": "fixed",
    },
    "Drug Testing Laboratory Rawalpindi": {
        "api_id": "Drug Testing Laboratory Rawalpindi",
        "display_name": "Drug Testing Laboratory Rawalpindi",
        "city": "Rawalpindi",
        "district": "Rawalpindi",
        "latitude": 33.54226391435295,
        "longitude": 73.01392021534237,
        "station_type": "fixed",
    },
}

# Alias map for mobile vans and common display variants
_ALIAS_MAP: Dict[str, str] = {
    "raja jang kasur - mobile 1": "Mobile 1",
    "lathepur lhr - mobile 2": "Mobile 2",
    "wagha border lhr - mobile 3": "Mobile 3",
    "egerton road - mobile 4": "Mobile 4",
    "bhu jandiala kalsan lhr - mobile 5": "Mobile 5",
}


def get_epa_station_info(station_id_or_name: str) -> Optional[Dict[str, Any]]:
    """Resolves station metadata by API ID or display name."""
    clean = str(station_id_or_name).strip()
    if clean in EPA_STATIONS_CATALOG:
        return EPA_STATIONS_CATALOG[clean]

    lower = clean.lower()
    if lower in _ALIAS_MAP:
        return EPA_STATIONS_CATALOG[_ALIAS_MAP[lower]]

    for api_id, info in EPA_STATIONS_CATALOG.items():
        if info["display_name"].lower() == lower:
            return info
        if api_id.lower() == lower:
            return info

    return None


def get_all_epa_stations() -> List[Dict[str, Any]]:
    """Returns list of all 38 official EPA Punjab AQMS stations."""
    return list(EPA_STATIONS_CATALOG.values())


def resolve_district_for_station(station_id_or_name: str) -> str:
    """Returns Punjab district name for station, or 'Lahore' as institutional default."""
    info = get_epa_station_info(station_id_or_name)
    if info:
        return info["district"]
    return "Lahore"


def resolve_station_coords(station_id_or_name: str) -> Optional[tuple[float, float]]:
    """Returns (latitude, longitude) for an official station, or None if unknown."""
    info = get_epa_station_info(station_id_or_name)
    if info:
        return (info["latitude"], info["longitude"])
    return None
