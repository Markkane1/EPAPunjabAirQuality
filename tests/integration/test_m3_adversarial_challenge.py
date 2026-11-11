"""
Adversarial Challenge & Stress Verification Suite for Milestone M3 Pipeline Modules.
Empirically tests and challenges:
1. METAR parser: weird weather tokens, variable wind (VRB/VRB02KT), missing temp/dewp, extreme wind gusts, temporal window edges.
2. SYNOP decoder: truncated telegrams, missing groups, negative temperatures, Section 3 max-temp isolation, wind unit indicators.
3. CSV adapter: multi-pollutant row merging (Town Hall PM2.5 and PM10 on separate lines merging to statutory composite PEPC AQI),
   PM10-dominant merging, asymmetric wind and QC flag consolidation, timezone harmonization, and multi-station isolation.
"""
from datetime import datetime, timezone, timedelta
import io
import math
import pytest

from src.domain.math.pepc_aqi import pepc_calculate_aqi, pepc_composite_aqi
from src.domain.schemas.measurement import NormalizedObservation
from src.pipelines.metar import MetarIngestionWorker
from src.pipelines.synop import SynopIngestionWorker
from src.pipelines.csv_adapter import UserCSVIngestionAdapter


# ==============================================================================
# 1. METAR PARSER ADVERSARIAL CHALLENGE
# ==============================================================================

class TestMetarAdversarialChallenge:
    """Stress-tests MetarIngestionWorker against hostile, malformed, and boundary inputs."""

    def test_variable_wind_vrb_variations(self):
        """
        Adversarial test: Variable wind variations:
        - wdir='VRB' with valid speed: direction is None, speed retained, u/v is None.
        - wdir='VRB02KT' (unsplit raw token in wdir): direction is None, no exception.
        - wdir='VRB' with calm speed (0.0): speed is 0.0, u=0.0, v=0.0.
        - wdir out of bounds (370 deg or -10 deg): direction is None.
        """
        worker = MetarIngestionWorker()

        # Case 1: Standard VRB with 4 knots
        p1 = [{"icaoId": "OPLA", "obsTime": "2026-11-10T12:00:00Z", "wdir": "VRB", "wspd": 4.0}]
        res1 = worker.parse_and_validate(p1)
        assert len(res1) == 1
        assert res1[0]["wind_direction_deg"] is None
        # 4 knots * 0.514444 = 2.06 m/s
        assert abs(res1[0]["wind_speed_ms"] - 2.06) < 0.02
        assert res1[0]["u"] is None
        assert res1[0]["v"] is None

        # Case 2: Raw string token 'VRB02KT' in wdir
        p2 = [{"icaoId": "OPLA", "obsTime": "2026-11-10T12:00:00Z", "wdir": "VRB02KT", "wspd": 2.0}]
        res2 = worker.parse_and_validate(p2)
        assert len(res2) == 1
        assert res2[0]["wind_direction_deg"] is None
        assert abs(res2[0]["wind_speed_ms"] - 1.03) < 0.02

        # Case 3: VRB with calm wind (0.0 kt)
        p3 = [{"icaoId": "OPLA", "obsTime": "2026-11-10T12:00:00Z", "wdir": "VRB", "wspd": 0.0}]
        res3 = worker.parse_and_validate(p3)
        assert len(res3) == 1
        assert res3[0]["wind_speed_ms"] == 0.0
        assert res3[0]["u"] == 0.0
        assert res3[0]["v"] == 0.0

        # Case 4: Out of range directions (380 deg, -15 deg)
        p4 = [
            {"icaoId": "OPST", "obsTime": "2026-11-10T12:00:00Z", "wdir": 380, "wspd": 5.0},
            {"icaoId": "OPFA", "obsTime": "2026-11-10T12:00:00Z", "wdir": -15, "wspd": 5.0},
        ]
        res4 = worker.parse_and_validate(p4)
        for r in res4:
            assert r["wind_direction_deg"] is None
            assert r["wind_speed_ms"] > 0.0

    def test_weird_weather_tokens_stress(self):
        """
        Adversarial test: Decodes complex, compound, and unmapped present weather tokens:
        - Compound: '+TSRA BR HZ', 'VCFG BLDU', '-RA FG'
        - Unmapped / rare: 'SN', 'GR', 'SQ', 'NSW', 'CAVOK', '///'
        - Corrupted / None: None, empty string, integer
        """
        worker = MetarIngestionWorker()

        # Compound weather: TS + RA + BR + HZ
        p_compound = [{
            "icaoId": "OPLA",
            "obsTime": "2026-11-10T12:00:00Z",
            "wxString": "+TSRA BR HZ",
            "wspd": 10.0,
            "wdir": 180,
        }]
        res_compound = worker.parse_and_validate(p_compound)[0]
        decoded = res_compound["weather_decoded"]
        assert "Thunderstorm" in decoded
        assert "Rain" in decoded
        assert "Mist" in decoded
        assert "Haze" in decoded
        assert res_compound["wx_tokens"] == "+TSRA BR HZ"

        # Vicinity Fog (VCFG) and Blowing Dust (BLDU)
        p_vcfg = [{
            "icaoId": "OPMT",
            "obsTime": "2026-11-10T12:00:00Z",
            "wxString": "VCFG BLDU",
            "wspd": 5.0,
            "wdir": 270,
        }]
        res_vcfg = worker.parse_and_validate(p_vcfg)[0]
        assert "Fog" in res_vcfg["weather_decoded"]
        assert "Dust" in res_vcfg["weather_decoded"]

        # Unmapped / international tokens: 'SN' (snow), 'GR' (hail), 'CAVOK', '///'
        p_unmapped = [{
            "icaoId": "OPIS",
            "obsTime": "2026-11-10T12:00:00Z",
            "wxString": "SN GR CAVOK ///",
            "wspd": 6.0,
            "wdir": 360,
        }]
        res_unmapped = worker.parse_and_validate(p_unmapped)[0]
        # Should not crash, unmapped tokens produce empty decoded list
        assert isinstance(res_unmapped["weather_decoded"], list)
        assert res_unmapped["wx_tokens"] == "SN GR CAVOK ///"

        # None / empty weather string
        p_none = [
            {"icaoId": "OPRN", "obsTime": "2026-11-10T12:00:00Z", "wxString": None},
            {"icaoId": "OPBW", "obsTime": "2026-11-10T12:00:00Z", "wxString": ""},
        ]
        res_none = worker.parse_and_validate(p_none)
        assert len(res_none) == 2
        for r in res_none:
            assert r["weather_decoded"] == []
            assert r["wx_tokens"] == ""

    def test_missing_temperature_dewpoint_and_coordinates(self):
        """
        Adversarial test: METAR report completely omitting temperature, dewpoint,
        latitude, longitude, or visibility.
        """
        worker = MetarIngestionWorker()
        p = [{
            "icaoId": "VIAR",
            "obsTime": "2026-11-10T12:00:00Z",
            "wspd": 5.0,
            "wdir": 90,
            # No lat, lon, visib, rawOb, temp, dewp
        }]
        res = worker.parse_and_validate(p)
        assert len(res) == 1
        r = res[0]
        assert r["icaoId"] == "VIAR"
        assert r["latitude"] is None
        assert r["longitude"] is None
        assert r["visibility_m"] is None
        assert r["wind_speed_ms"] == round(5.0 * 0.514444, 2)
        assert r["wind_direction_deg"] == 90.0

    def test_extreme_wind_gusts_and_kinematics(self):
        """
        Adversarial test: Extreme wind gusts (e.g. 85 kt tropical cyclone / severe squall),
        calm gusts, negative gusts, and corrupt gust types.
        """
        worker = MetarIngestionWorker()
        p = [
            # 85 knot extreme gust
            {"icaoId": "OPLA", "obsTime": "2026-11-10T12:00:00Z", "wspd": 45.0, "wdir": 270, "wgst": 85.0},
            # 0.0 knot gust
            {"icaoId": "OPFA", "obsTime": "2026-11-10T12:00:00Z", "wspd": 10.0, "wdir": 180, "wgst": 0.0},
            # Negative gust (sensor malfunction)
            {"icaoId": "OPMT", "obsTime": "2026-11-10T12:00:00Z", "wspd": 10.0, "wdir": 180, "wgst": -15.0},
            # Corrupted gust string
            {"icaoId": "OPST", "obsTime": "2026-11-10T12:00:00Z", "wspd": 10.0, "wdir": 180, "wgst": "50G75KT"},
        ]
        res = worker.parse_and_validate(p)
        # 85 kt -> 43.73 m/s
        opla = next(r for r in res if r["icaoId"] == "OPLA")
        assert opla["wind_gust_ms"] == round(85.0 * 0.514444, 2)

        opfa = next(r for r in res if r["icaoId"] == "OPFA")
        assert opfa["wind_gust_ms"] == 0.0

        opmt = next(r for r in res if r["icaoId"] == "OPMT")
        assert opmt["wind_gust_ms"] is None

        opst = next(r for r in res if r["icaoId"] == "OPST")
        assert opst["wind_gust_ms"] is None

    def test_temporal_window_selection_boundaries(self):
        """
        Adversarial test: Temporal alignment window [-35 min, +25 min] around target time:
        - Multiple reports for same airport: selects closest within window.
        - Reports outside window: selects chronologically nearest rather than dropping.
        """
        worker = MetarIngestionWorker()
        target_t = datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)

        # 3 reports for OPLA: 11:20 (outside -40m), 11:45 (inside -15m), 12:10 (inside +10m)
        reports = [
            {"icaoId": "OPLA", "obsTime": "2026-11-10T11:20:00Z", "wspd": 3.0, "wdir": 90},
            {"icaoId": "OPLA", "obsTime": "2026-11-10T11:45:00Z", "wspd": 5.0, "wdir": 90},
            {"icaoId": "OPLA", "obsTime": "2026-11-10T12:10:00Z", "wspd": 7.0, "wdir": 90},
        ]
        res = worker.parse_and_validate(reports, target_timestamp=target_t)
        assert len(res) == 1
        # 12:10 is 10 min away, 11:45 is 15 min away -> 12:10 must be selected
        assert res[0]["obsTime"] == "2026-11-10T12:10:00Z"
        assert abs(res[0]["wind_speed_ms"] - round(7.0 * 0.514444, 2)) < 0.01

        # All reports outside [-35m, +25m]: e.g. 10:00 and 14:00 -> picks 10:00 (2h away vs 2h away)
        far_reports = [
            {"icaoId": "OPDG", "obsTime": "2026-11-10T10:30:00Z", "wspd": 8.0, "wdir": 180},
            {"icaoId": "OPDG", "obsTime": "2026-11-10T14:30:00Z", "wspd": 12.0, "wdir": 180},
        ]
        res_far = worker.parse_and_validate(far_reports, target_timestamp=target_t)
        assert len(res_far) == 1
        # 10:30 is 1.5h away, 14:30 is 2.5h away -> picks 10:30
        assert res_far[0]["obsTime"] == "2026-11-10T10:30:00Z"

    def test_metar_all_12_aerodromes_full_coverage(self):
        """
        Adversarial test: Comprehensive coverage of all 12 aerodromes:
        - OPLA: Allama Iqbal Intl, Lahore
        - OPFA: Faisalabad Intl
        - OPMT: Multan Intl
        - OPST: Sialkot Intl
        - OPIS: Islamabad Intl
        - OPRN: Benazir Bhutto (PAF Chaklala), Rawalpindi
        - OPRK: Shaikh Zayed Intl, Rahim Yar Khan
        - OPBW: Bahawalpur
        - OPDG: Dera Ghazi Khan
        - OPSR: PAF Base Mushaf, Sargodha
        - OPMI: PAF Base Mianwali
        - VIAR: Sri Guru Ram Dass Jee Intl, Amritsar (Key transboundary anchor)
        Verify that a single batch containing all 12 aerodromes produces exactly 12 validated observations.
        """
        worker = MetarIngestionWorker()
        target_time = datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)
        all_12_icaos = [
            "OPLA", "OPFA", "OPMT", "OPST", "OPIS", "OPRN",
            "OPRK", "OPBW", "OPDG", "OPSR", "OPMI", "VIAR"
        ]

        batch_payload = [
            {
                "icaoId": icao,
                "station_id": icao,
                "name": f"Station {icao}",
                "obsTime": "2026-11-10T12:00:00Z",
                "lat": 31.0 + idx * 0.1,
                "lon": 74.0 + idx * 0.1,
                "wdir": (idx * 30) % 360,
                "wspd": 5.0 + idx,
                "visib": 6.0,
                "rawOb": f"METAR {icao} 101200Z {(idx * 30) % 360:03d}{int(5.0 + idx):02d}KT 5000 HZ NSC 24/16 Q1013=",
            }
            for idx, icao in enumerate(all_12_icaos)
        ]

        results = worker.parse_and_validate(batch_payload, target_timestamp=target_time)
        assert len(results) == 12, f"Expected 12 parsed aerodromes, got {len(results)}"

        parsed_icaos = {r["icaoId"] for r in results}
        assert parsed_icaos == set(all_12_icaos), f"Missing aerodromes: {set(all_12_icaos) - parsed_icaos}"

        # Verify key individual aerodrome characteristics
        viar = next(r for r in results if r["icaoId"] == "VIAR")
        assert viar["source"] == "noaa_awc_metar"
        assert viar["station_id"] == "VIAR"

        oprn = next(r for r in results if r["icaoId"] == "OPRN")
        assert oprn["station_id"] == "OPRN"

        opsr = next(r for r in results if r["icaoId"] == "OPSR")
        assert opsr["station_id"] == "OPSR"

        opmi = next(r for r in results if r["icaoId"] == "OPMI")
        assert opmi["station_id"] == "OPMI"

    def test_metar_metric_visibility_regex_override(self):
        """
        Adversarial test: Metric visibility regex \\s(\\d{4})\\s override in rawOb:
        - Case 1: Statute miles visib=10.0 (sm -> 16093.4 m), rawOb contains ' 0800 ' (800m fog in Lahore).
          Must override visibility_m to 800.0.
        - Case 2: Statute miles visib=6.0 (sm -> 9656.1 m), rawOb contains ' 3500 '.
          Must override visibility_m to 3500.0.
        - Case 3: Metric visibility maximum ' 9999 ' (>=10km) in rawOb.
          Must override visibility_m to 9999.0.
        - Case 4: No metric 4-digit token in rawOb (' 10SM '), statute miles conversion is retained.
        - Case 5: 5-digit number in rawOb (' 10000 ') or prefixed (' Q1013 ') does not trigger override.
        """
        worker = MetarIngestionWorker()

        # Case 1: visib=10.0 sm (16093.4 m), rawOb with ' 0800 ' (800m fog)
        item1 = {
            "icaoId": "OPLA",
            "obsTime": "2026-11-10T12:00:00Z",
            "visib": 10.0,
            "rawOb": "METAR OPLA 101200Z 09004KT 0800 FG NSC 20/18 Q1015=",
        }
        res1 = worker._parse_single_metar(item1)
        assert res1 is not None
        assert res1["raw_visibility_sm"] == 10.0
        assert res1["visibility_m"] == 800.0, f"Expected metric override 800.0, got {res1['visibility_m']}"

        # Case 2: visib=6.0 sm (9656.1 m), rawOb with ' 3500 ' (3500m haze)
        item2 = {
            "icaoId": "OPFA",
            "obsTime": "2026-11-10T12:00:00Z",
            "visib": 6.0,
            "rawOb": "METAR OPFA 101200Z 18006KT 3500 HZ NSC 25/14 Q1013=",
        }
        res2 = worker._parse_single_metar(item2)
        assert res2 is not None
        assert res2["visibility_m"] == 3500.0

        # Case 3: Metric visibility maximum ' 9999 ' (>=10km)
        item3 = {
            "icaoId": "OPMT",
            "obsTime": "2026-11-10T12:00:00Z",
            "visib": 10.0,
            "rawOb": "METAR OPMT 101200Z 27008KT 9999 NSC 28/12 Q1012=",
        }
        res3 = worker._parse_single_metar(item3)
        assert res3 is not None
        assert res3["visibility_m"] == 9999.0

        # Case 4: No metric 4-digit token in rawOb, statute-to-meters conversion is retained
        item4 = {
            "icaoId": "OPIS",
            "obsTime": "2026-11-10T12:00:00Z",
            "visib": 5.0,
            "rawOb": "METAR OPIS 101200Z 36005KT 5SM CLR 22/10 Q1016=",
        }
        res4 = worker._parse_single_metar(item4)
        assert res4 is not None
        expected_m = round(5.0 * 1609.344, 1)
        assert res4["visibility_m"] == expected_m

        # Case 5: 5-digit number in rawOb (' 10000 ') does not match \\s(\\d{4})\\s
        item5 = {
            "icaoId": "OPST",
            "obsTime": "2026-11-10T12:00:00Z",
            "visib": 4.0,
            "rawOb": "METAR OPST 101200Z 05003KT 10000 HZ NSC 21/15 Q1014=",
        }
        res5 = worker._parse_single_metar(item5)
        assert res5 is not None
        assert res5["visibility_m"] == round(4.0 * 1609.344, 1)

    def test_metar_all_seven_present_weather_tokens(self):
        """
        Adversarial test: Explicit decoding of all 7 present weather tokens:
        - FU -> Smoke
        - HZ -> Haze
        - BR -> Mist
        - FG -> Fog
        - DU -> Dust
        - RA -> Rain
        - TS -> Thunderstorm
        Verifies individual token mapping and complete compound aggregation.
        """
        worker = MetarIngestionWorker()
        token_expectations = {
            "FU": "Smoke",
            "HZ": "Haze",
            "BR": "Mist",
            "FG": "Fog",
            "DU": "Dust",
            "RA": "Rain",
            "TS": "Thunderstorm",
        }

        # Test each token individually
        for token, expected_desc in token_expectations.items():
            item = {
                "icaoId": "OPLA",
                "obsTime": "2026-11-10T12:00:00Z",
                "wxString": token,
            }
            parsed = worker._parse_single_metar(item)
            assert parsed is not None
            assert expected_desc in parsed["weather_decoded"], f"Token {token} failed to decode to {expected_desc}"
            assert len(parsed["weather_decoded"]) == 1

        # Test all 7 combined in a single compound string
        compound_string = "+TSRA FG BR HZ FU DU"
        item_all = {
            "icaoId": "OPLA",
            "obsTime": "2026-11-10T12:00:00Z",
            "wxString": compound_string,
        }
        parsed_all = worker._parse_single_metar(item_all)
        assert parsed_all is not None
        assert len(parsed_all["weather_decoded"]) == 7
        for expected_desc in token_expectations.values():
            assert expected_desc in parsed_all["weather_decoded"]

    def test_metar_strict_temporal_window_exact_edges(self):
        """
        Adversarial test: Strict edge boundaries for temporal alignment window [-35 min, +25 min]:
        - Target: 12:00:00 UTC
        - Exact boundary: 11:25:00 UTC (-35 min) -> valid candidate.
        - Exact boundary: 12:25:00 UTC (+25 min) -> valid candidate.
        - Excluded boundary: 11:24:59 UTC (-35m 1s) -> outside valid candidate window.
        - Excluded boundary: 12:25:01 UTC (+25m 1s) -> outside valid candidate window.
        - Preference: within valid candidates, closest report is selected.
        """
        worker = MetarIngestionWorker()
        target_t = datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)

        # Reports at exact window edges vs just outside
        reports = [
            {"icaoId": "OPLA", "obsTime": "2026-11-10T11:24:59Z", "wspd": 1.0, "wdir": 90},  # -35m 1s
            {"icaoId": "OPLA", "obsTime": "2026-11-10T11:25:00Z", "wspd": 2.0, "wdir": 90},  # Exactly -35m
            {"icaoId": "OPLA", "obsTime": "2026-11-10T12:25:00Z", "wspd": 3.0, "wdir": 90},  # Exactly +25m
            {"icaoId": "OPLA", "obsTime": "2026-11-10T12:25:01Z", "wspd": 4.0, "wdir": 90},  # +25m 1s
        ]

        # 12:25:00 is 25 min away (1500s), 11:25:00 is 35 min away (2100s).
        # Both are valid, but 12:25:00 is closer to top of hour (25m < 35m).
        res = worker.parse_and_validate(reports, target_timestamp=target_t)
        assert len(res) == 1
        assert res[0]["obsTime"] == "2026-11-10T12:25:00Z"
        assert res[0]["wind_speed_ms"] == round(3.0 * 0.514444, 2)

        # Test when only -35m exact edge and outside reports exist
        edge_reports = [
            {"icaoId": "OPLA", "obsTime": "2026-11-10T11:24:59Z", "wspd": 1.0, "wdir": 90},  # -35m 1s
            {"icaoId": "OPLA", "obsTime": "2026-11-10T11:25:00Z", "wspd": 2.0, "wdir": 90},  # Exactly -35m
        ]
        res_edge = worker.parse_and_validate(edge_reports, target_timestamp=target_t)
        assert len(res_edge) == 1
        assert res_edge[0]["obsTime"] == "2026-11-10T11:25:00Z"



# ==============================================================================
# 2. SYNOP DECODER ADVERSARIAL CHALLENGE
# ==============================================================================

class TestSynopAdversarialChallenge:
    """Stress-tests SynopIngestionWorker FM-12 telegraphic decoder against corrupted inputs."""

    def test_truncated_and_corrupt_telegrams(self):
        """
        Adversarial test: Severely truncated or corrupt SYNOP telegram lines:
        - Single token 'AAXX'
        - Truncated before station ID 'AAXX 09184'
        - Truncated before wind group 'AAXX 09184 41640 11560'
        - Non-AAXX lines ('BBXX...', 'METAR...')
        - Empty and whitespace lines
        All must safely return None without throwing IndexError or unhandled exceptions.
        """
        worker = SynopIngestionWorker()

        truncated_cases = [
            "AAXX",
            "AAXX=",
            "AAXX 09184",
            "AAXX 09184=",
            "AAXX 09184 41640",
            "AAXX 09184 41640 11560",
            "BBXX 09184 41640 11560 81802 10224 20182=",
            "METAR OPLA 101200Z 09010KT=",
            "",
            "   \n   \t  ",
            "AAXX invalid_tokens_everywhere 41640",
        ]
        for line in truncated_cases:
            decoded = worker.decode_synop_line(line)
            assert decoded is None, f"Expected None for truncated line: '{line}'"

        # Multi-line batch with all truncated lines must return empty list
        batch_res = worker.parse_and_validate("\n".join(truncated_cases))
        assert batch_res == []

    def test_missing_groups_graceful_handling(self):
        """
        Adversarial test: Telegrams missing Section 1 groups:
        - Missing temperature group 1snTTT -> temperature_c is None.
        - Missing dewpoint group 2snTdTdTd -> dewpoint_c is None.
        - Minimal telegram ending right after wind group.
        - Telegram with Section 3 (333) immediately following wind group.
        """
        worker = SynopIngestionWorker()

        # Minimal telegram: Header, Station 41640, iRixhVV, Nddff, then '='
        # iw = 1 (m/s), dd = 18 (180 deg), ff = 05 (5 m/s)
        min_line = "AAXX 09181 41640 11560 81805="
        dec_min = worker.decode_synop_line(min_line)
        assert dec_min is not None
        assert dec_min["wmo_id"] == "41640"
        assert dec_min["wind_speed_ms"] == 5.0
        assert dec_min["wind_direction_deg"] == 180.0
        assert dec_min["temperature_c"] is None
        assert dec_min["dewpoint_c"] is None

        # Telegram with temperature but missing dewpoint:
        # T = +24.5C (10245)
        temp_only = "AAXX 09181 41640 11560 81805 10245 40160 333="
        dec_t = worker.decode_synop_line(temp_only)
        assert dec_t is not None
        assert dec_t["temperature_c"] == 24.5
        assert dec_t["dewpoint_c"] is None

        # Telegram with dewpoint but missing temperature:
        # Td = +16.0C (20160)
        dewp_only = "AAXX 09181 41640 11560 81805 20160 40160 333="
        dec_d = worker.decode_synop_line(dewp_only)
        assert dec_d is not None
        assert dec_d["temperature_c"] is None
        assert dec_d["dewpoint_c"] == 16.0

    def test_negative_temperatures_and_dewpoints(self):
        """
        Adversarial test: Decoding negative temperatures and dewpoints (WMO sn=1):
        - Sub-zero temperature: 11054 -> -5.4 C
        - Fractional negative: 11005 -> -0.5 C
        - Extreme frost: 11250 -> -25.0 C
        - Negative dewpoint: 21085 -> -8.5 C
        - Zero threshold: 10000 -> 0.0 C
        - Scorching summer heat: 10468 -> +46.8 C
        """
        worker = SynopIngestionWorker()

        # Winter frost: T = -5.4 C (11054), Td = -8.5 C (21085)
        frost_line = "AAXX 09181 41571 11560 83602 11054 21085 40160 333="
        dec_frost = worker.decode_synop_line(frost_line)
        assert dec_frost is not None
        assert dec_frost["wmo_id"] == "41571"  # Islamabad
        assert dec_frost["temperature_c"] == -5.4
        assert dec_frost["dewpoint_c"] == -8.5

        # Sub-zero fractional: T = -0.5 C (11005), Td = -1.2 C (21012)
        subzero_line = "AAXX 09181 41598 11560 83602 11005 21012 40160 333="
        dec_subzero = worker.decode_synop_line(subzero_line)
        assert dec_subzero is not None
        assert dec_subzero["temperature_c"] == -0.5
        assert dec_subzero["dewpoint_c"] == -1.2

        # Freezing point: T = 0.0 C (10000)
        zero_line = "AAXX 09181 41600 11560 83602 10000 20000 40160 333="
        dec_zero = worker.decode_synop_line(zero_line)
        assert dec_zero is not None
        assert dec_zero["temperature_c"] == 0.0
        assert dec_zero["dewpoint_c"] == 0.0

        # Scorching heat in Multan: T = +46.8 C (10468), Td = +22.0 C (20220)
        heat_line = "AAXX 09181 41675 11560 81805 10468 20220 40160 333="
        dec_heat = worker.decode_synop_line(heat_line)
        assert dec_heat is not None
        assert dec_heat["temperature_c"] == 46.8
        assert dec_heat["dewpoint_c"] == 22.0

    def test_section_3_temperature_isolation(self):
        """
        Adversarial test: Section 3 (333) contains group 1snTxTxTx (maximum temperature).
        When Section 1 has NO temperature group, verify that Section 3's 1snTxTxTx
        is NOT erroneously parsed as the Section 1 dry bulb temperature.
        """
        worker = SynopIngestionWorker()
        # Section 1 has no 1snTTT group. Section 3 contains 10425 (max temp +42.5C)
        line = "AAXX 09184 41640 11560 81802 40162 57018 333 10425 55300 20000="
        decoded = worker.decode_synop_line(line)
        assert decoded is not None
        # Section 1 temperature MUST be None (not 42.5 from Section 3)
        assert decoded["temperature_c"] is None

    def test_synop_wind_speed_overflow_and_units(self):
        """
        Adversarial test:
        - iw=1 (m/s) vs iw=4 (knots).
        - Calm wind dd=00 -> speed=0, dir=None, u=0, v=0.
        - Variable wind dd=99 -> dir=None.
        - Speed overflow ff=99 with Section 3 auxiliary group 00fff (e.g. 00125 -> 125 kt/ms).
        """
        worker = SynopIngestionWorker()

        # Case 1: iw=4 (knots) with dd=27 (270 deg), ff=99 (overflow) -> Section 3 has 00115 (115 kt)
        overflow_line = "AAXX 09184 41640 11560 82799 10250 20180 333 00115 55300="
        dec_overflow = worker.decode_synop_line(overflow_line)
        assert dec_overflow is not None
        assert dec_overflow["wind_direction_deg"] == 270.0
        # 115 knots * 0.514444 = 59.16 m/s
        assert abs(dec_overflow["wind_speed_ms"] - round(115 * 0.514444, 2)) < 0.05
        # u pointing east (u > 0) for wind from 270 deg (West)
        assert dec_overflow["u"] > 0.0

        # Case 2: Calm wind dd=00, ff=00
        calm_line = "AAXX 09181 41640 11560 80000 10250 20180 333="
        dec_calm = worker.decode_synop_line(calm_line)
        assert dec_calm is not None
        assert dec_calm["wind_speed_ms"] == 0.0
        assert dec_calm["wind_direction_deg"] is None
        assert dec_calm["u"] == 0.0
        assert dec_calm["v"] == 0.0

        # Case 3: Variable wind dd=99, ff=04 with iw=1 (m/s)
        vrb_line = "AAXX 09181 41640 11560 89904 10250 20180 333="
        dec_vrb = worker.decode_synop_line(vrb_line)
        assert dec_vrb is not None
        assert dec_vrb["wind_direction_deg"] is None
        assert dec_vrb["wind_speed_ms"] == 4.0
        assert dec_vrb["u"] is None
        assert dec_vrb["v"] is None

    def test_synop_token_collision_indicator_group_and_cloud_group(self):
        """
        Adversarial test: Token collision resistance:
        - Section 1 indicator group iRixhVV (token 3) which commonly begins with '1' (e.g. '11560', '12562')
          must NOT collide with temperature group 1snTTT.
        - Cloud group Nddff beginning with '1' (N=1 okta cloud cover, e.g. '11805')
          must NOT collide with temperature group 1snTTT.
        - Positive temperature 10224 (+22.4 C) and negative temperature 11050 (-5.0 C) must decode accurately.
        - When temperature group 1snTTT is omitted, iRixhVV='11560' must NOT be parsed as temperature.
        """
        worker = SynopIngestionWorker()

        # Case 1: iRixhVV starts with '1' (11560), cloud starts with '1' (11802 -> N=1 okta), temp is positive +22.4C (10224)
        # Slices sec1_tokens[2:] must skip both 11560 and 11802 to hit 10224.
        line_pos = "AAXX 09184 41640 11560 11802 10224 20182 40162 333="
        dec_pos = worker.decode_synop_line(line_pos)
        assert dec_pos is not None
        assert dec_pos["temperature_c"] == 22.4, f"Expected +22.4, got {dec_pos['temperature_c']}"
        assert dec_pos["dewpoint_c"] == 18.2
        assert dec_pos["wind_direction_deg"] == 180.0
        assert dec_pos["wind_speed_ms"] == round(2.0 * 0.514444, 2)

        # Case 2: iRixhVV starts with '1' (11560), temp is negative -5.0C (11050)
        # Must parse -5.0C, NOT -56.0C from 11560!
        line_neg = "AAXX 09184 41571 11560 83604 11050 21080 40160 333="
        dec_neg = worker.decode_synop_line(line_neg)
        assert dec_neg is not None
        assert dec_neg["temperature_c"] == -5.0, f"Expected -5.0, got {dec_neg['temperature_c']}"
        assert dec_neg["dewpoint_c"] == -8.0

        # Case 3: iRixhVV is '11560', but 1snTTT is completely missing.
        # Temperature MUST be None, proving iRixhVV is never erroneously interpreted as temperature.
        line_no_temp = "AAXX 09184 41640 11560 81802 20182 40162 333="
        dec_no_temp = worker.decode_synop_line(line_no_temp)
        assert dec_no_temp is not None
        assert dec_no_temp["temperature_c"] is None, f"Expected None, got {dec_no_temp['temperature_c']}"
        assert dec_no_temp["dewpoint_c"] == 18.2

    def test_synop_wind_all_iw_unit_indicators(self):
        """
        Adversarial test: Verification of wind speed unit conversion across all 4 WMO iw values:
        - iw=0: m/s (estimated) -> native m/s, conversion factor 1.0
        - iw=1: m/s (anemometer) -> native m/s, conversion factor 1.0
        - iw=3: knots (estimated) -> knots-to-m/s factor 0.514444
        - iw=4: knots (anemometer) -> knots-to-m/s factor 0.514444
        """
        worker = SynopIngestionWorker()

        # iw = 0 (m/s estimated): ff = 12 -> 12.0 m/s
        line_iw0 = "AAXX 09180 41640 11560 81812 10250 20180 333="
        dec_iw0 = worker.decode_synop_line(line_iw0)
        assert dec_iw0 is not None
        assert dec_iw0["wind_speed_ms"] == 12.0

        # iw = 1 (m/s measured): ff = 12 -> 12.0 m/s
        line_iw1 = "AAXX 09181 41640 11560 81812 10250 20180 333="
        dec_iw1 = worker.decode_synop_line(line_iw1)
        assert dec_iw1 is not None
        assert dec_iw1["wind_speed_ms"] == 12.0

        # iw = 3 (knots estimated): ff = 12 -> 12 * 0.514444 = 6.17 m/s
        line_iw3 = "AAXX 09183 41640 11560 81812 10250 20180 333="
        dec_iw3 = worker.decode_synop_line(line_iw3)
        assert dec_iw3 is not None
        assert dec_iw3["wind_speed_ms"] == round(12.0 * 0.514444, 2)
        assert dec_iw3["wind_speed_ms"] == 6.17

        # iw = 4 (knots measured): ff = 12 -> 12 * 0.514444 = 6.17 m/s
        line_iw4 = "AAXX 09184 41640 11560 81812 10250 20180 333="
        dec_iw4 = worker.decode_synop_line(line_iw4)
        assert dec_iw4 is not None
        assert dec_iw4["wind_speed_ms"] == round(12.0 * 0.514444, 2)
        assert dec_iw4["wind_speed_ms"] == 6.17

    def test_synop_storm_speeds_auxiliary_group_in_section_3(self):
        """
        Adversarial test: Storm speeds (>99 kt / >99 m/s) with Section 3 auxiliary group 00fff:
        - When ff=99 and Section 3 has '00130' (130 kt) with iw=4 -> round(130 * 0.514444, 2) = 66.88 m/s.
        - When ff=99 and Section 3 has '00055' (55 m/s) with iw=1 -> 55.0 m/s.
        - When ff=45 (<99) and Section 3 has '00130' -> auxiliary group is ignored, ff=45 is retained.
        - When ff=99 and Section 3 has no auxiliary group -> ff=99 is retained.
        """
        worker = SynopIngestionWorker()

        # 130 knots storm with iw=4 (knots)
        line_storm_kt = "AAXX 09184 41640 11560 82799 10200 20150 333 00130 55300="
        dec_storm_kt = worker.decode_synop_line(line_storm_kt)
        assert dec_storm_kt is not None
        assert dec_storm_kt["wind_direction_deg"] == 270.0
        assert dec_storm_kt["wind_speed_ms"] == round(130 * 0.514444, 2)
        assert dec_storm_kt["wind_speed_ms"] == 66.88

        # 55 m/s storm with iw=1 (m/s)
        line_storm_ms = "AAXX 09181 41640 11560 81899 10200 20150 333 00055 55300="
        dec_storm_ms = worker.decode_synop_line(line_storm_ms)
        assert dec_storm_ms is not None
        assert dec_storm_ms["wind_direction_deg"] == 180.0
        assert dec_storm_ms["wind_speed_ms"] == 55.0

        # ff < 99 (e.g. ff=45 kt) should NOT trigger auxiliary override even if 00130 is present
        line_normal = "AAXX 09184 41640 11560 82745 10200 20150 333 00130 55300="
        dec_normal = worker.decode_synop_line(line_normal)
        assert dec_normal is not None
        assert dec_normal["wind_speed_ms"] == round(45 * 0.514444, 2)
        assert dec_normal["wind_speed_ms"] == 23.15

        # ff == 99 without auxiliary group in Section 3 -> fallback to 99 kt
        line_no_aux = "AAXX 09184 41640 11560 82799 10200 20150 333 55300="
        dec_no_aux = worker.decode_synop_line(line_no_aux)
        assert dec_no_aux is not None
        assert dec_no_aux["wind_speed_ms"] == round(99 * 0.514444, 2)
        assert dec_no_aux["wind_speed_ms"] == 50.93



# ==============================================================================
# 3. CSV ADAPTER MULTI-POLLUTANT ROW MERGING ADVERSARIAL CHALLENGE
# ==============================================================================

class TestCSVAdapterAdversarialChallenge:
    """Stress-tests UserCSVIngestionAdapter multi-pollutant row merging and composite AQI."""

    def test_csv_town_hall_pm25_pm10_row_merging(self):
        """
        Adversarial test: Town Hall PM2.5 and PM10 reported on separate lines
        sharing the same station_id ('PK_LHR_001') and timestamp:
        - Row 1: PM2.5 = 185.4 ug/m3 (Sub-index AQI = 241)
        - Row 2: PM10 = 290.1 ug/m3 (Sub-index AQI = 170)
        - Merged observation MUST contain both pm25_qc and pm10_qc.
        - Composite PEPC AQI MUST equal max(241, 170) = 241.
        """
        csv_data = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value,wind_speed,wind_direction\n"
            "2026-11-10T12:00:00Z,PK_LHR_001,Town Hall,Lahore,31.5600,74.3100,pm25,185.4,2.5,90.0\n"
            "2026-11-10T12:00:00Z,PK_LHR_001,Town Hall,Lahore,31.5600,74.3100,pm10,290.1,2.5,90.0\n"
        )
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(csv_data)

        assert res.status == "success"
        assert res.total_rows == 2
        assert res.valid_count == 2
        assert res.quarantine_count == 0

        # Execute multi-pollutant merge
        merged = res.get_merged_observations()
        assert len(merged) == 1, f"Expected exactly 1 merged observation, got {len(merged)}"

        obs = merged[0]
        assert obs.station_id == "PK_LHR_001"
        assert obs.station_name == "Town Hall"
        assert obs.district == "Lahore"
        assert obs.pm25_qc == 185.4
        assert obs.pm10_qc == 290.1

        # Verify individual and composite sub-indices
        pm25_aqi = pepc_calculate_aqi("PM2.5", 185.4)
        pm10_aqi = pepc_calculate_aqi("PM10", 290.1)
        assert pm25_aqi == 241
        assert pm10_aqi == 170
        assert obs.pepc_aqi == 241
        assert obs.pepc_aqi == pepc_composite_aqi(pm25_aqi, pm10_aqi)

    def test_csv_pm10_dominant_composite_merging(self):
        """
        Adversarial test: PM10 sub-index dominates PM2.5 sub-index:
        - Row 1: PM2.5 = 20.0 ug/m3 (AQI = 63, Moderate/Satisfactory)
        - Row 2: PM10 = 400.0 ug/m3 (AQI = 250, Unhealthy)
        - Composite AQI MUST equal 250 (PM10 dominant).
        """
        csv_data = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            "2026-11-10T12:00:00Z,PK_MLT_001,Multan Dust Node,Multan,30.1984,71.4687,pm25,20.0\n"
            "2026-11-10T12:00:00Z,PK_MLT_001,Multan Dust Node,Multan,30.1984,71.4687,pm10,400.0\n"
        )
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(csv_data)
        merged = res.get_merged_observations()

        assert len(merged) == 1
        obs = merged[0]
        assert obs.pm25_qc == 20.0
        assert obs.pm10_qc == 400.0
        assert obs.pepc_aqi == 250
        assert obs.pepc_aqi == max(pepc_calculate_aqi("PM2.5", 20.0), pepc_calculate_aqi("PM10", 400.0))

    def test_csv_multi_pollutant_full_suite_merging(self):
        """
        Adversarial test: Merging 6 statutory pollutants across 6 separate rows
        for the same station and timestamp: PM2.5, PM10, NO2, SO2, CO, O3.
        """
        csv_data = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            "2026-11-10T12:00:00Z,PK_FSD_001,Faisalabad Core,Faisalabad,31.4187,73.0791,pm25,120.0\n"
            "2026-11-10T12:00:00Z,PK_FSD_001,Faisalabad Core,Faisalabad,31.4187,73.0791,pm10,210.0\n"
            "2026-11-10T12:00:00Z,PK_FSD_001,Faisalabad Core,Faisalabad,31.4187,73.0791,no2,65.0\n"
            "2026-11-10T12:00:00Z,PK_FSD_001,Faisalabad Core,Faisalabad,31.4187,73.0791,so2,85.0\n"
            "2026-11-10T12:00:00Z,PK_FSD_001,Faisalabad Core,Faisalabad,31.4187,73.0791,co,4.5\n"
            "2026-11-10T12:00:00Z,PK_FSD_001,Faisalabad Core,Faisalabad,31.4187,73.0791,o3,95.0\n"
        )
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(csv_data)
        assert res.valid_count == 6

        merged = res.get_merged_observations()
        assert len(merged) == 1
        obs = merged[0]
        assert obs.pm25_qc == 120.0
        assert obs.pm10_qc == 210.0
        assert obs.no2_qc == 65.0
        assert obs.so2_qc == 85.0
        assert obs.co_qc == 4.5
        assert obs.o3_qc == 95.0

    def test_csv_asymmetric_wind_merging(self):
        """
        Adversarial test: Row 1 has pollutant PM2.5 with NO wind data.
        Row 2 has pollutant PM10 with valid wind data (speed=4.5 m/s, dir=180 deg).
        Merged observation MUST retain both pollutants and the wind parameters.
        """
        csv_data = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value,wind_speed,wind_direction\n"
            "2026-11-10T12:00:00Z,PK_SKT_001,Sialkot Node,Sialkot,32.4945,74.5372,pm25,110.0,,\n"
            "2026-11-10T12:00:00Z,PK_SKT_001,Sialkot Node,Sialkot,32.4945,74.5372,pm10,195.0,4.5,180.0\n"
        )
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(csv_data)
        merged = res.get_merged_observations()

        assert len(merged) == 1
        obs = merged[0]
        assert obs.pm25_qc == 110.0
        assert obs.pm10_qc == 195.0
        assert obs.wind_speed_ms == 4.5
        assert obs.wind_direction_deg == 180.0
        # Wind vector pointing North for wind FROM 180 deg (South)
        assert obs.u_vector_ms == 0.0
        assert obs.v_vector_ms == 4.5

    def test_csv_asymmetric_qc_flags_merging(self):
        """
        Adversarial test:
        Row 1 has PM2.5 = 1250.0 (triggers QC_EXCEEDANCE_EXTREME).
        Row 2 has PM10 = 250.0 (normal).
        Station is Wazirabad AQMS (triggers WIND_BLACKLIST_WAZIRABAD).
        Merged observation MUST consolidate both QC flags without duplicate entries.
        """
        csv_data = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value,wind_speed,wind_direction\n"
            "2026-11-10T12:00:00Z,PK_WAZ_001,Wazirabad AQMS,Gujranwala,32.4428,74.1197,pm25,1250.0,3.0,90.0\n"
            "2026-11-10T12:00:00Z,PK_WAZ_001,Wazirabad AQMS,Gujranwala,32.4428,74.1197,pm10,250.0,3.0,90.0\n"
        )
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(csv_data)
        merged = res.get_merged_observations()

        assert len(merged) == 1
        obs = merged[0]
        assert "QC_EXCEEDANCE_EXTREME" in obs.qc_flags
        assert "WIND_BLACKLIST_WAZIRABAD" in obs.qc_flags
        # Verify deduplication
        assert obs.qc_flags.count("WIND_BLACKLIST_WAZIRABAD") == 1
        assert obs.wind_speed_ms is None

    def test_csv_timezone_and_timestamp_format_harmonization(self):
        """
        Adversarial test:
        Row 1: ISO timestamp with explicit UTC 'Z' ('2026-11-10T07:00:00Z')
        Row 2: Naive local PKT timestamp ('2026-11-10 12:00') -> PKT is UTC+5, so 12:00 PKT == 07:00 UTC.
        Both rows MUST resolve to identical UTC instant and merge into 1 observation.
        """
        csv_data = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            "2026-11-10T07:00:00Z,PK_RWP_001,Rawalpindi Hub,Rawalpindi,33.5651,73.0169,pm25,95.0\n"
            "2026-11-10 12:00,PK_RWP_001,Rawalpindi Hub,Rawalpindi,33.5651,73.0169,pm10,160.0\n"
        )
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(csv_data)
        assert res.valid_count == 2

        merged = res.get_merged_observations()
        assert len(merged) == 1
        obs = merged[0]
        assert obs.pm25_qc == 95.0
        assert obs.pm10_qc == 160.0
        expected_dt = datetime(2026, 11, 10, 7, 0, 0, tzinfo=timezone.utc)
        assert obs.timestamp == expected_dt

    def test_csv_zero_and_negative_row_purging_during_merge(self):
        """
        Adversarial test: Multi-pollutant set containing Step 0 invalid sensor readings:
        Row 1: PM2.5 = 145.0 (valid)
        Row 2: PM10 = 0.0 (zero concentration -> Step 0 purge)
        Row 3: NO2 = -15.0 (negative sensor glitch -> Step 0 purge)
        Merged observation MUST contain only valid PM2.5, with PM10 and NO2 as None.
        """
        csv_data = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            "2026-11-10T12:00:00Z,PK_GUJ_001,Gujrat Station,Gujrat,32.5742,74.0754,pm25,145.0\n"
            "2026-11-10T12:00:00Z,PK_GUJ_001,Gujrat Station,Gujrat,32.5742,74.0754,pm10,0.0\n"
            "2026-11-10T12:00:00Z,PK_GUJ_001,Gujrat Station,Gujrat,32.5742,74.0754,no2,-15.0\n"
        )
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(csv_data)

        # 1 valid row, 2 quarantined rows
        assert res.valid_count == 1
        assert res.quarantine_count == 2
        assert res.status == "partial_quarantine"

        merged = res.get_merged_observations()
        assert len(merged) == 1
        obs = merged[0]
        assert obs.pm25_qc == 145.0
        assert obs.pm10_qc is None
        assert obs.no2_qc is None

    def test_csv_multi_station_multi_hour_isolation(self):
        """
        Adversarial test: 3 stations across 2 timestamps, each reporting PM2.5 and PM10 (12 rows).
        Merging MUST produce exactly 6 isolated observations (3 stations * 2 timestamps)
        with zero cross-station or cross-temporal crosstalk.
        """
        stations = [
            ("PK_01", "Lahore Station", "Lahore", 31.5204, 74.3587),
            ("PK_02", "Faisalabad Station", "Faisalabad", 31.4187, 73.0791),
            ("PK_03", "Multan Station", "Multan", 30.1984, 71.4687),
        ]
        timestamps = ["2026-11-10T12:00:00Z", "2026-11-10T13:00:00Z"]

        rows = ["timestamp,station_id,station_name,district,latitude,longitude,pollutant,value"]
        for ts in timestamps:
            for sid, sname, dist, lat, lon in stations:
                rows.append(f"{ts},{sid},{sname},{dist},{lat},{lon},pm25,120.0")
                rows.append(f"{ts},{sid},{sname},{dist},{lat},{lon},pm10,220.0")

        csv_content = "\n".join(rows) + "\n"
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(csv_content)
        assert res.total_rows == 12
        assert res.valid_count == 12

        merged = res.get_merged_observations()
        assert len(merged) == 6

        # Verify each of the 6 combinations exists with both PM2.5 and PM10 populated
        for ts_str in timestamps:
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            for sid, sname, dist, _, _ in stations:
                matching = [m for m in merged if m.station_id == sid and m.timestamp == dt]
                assert len(matching) == 1
                m = matching[0]
                assert m.pm25_qc == 120.0
                assert m.pm10_qc == 220.0
                assert m.pepc_aqi == pepc_composite_aqi(
                    pepc_calculate_aqi("PM2.5", 120.0),
                    pepc_calculate_aqi("PM10", 220.0),
                )

    def test_csv_multi_pollutant_prompt_specific_pair_merging(self):
        """
        Adversarial test: Explicit pair specified in dispatch:
        - Ingest multiple rows sharing the same (station_id, timestamp) with different pollutants:
          * Row 1: PM2.5 = 120.0 ug/m3
          * Row 2: PM10 = 250.0 ug/m3
        - Verify get_merged_observations() merges them into a single coherent Observation entity with both values populated.
        - Verify PEPC statutory composite AQI recalculation (max(I_PM2.5, I_PM10)):
          * I_PM2.5(120.0): In range (70, 140], (BP_low=70, BP_high=140, I_low=150, I_high=200):
            ((200 - 150)/(140 - 70))*(120 - 70) + 150 = round(35.714 + 150) = 186.
          * I_PM10(250.0): In range (150, 250], exactly at breakpoint BP_3 = 250.0:
            ((150 - 100)/(250 - 150))*(250 - 150) + 100 = 150.
          * Composite PEPC AQI: max(186, 150) = 186.
        """
        csv_data = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            "2026-11-10T12:00:00Z,PK_TEST_01,Lahore Center,Lahore,31.5500,74.3300,pm25,120.0\n"
            "2026-11-10T12:00:00Z,PK_TEST_01,Lahore Center,Lahore,31.5500,74.3300,pm10,250.0\n"
        )
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(csv_data)

        assert res.status == "success"
        assert res.valid_count == 2
        assert res.quarantine_count == 0

        merged = res.get_merged_observations()
        assert len(merged) == 1, f"Expected 1 consolidated observation, got {len(merged)}"

        obs = merged[0]
        # Verify single coherent Observation entity with both values populated
        assert obs.station_id == "PK_TEST_01"
        assert obs.station_name == "Lahore Center"
        assert obs.district == "Lahore"
        assert obs.latitude == 31.5500
        assert obs.longitude == 74.3300
        assert obs.pm25_qc == 120.0
        assert obs.pm10_qc == 250.0

        # Verify individual sub-indices and composite recalculation
        sub_pm25 = pepc_calculate_aqi("PM2.5", 120.0)
        sub_pm10 = pepc_calculate_aqi("PM10", 250.0)
        assert sub_pm25 == 186
        assert sub_pm10 == 150

        # Statutory composite AQI = max(186, 150) = 186
        assert obs.pepc_aqi == 186
        assert obs.pepc_aqi == max(sub_pm25, sub_pm10)
        assert obs.pepc_aqi == pepc_composite_aqi(sub_pm25, sub_pm10)

    def test_csv_multi_pollutant_gaseous_coexistence_does_not_corrupt_composite(self):
        """
        Adversarial test: Gaseous pollutants (NO2, SO2, CO, O3) reported alongside PM2.5 and PM10:
        - Gaseous sub-indices (e.g. NO2=180 -> AQI=200) must NOT override or distort the
          statutory particulate composite rule AQI_composite = max(I_PM2.5, I_PM10).
        """
        csv_data = (
            "timestamp,station_id,station_name,district,latitude,longitude,pollutant,value\n"
            "2026-11-10T12:00:00Z,PK_TEST_02,Multan Industrial,Multan,30.2000,71.4500,pm25,30.0\n"
            "2026-11-10T12:00:00Z,PK_TEST_02,Multan Industrial,Multan,30.2000,71.4500,pm10,60.0\n"
            "2026-11-10T12:00:00Z,PK_TEST_02,Multan Industrial,Multan,30.2000,71.4500,no2,175.0\n"
        )
        adapter = UserCSVIngestionAdapter()
        res = adapter.ingest_csv(csv_data)
        assert res.valid_count == 3

        merged = res.get_merged_observations()
        assert len(merged) == 1

        obs = merged[0]
        assert obs.pm25_qc == 30.0
        assert obs.pm10_qc == 60.0
        assert obs.no2_qc == 175.0

        # PM2.5 sub-index: 30.0 in (15, 35] -> ((100-50)/(35-15))*(30-15) + 50 = 88
        # PM10 sub-index: 60.0 in (0, 75] -> (50/75)*60 = 40
        # NO2 sub-index: 175.0 in (130, 180] -> ((200-150)/(180-130))*(175-130) + 150 = 195
        # Composite PEPC AQI is strictly max(I_PM2.5, I_PM10) = max(88, 40) = 88
        assert obs.pepc_aqi == 88

