"""
Statutory Graded Emergency Action Policy Engine.
Evaluates multi-tier regulatory action alerts under the Punjab Environmental Protection Act
and Smog Emergency Mitigation Framework.
Adheres to System Specification Domain 1 (GAP-REG-01).
"""
from typing import Any, Dict, List, Optional

# Alert Level Definitions
ALERT_LEVEL_NORMAL: int = 0
ALERT_LEVEL_ADVISORY: int = 1
ALERT_LEVEL_UNHEALTHY: int = 2
ALERT_LEVEL_SEVERE: int = 3
ALERT_LEVEL_HAZARDOUS: int = 4
ALERT_LEVEL_EMERGENCY: int = 5

ALERT_NAMES: Dict[int, str] = {
    ALERT_LEVEL_NORMAL: "Level 0: Routine Monitoring",
    ALERT_LEVEL_ADVISORY: "Level 1: Sensitive Health Advisory",
    ALERT_LEVEL_UNHEALTHY: "Level 2: Precautionary Yellow Alert",
    ALERT_LEVEL_SEVERE: "Level 3: Heightened Orange Alert",
    ALERT_LEVEL_HAZARDOUS: "Level 4: Hazardous Red Emergency",
    ALERT_LEVEL_EMERGENCY: "Level 5: Critical Crisis Lockdown",
}

ALERT_COLORS: Dict[int, str] = {
    ALERT_LEVEL_NORMAL: "#00B050",     # Green
    ALERT_LEVEL_ADVISORY: "#FFFF00",   # Yellow
    ALERT_LEVEL_UNHEALTHY: "#ED7D31", # Orange
    ALERT_LEVEL_SEVERE: "#FF0000",    # Red
    ALERT_LEVEL_HAZARDOUS: "#7030A0", # Purple
    ALERT_LEVEL_EMERGENCY: "#C00000", # Dark Red / Burgundy
}

STATUTORY_ACTIONS: Dict[int, List[str]] = {
    ALERT_LEVEL_NORMAL: [
        "Continuous 24/7 environmental station telemetry monitoring.",
        "Routine municipal mechanized street sweeping.",
    ],
    ALERT_LEVEL_ADVISORY: [
        "Public health advisory issued for children, elderly, and respiratory patients.",
        "Mandatory water sprinkling at active construction sites to suppress dust.",
        "Voluntary reduction in non-essential personal vehicular travel.",
    ],
    ALERT_LEVEL_UNHEALTHY: [
        "Public N95 mask advisory recommended for all outdoor activities.",
        "Anti-idling enforcement squads deployed at educational and transit choke points.",
        "Intensified industrial inspections for visible stack opacity exceedances.",
        "Prohibition of open municipal waste and leaf burning under Section 16 PEPA 1997.",
    ],
    ALERT_LEVEL_SEVERE: [
        "Primary school outdoor sports banned; morning shifts adjusted.",
        "Heavy diesel transport (3+ axles) restricted on urban arterial roads from 06:00 to 22:00 PKT.",
        "Immediate shutdown of un-scrubbed steel re-rolling and secondary smelting furnaces.",
        "Enhanced police deployment enforcing Section 144 against crop stubble burning.",
    ],
    ALERT_LEVEL_HAZARDOUS: [
        "Primary and middle schools transitioned to 100% online/hybrid attendance.",
        "Commercial markets and shopping plazas mandated to close early at 20:00 PKT.",
        "50% mandatory work-from-home rotation for public and private sector offices.",
        "Complete operational shutdown of traditional Bull's Trench brick kilns.",
        "Deployment of high-pressure anti-smog misting cannons along central corridors.",
    ],
    ALERT_LEVEL_EMERGENCY: [
        "Statutory odd-even vehicular movement rationing enforced across metropolitan centers.",
        "Total prohibition of commercial heavy freight entry into city centers.",
        "Emergency triage wards and oxygen backup mobilized at all tertiary government hospitals.",
        "Total shutdown of polluting industries in identified smog hotspot industrial clusters.",
        "Drone-based aerial thermal surveillance over agricultural stubble and kiln belts.",
    ],
}


def classify_alert_level(aqi: float) -> int:
    """
    Classifies AQI into statutory graded alert levels:
        AQI <= 100: Level 0 (Normal)
        100 < AQI <= 150: Level 1 (Advisory)
        150 < AQI <= 200: Level 2 (Unhealthy)
        200 < AQI <= 300: Level 3 (Severe)
        300 < AQI <= 400: Level 4 (Hazardous)
        AQI > 400: Level 5 (Emergency Crisis)
    """
    v = max(0.0, float(aqi))
    if v <= 100.0:
        return ALERT_LEVEL_NORMAL
    elif v <= 150.0:
        return ALERT_LEVEL_ADVISORY
    elif v <= 200.0:
        return ALERT_LEVEL_UNHEALTHY
    elif v <= 300.0:
        return ALERT_LEVEL_SEVERE
    elif v <= 400.0:
        return ALERT_LEVEL_HAZARDOUS
    else:
        return ALERT_LEVEL_EMERGENCY


def evaluate_district_emergency_actions(
    aqi: float, district_name: str, pm25: Optional[float] = None
) -> Dict[str, Any]:
    """
    Evaluates statutory emergency actions for a specific district.
    """
    alert_lvl = classify_alert_level(aqi)
    return {
        "district": district_name,
        "aqi": round(float(aqi), 1),
        "pm25": round(float(pm25), 1) if pm25 is not None else None,
        "alert_level": alert_lvl,
        "alert_name": ALERT_NAMES[alert_lvl],
        "alert_color": ALERT_COLORS[alert_lvl],
        "is_emergency_triggered": alert_lvl >= ALERT_LEVEL_SEVERE,
        "is_school_closure_mandated": alert_lvl >= ALERT_LEVEL_HAZARDOUS,
        "is_market_curfew_mandated": alert_lvl >= ALERT_LEVEL_HAZARDOUS,
        "is_odd_even_mandated": alert_lvl >= ALERT_LEVEL_EMERGENCY,
        "mandatory_actions": STATUTORY_ACTIONS[alert_lvl],
    }


def evaluate_provincial_emergency_status(
    district_aqi_map: Dict[str, float]
) -> Dict[str, Any]:
    """
    Aggregates provincial emergency status across all reporting districts.
    """
    if not district_aqi_map:
        return {
            "provincial_mean_aqi": 0.0,
            "max_aqi": 0.0,
            "max_aqi_district": "",
            "districts_in_emergency": [],
            "districts_in_hazardous": [],
            "districts_in_severe": [],
            "overall_provincial_alert_level": 0,
            "overall_alert_name": ALERT_NAMES[0],
            "total_districts_evaluated": 0,
        }

    evaluations: List[Dict[str, Any]] = []
    severe_dists: List[str] = []
    hazardous_dists: List[str] = []
    emergency_dists: List[str] = []

    total_aqi = 0.0
    max_aqi = -1.0
    max_dist = ""

    for dname, aqi_val in district_aqi_map.items():
        v = float(aqi_val)
        total_aqi += v
        if v > max_aqi:
            max_aqi = v
            max_dist = dname

        eval_res = evaluate_district_emergency_actions(v, dname)
        evaluations.append(eval_res)

        lvl = eval_res["alert_level"]
        if lvl >= ALERT_LEVEL_EMERGENCY:
            emergency_dists.append(dname)
        elif lvl >= ALERT_LEVEL_HAZARDOUS:
            hazardous_dists.append(dname)
        elif lvl >= ALERT_LEVEL_SEVERE:
            severe_dists.append(dname)

    mean_aqi = total_aqi / len(district_aqi_map)
    provincial_lvl = classify_alert_level(mean_aqi)

    return {
        "provincial_mean_aqi": round(mean_aqi, 1),
        "max_aqi": round(max_aqi, 1),
        "max_aqi_district": max_dist,
        "districts_in_emergency": emergency_dists,
        "districts_in_hazardous": hazardous_dists,
        "districts_in_severe": severe_dists,
        "overall_provincial_alert_level": provincial_lvl,
        "overall_alert_name": ALERT_NAMES[provincial_lvl],
        "total_districts_evaluated": len(district_aqi_map),
        "district_evaluations": evaluations,
    }
