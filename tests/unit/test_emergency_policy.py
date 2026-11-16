"""
Unit tests for Domain 1 (GAP-REG-01): Statutory Graded Emergency Action Policy Engine.
Verifies alert thresholds, mandated mitigations, school/market curfews, and provincial aggregation.
"""
import pytest

from src.domain.math.policy import (
    classify_alert_level,
    evaluate_district_emergency_actions,
    evaluate_provincial_emergency_status,
    ALERT_LEVEL_NORMAL,
    ALERT_LEVEL_ADVISORY,
    ALERT_LEVEL_UNHEALTHY,
    ALERT_LEVEL_SEVERE,
    ALERT_LEVEL_HAZARDOUS,
    ALERT_LEVEL_EMERGENCY,
    ALERT_NAMES,
    ALERT_COLORS,
    STATUTORY_ACTIONS,
)


class TestEmergencyPolicyEngine:
    """Verifies that statutory PEPC alert levels and mandated actions match specifications."""

    def test_alert_level_classification_boundaries(self):
        # Level 0: <= 100
        assert classify_alert_level(0.0) == ALERT_LEVEL_NORMAL
        assert classify_alert_level(50.0) == ALERT_LEVEL_NORMAL
        assert classify_alert_level(100.0) == ALERT_LEVEL_NORMAL

        # Level 1: 101 - 150
        assert classify_alert_level(100.1) == ALERT_LEVEL_ADVISORY
        assert classify_alert_level(150.0) == ALERT_LEVEL_ADVISORY

        # Level 2: 151 - 200
        assert classify_alert_level(150.1) == ALERT_LEVEL_UNHEALTHY
        assert classify_alert_level(200.0) == ALERT_LEVEL_UNHEALTHY

        # Level 3: 201 - 300
        assert classify_alert_level(200.1) == ALERT_LEVEL_SEVERE
        assert classify_alert_level(300.0) == ALERT_LEVEL_SEVERE

        # Level 4: 301 - 400
        assert classify_alert_level(300.1) == ALERT_LEVEL_HAZARDOUS
        assert classify_alert_level(400.0) == ALERT_LEVEL_HAZARDOUS

        # Level 5: > 400
        assert classify_alert_level(400.1) == ALERT_LEVEL_EMERGENCY
        assert classify_alert_level(850.0) == ALERT_LEVEL_EMERGENCY

    def test_district_emergency_action_triggers(self):
        # Normal district
        eval_norm = evaluate_district_emergency_actions(85.0, "Rawalpindi")
        assert eval_norm["alert_level"] == ALERT_LEVEL_NORMAL
        assert eval_norm["is_emergency_triggered"] is False
        assert eval_norm["is_school_closure_mandated"] is False
        assert eval_norm["is_odd_even_mandated"] is False

        # Hazardous district (e.g. Lahore in crisis episode, AQI 350)
        eval_haz = evaluate_district_emergency_actions(350.0, "Lahore", pm25=300.0)
        assert eval_haz["alert_level"] == ALERT_LEVEL_HAZARDOUS
        assert eval_haz["is_emergency_triggered"] is True
        assert eval_haz["is_school_closure_mandated"] is True
        assert eval_haz["is_market_curfew_mandated"] is True
        assert eval_haz["is_odd_even_mandated"] is False
        assert any("Bull's Trench" in act for act in eval_haz["mandatory_actions"])

        # Crisis district (AQI 450)
        eval_crisis = evaluate_district_emergency_actions(450.0, "Kasur", pm25=420.0)
        assert eval_crisis["alert_level"] == ALERT_LEVEL_EMERGENCY
        assert eval_crisis["is_odd_even_mandated"] is True
        assert any("odd-even" in act for act in eval_crisis["mandatory_actions"])

    def test_provincial_emergency_aggregation(self):
        data = {
            "Lahore": 450.0,      # Emergency
            "Kasur": 350.0,       # Hazardous
            "Gujranwala": 250.0,  # Severe
            "Faisalabad": 180.0,  # Unhealthy
            "Rawalpindi": 80.0,   # Normal
        }
        res = evaluate_provincial_emergency_status(data)
        assert res["total_districts_evaluated"] == 5
        assert res["max_aqi"] == 450.0
        assert res["max_aqi_district"] == "Lahore"
        assert "Lahore" in res["districts_in_emergency"]
        assert "Kasur" in res["districts_in_hazardous"]
        assert "Gujranwala" in res["districts_in_severe"]
        # Mean = (450 + 350 + 250 + 180 + 80) / 5 = 262.0 -> Level 3 (Severe)
        assert res["overall_provincial_alert_level"] == ALERT_LEVEL_SEVERE
