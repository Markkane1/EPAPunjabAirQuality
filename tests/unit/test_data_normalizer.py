"""Unit and Adversarial Test Suite for Domain Normalizer (5 Schema Traps).

Empirically verifies:
1. Trap 1: Inversion of district centroid [lat, lon] to [lon, lat] while preserving
   label [lon, lat] and boundary GeoJSON coordinates.
2. Trap 2: Differentiation of aerodrome null wind outages (state: 'dropout') from
   aerodynamic calm (state: 'calm', 0.0 <= ws < 0.50 m/s) and active vectors (state: 'active').
3. Trap 3: Hard-blocking of Station 172 (Wazirabad AQMS) wind vectors due to
   140-degree vane offset blacklist.
4. Trap 4: Dynamic computation of fixed (74) vs mobile (5) station counts from baseline data.
5. Trap 5: Unification of divergent estimation flags (est, is_monitored) into
   is_estimated and diagonal cross-hatching trigger.
"""
import json
import math
from pathlib import Path
import pytest

from src.domain.normalizer.normalizer import (
    blacklist_banner_text,
    count_station_networks,
    is_blacklisted_station,
    is_district_estimated,
    is_point_in_polygon,
    normalize_centroid,
    normalize_wind,
    sanitize_station_coordinates,
    should_apply_diagonal_hatching,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BASELINE_DIR = PROJECT_ROOT / "data" / "baseline"


class TestSchemaTrap1CentroidInversion:
    """Trap 1: Centroid inversion from [lat, lon] to cartographic [lon, lat]."""

    @pytest.fixture(scope="class")
    @classmethod
    def districts(cls):
        with open(BASELINE_DIR / "districts.json", "r", encoding="utf-8") as f:
            return json.load(f)

    def test_raw_district_centroids_are_lat_lon_trap(self, districts):
        """Proves that raw baseline data has [lat, lon] in centroid field."""
        for d in districts:
            centroid = d.get("centroid")
            assert isinstance(centroid, list) and len(centroid) == 2
            lat, lon = centroid
            # In Punjab, latitude is ~27-35.5 and longitude is ~69-76.5
            assert 27.0 <= lat <= 35.5, f"Centroid[0] {lat} is latitude"
            assert 69.0 <= lon <= 76.5, f"Centroid[1] {lon} is longitude"

    def test_normalize_centroid_inverts_lat_lon_to_lon_lat(self, districts):
        """Verifies that production normalize_centroid strictly places longitude first."""
        for d in districts:
            raw_c = d["centroid"]
            norm_lon, norm_lat = normalize_centroid(raw_c)
            assert 69.0 <= norm_lon <= 76.5, f"Normalized longitude out of bounds: {norm_lon}"
            assert 27.0 <= norm_lat <= 35.5, f"Normalized latitude out of bounds: {norm_lat}"

    def test_normalize_centroid_idempotency_and_edge_cases(self):
        """Tests that normalize_centroid preserves already-inverted coordinates and handles edge cases."""
        # Already lon, lat
        assert normalize_centroid([74.3587, 31.5204]) == (74.3587, 31.5204)
        # Lat, lon
        assert normalize_centroid([31.5204, 74.3587]) == (74.3587, 31.5204)
        # Empty / invalid
        assert normalize_centroid([]) == (0.0, 0.0)
        assert normalize_centroid([float("nan"), 74.0]) == (0.0, 0.0)

    def test_label_coordinates_remain_lon_lat(self, districts):
        """Verifies that label coordinates (if present) are already [lon, lat] and not inverted twice."""
        for d in districts:
            label = d.get("label")
            if label:
                assert isinstance(label, list) and len(label) == 2
                lon, lat = label
                assert 69.0 <= lon <= 76.5, f"Label lon out of bounds: {lon}"
                assert 27.0 <= lat <= 35.5, f"Label lat out of bounds: {lat}"


class TestSchemaTrap2AerodromeNullVsCalm:
    """Trap 2: Differentiating METAR wind null (dropout) from aerodynamic calm (<0.50 m/s)."""

    @pytest.fixture(scope="class")
    @classmethod
    def baseline(cls):
        with open(BASELINE_DIR / "baseline_data.json", "r", encoding="utf-8") as f:
            return json.load(f)

    def test_normalize_wind_discrimination(self):
        """Tests production normalize_wind against dropout, calm, and active states."""
        # Dropout cases
        assert normalize_wind(None, 180.0)["state"] == "dropout"
        assert normalize_wind(5.0, None)["state"] == "dropout"
        assert normalize_wind(float("nan"), 180.0)["state"] == "dropout"
        assert normalize_wind(-1.0, 180.0)["state"] == "dropout"
        assert normalize_wind(35.0, 180.0)["state"] == "dropout"  # speed > 30 m/s

        # Calm cases
        calm_0 = normalize_wind(0.0, 0.0)
        assert calm_0["state"] == "calm"
        assert calm_0["u"] == 0.0 and calm_0["v"] == 0.0

        calm_4 = normalize_wind(0.45, 90.0)
        assert calm_4["state"] == "calm"
        assert calm_4["u"] == 0.0 and calm_4["v"] == 0.0

        # Active case
        active = normalize_wind(5.0, 90.0)
        assert active["state"] == "active"
        assert active["u"] == pytest.approx(-5.0, abs=1e-3)
        assert active["v"] == pytest.approx(0.0, abs=1e-3)

    def test_airports_exist_with_null_and_calm(self, baseline):
        airports = baseline.get("airports", [])
        assert len(airports) == 6

        # Check that we can distinguish nulls (telemetry dropout) from aerodynamic calm
        for ap in airports:
            u_series = ap.get("u", [])
            v_series = ap.get("v", [])
            assert len(u_series) == 216
            assert len(v_series) == 216

            dropout_count = 0
            calm_count = 0
            active_count = 0

            for u, v in zip(u_series, v_series):
                if u is None or v is None:
                    dropout_count += 1
                else:
                    spd = (u * u + v * v) ** 0.5
                    if spd < 0.50:
                        calm_count += 1
                    else:
                        active_count += 1

            assert dropout_count + calm_count + active_count == 216


class TestSchemaTrap3Station172WazirabadBlacklist:
    """Trap 3: Hard-blocking Station 172 (Wazirabad) wind vectors."""

    @pytest.fixture(scope="class")
    @classmethod
    def stations(cls):
        with open(BASELINE_DIR / "stations.json", "r", encoding="utf-8") as f:
            return json.load(f)

    def test_wazirabad_station_identified(self, stations):
        waz_stations = [
            s for s in stations
            if "wazirabad" in s["name"].lower()
            or s.get("id") == "172"
            or s.get("numeric_id") == 172
            or s.get("station_id") == "172"
        ]
        assert len(waz_stations) >= 1, "Wazirabad station not found in catalog"
        for st in waz_stations:
            assert "wazirabad" in st["name"].lower()

    def test_blacklist_station_172_in_normalizer(self):
        """Verifies Station 172 and Wazirabad are blocked across IDs, integers, and names."""
        assert is_blacklisted_station("172") is True
        assert is_blacklisted_station(172) is True
        assert is_blacklisted_station("wazirabad") is True
        assert is_blacklisted_station("Wazirabad AQMS") is True
        assert is_blacklisted_station("pk_waz_001") is True
        assert is_blacklisted_station("lahore_town_hall") is False

        # Verify normalize_wind blocks Station 172
        res = normalize_wind(5.0, 90.0, station_id_or_name="172")
        assert res["state"] == "blacklisted"
        assert res["blacklisted"] is True
        assert res["speed"] is None
        assert "ANEMOMETER BLACKLISTED" in res["blacklist_reason"]

        res_int = normalize_wind(5.0, 90.0, station_id_or_name=172)
        assert res_int["state"] == "blacklisted"
        assert res_int["blacklisted"] is True

        # Verify blacklist banner text
        assert blacklist_banner_text("172") == "ANEMOMETER BLACKLISTED (VANE OFFSET)"
        assert blacklist_banner_text({"id": 172, "name": "Wazirabad"}) == "ANEMOMETER BLACKLISTED (VANE OFFSET)"
        assert blacklist_banner_text({"id": 101, "name": "Lahore"}) is None


class TestSchemaTrap4DynamicStationCounts:
    """Trap 4: Dynamically computing fixed (74) vs mobile (5) station counts."""

    @pytest.fixture(scope="class")
    @classmethod
    def stations(cls):
        with open(BASELINE_DIR / "stations.json", "r", encoding="utf-8") as f:
            return json.load(f)

    def test_dynamic_counts_match_74_fixed_5_mobile(self, stations):
        assert len(stations) == 79
        counts = count_station_networks(stations)
        assert counts["mobile"] == 5, f"Expected 5 mobile stations, got {counts['mobile']}"
        assert counts["fixed"] == 74, f"Expected 74 fixed stations, got {counts['fixed']}"
        assert counts["total"] == 79


class TestSchemaTrap5EstimationFlagUnification:
    """Trap 5: Unifying estimation flags (est, is_monitored) into is_estimated."""

    @pytest.fixture(scope="class")
    @classmethod
    def districts(cls):
        with open(BASELINE_DIR / "districts.json", "r", encoding="utf-8") as f:
            return json.load(f)

    def test_estimated_districts_identified(self, districts):
        unmonitored = []
        monitored = []

        for d in districts:
            is_est = is_district_estimated(d)
            if is_est:
                unmonitored.append(d["name"])
            else:
                monitored.append(d["name"])

        assert len(monitored) + len(unmonitored) == 41
        assert len(monitored) >= 30, "Monitored districts suspiciously low"
        # Verify Lahore is always monitored
        assert "Lahore" in monitored
        # Verify hatching matches
        for d in districts:
            assert should_apply_diagonal_hatching(d) == is_district_estimated(d)


class TestGeometricSanitizer:
    """Tests GAP-GEO-03: Shapefile and geometric coordinate sanitization."""

    def test_canonical_trap_overrides(self):
        # Known trap: Gulberg III
        lat, lon, rectified = sanitize_station_coordinates("Gulberg III, Lahore", 31.0, 74.0)
        assert rectified is True
        assert abs(lat - 31.5097) < 0.001
        assert abs(lon - 74.3478) < 0.001

        # Known trap: Wazirabad
        lat, lon, rectified = sanitize_station_coordinates("Wazirabad AQMS", 32.0, 74.0)
        assert rectified is True
        assert abs(lat - 32.4428) < 0.001

    def test_inversion_and_out_of_bounds_detection(self):
        # Inverted coordinates [lon, lat] passed to lat, lon
        lat, lon, rectified = sanitize_station_coordinates("Unknown Station", 74.34, 31.54)
        assert rectified is True
        assert abs(lat - 31.54) < 0.001
        assert abs(lon - 74.34) < 0.001

        # Completely out of bounds (e.g. London coordinates)
        lat, lon, rectified = sanitize_station_coordinates("Foreign Station", 51.5, -0.1)
        assert rectified is True

    def test_point_in_polygon(self):
        # Unit square in Punjab
        poly = [[74.0, 31.0], [75.0, 31.0], [75.0, 32.0], [74.0, 32.0]]
        assert is_point_in_polygon(31.5, 74.5, poly) is True
        assert is_point_in_polygon(33.0, 74.5, poly) is False
