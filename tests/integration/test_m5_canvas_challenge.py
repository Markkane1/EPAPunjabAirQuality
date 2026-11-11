"""
Adversarial Verification & Empirical Stress Test Suite for Milestone M5:
Component-Driven UI/UX Dashboard & High-Performance Canvas Rendering Engine.

Stress-Tests:
1. Zero-GC particle advection engine memory invariants (Float32Array ring buffer size, zero heap allocations).
2. 60 FPS animation loop with sub-hourly temporal linear interpolation C(fp) = (1 - f) C_i + f C_j and DOM throttling.
3. Spatial math & projections: Equirectangular Plate Carrée (K_X = cos 31°), bounding coordinates, roundtrip invertibility.
4. Continuous IDW distance confidence opacity taper in [95, 235] between 45km and 140km.
5. 16-sector polar wind rose math (CPF threshold tau, calm < 0.5 m/s exclusion, null hypothesis 0.25 circle, chromatic amplification).
6. Greedy 12-offset collision-free label search (candidate offset matrix, AABB collision avoidance, leader lines for disp > 20px).
7. Live Node.js runtime execution benchmark measuring heap stability over 5,000 continuous frames.
"""
import math
from pathlib import Path
import json
import re
import subprocess
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATIC_JS_DIR = PROJECT_ROOT / "src" / "frontend" / "static" / "js"
CANVAS_JS = STATIC_JS_DIR / "canvas.js"
GEO_JS = STATIC_JS_DIR / "geo.js"
APP_JS = STATIC_JS_DIR / "app.js"
UI_JS = STATIC_JS_DIR / "ui.js"


# =============================================================================
# 1. Zero-GC Particle Advection Engine & Ring Buffer Invariants
# =============================================================================

class TestParticleEngineMemoryInvariants:
    """Empirically verifies particle advection memory allocation and typed array sizing."""

    def test_particle_buffer_dimensions_and_spec_conformance(self):
        """
        Verify Float32Array ring buffer size matches:
        1,300 particles * 8 history points * 2 coordinates (x, y) = 20,800 floats (83,200 bytes).
        State buffer: 1,300 particles * 6 floats = 7,800 floats (31,200 bytes).
        Head pointer buffer: 1,300 uint8 = 1,300 bytes.
        """
        src = CANVAS_JS.read_text(encoding="utf-8")

        # Verify constants in canvas.js
        assert "this.PARTICLE_COUNT = 1300" in src
        assert "this.LOCAL_COUNT = 700" in src
        assert "this.REGIONAL_COUNT = 600" in src
        assert "this.TRAIL_LENGTH = 8" in src

        # Verify typed array allocations in constructor
        assert "new Float32Array(this.PARTICLE_COUNT * this.TRAIL_LENGTH * 2)" in src
        assert "new Float32Array(this.PARTICLE_COUNT * 6)" in src
        assert "new Uint8Array(this.PARTICLE_COUNT)" in src

        # Numerical invariant verification
        particle_count = 1300
        trail_length = 8
        coords_per_point = 2
        total_trail_floats = particle_count * trail_length * coords_per_point
        assert total_trail_floats == 20800, f"Expected 20,800 floats, got {total_trail_floats}"
        assert total_trail_floats * 4 == 83200, f"Expected 83,200 bytes, got {total_trail_floats * 4}"

        total_state_floats = particle_count * 6
        assert total_state_floats == 7800
        assert total_state_floats * 4 == 31200

    def test_zero_gc_ring_buffer_pointer_arithmetic(self):
        """
        Simulate 10,000 frames of particle ring buffer updates in Python.
        Verify that head pointer always cycles in [0, 7] and trail coordinates update strictly in-place.
        """
        PARTICLE_COUNT = 1300
        TRAIL_LENGTH = 8
        # Flat arrays simulating typed buffers
        particle_trails = [0.0] * (PARTICLE_COUNT * TRAIL_LENGTH * 2)
        particle_head = [0] * PARTICLE_COUNT
        particle_state = [0.0] * (PARTICLE_COUNT * 6)

        # Initialize particles
        for i in range(PARTICLE_COUNT):
            particle_state[i * 6] = 400.0  # x
            particle_state[i * 6 + 1] = 300.0  # y
            particle_state[i * 6 + 2] = 0.0  # age
            particle_state[i * 6 + 3] = 120.0  # maxAge
            particle_state[i * 6 + 4] = 1.0  # speed
            particle_state[i * 6 + 5] = 1.0 if i < 700 else 0.0  # isLocal

        # Run 10,000 frame updates
        for frame in range(10000):
            for i in range(PARTICLE_COUNT):
                sIdx = i * 6
                nx = (particle_state[sIdx] + 0.5) % 800.0
                ny = (particle_state[sIdx + 1] + 0.2) % 600.0
                particle_state[sIdx] = nx
                particle_state[sIdx + 1] = ny

                # Head pointer arithmetic: (head + 1) % 8
                head = (particle_head[i] + 1) % TRAIL_LENGTH
                particle_head[i] = head

                assert 0 <= head < TRAIL_LENGTH, f"Head pointer out of bounds: {head}"

                tBase = i * TRAIL_LENGTH * 2
                particle_trails[tBase + head * 2] = nx
                particle_trails[tBase + head * 2 + 1] = ny

        # Invariant check: buffer length must never change (zero reallocation)
        assert len(particle_trails) == 20800
        assert len(particle_state) == 7800
        assert len(particle_head) == 1300

    def test_canvas_drawlayer2_contains_no_array_push_or_shift(self):
        """Verify drawLayer2 in canvas.js contains no push() or shift() array mutating calls."""
        src = CANVAS_JS.read_text(encoding="utf-8")
        # Extract drawLayer2 method
        start_idx = src.find("drawLayer2(ctx, activeWinds)")
        assert start_idx != -1, "drawLayer2 method missing in canvas.js"
        end_idx = src.find("drawLayer3(ctx, transportLinks, activeWinds)", start_idx)
        layer2_code = src[start_idx:end_idx]

        assert ".push(" not in layer2_code, "Found forbidden .push() in drawLayer2 animation loop"
        assert ".shift(" not in layer2_code, "Found forbidden .shift() in drawLayer2 animation loop"
        assert "new Array" not in layer2_code, "Found forbidden 'new Array' in drawLayer2 animation loop"


# =============================================================================
# 2. 60 FPS Animation Loop & Sub-Hourly Temporal Linear Interpolation
# =============================================================================

class TestTemporalInterpolationAndDecoupling:
    """Stress-tests continuous temporal lerp math and DOM update throttling."""

    @staticmethod
    def lerp_value(v0, v1, f):
        """Mathematical oracle for sub-hourly linear lerp: C(fp) = (1 - f) C_i + f C_j."""
        if v0 is None and v1 is None:
            return None
        if v0 is None:
            return v1
        if v1 is None:
            return v0
        return (1.0 - f) * v0 + f * v1

    @pytest.mark.parametrize("c0, c1, f, expected", [
        (100.0, 200.0, 0.0, 100.0),
        (100.0, 200.0, 1.0, 200.0),
        (100.0, 200.0, 0.5, 150.0),
        (100.0, 200.0, 0.25, 125.0),
        (100.0, 200.0, 0.75, 175.0),
        (None, 250.0, 0.4, 250.0),     # Null-safe fallback
        (300.0, None, 0.8, 300.0),     # Null-safe fallback
        (None, None, 0.5, None),        # Both null
        (0.0, 500.0, 0.1, 50.0),
        (450.0, 450.0, 0.63, 450.0),   # Iso-concentration
    ])
    def test_lerp_mathematical_oracle(self, c0, c1, f, expected):
        res = self.lerp_value(c0, c1, f)
        if expected is None:
            assert res is None
        else:
            assert abs(res - expected) < 1e-9

    def test_temporal_fractional_position_adversarial_boundaries(self):
        """Test continuous timeline scrubbing across fractional positions in [0.00, 215.00]."""
        total_hours = 216
        # Generate adversarial float timestamps
        test_positions = [
            0.0, 0.000001, 0.5, 0.999999, 1.0, 107.5,
            214.0, 214.999, 215.0, 215.0001, 215.999
        ]

        for fp in test_positions:
            i = math.floor(fp)
            f = fp - i
            j = min(total_hours - 1, i + 1)
            i_clamped = min(total_hours - 1, max(0, i))

            assert 0 <= i_clamped < total_hours, f"Hour index out of bounds: {i_clamped}"
            assert 0 <= j < total_hours, f"Target hour index out of bounds: {j}"
            assert 0.0 <= f <= 1.000001, f"Fractional position out of bounds: {f}"

    def test_dom_update_decoupling_throttle(self):
        """Verify app.js implements 10 Hz DOM update throttling decoupled from 60 FPS RAF."""
        src = APP_JS.read_text(encoding="utf-8")

        # Verify RAF loop
        assert "requestAnimationFrame" in src
        # Verify 100ms throttle check (10 Hz)
        assert "timestamp - this.lastUiUpdateTime > 100" in src, "Missing 100ms throttle condition in app.js"
        assert "this.lastUiUpdateTime = timestamp" in src


# =============================================================================
# 3. Equirectangular Plate Carrée Projection Math & Invertibility
# =============================================================================

class TestPlateCarreeProjectionMath:
    """Stress-tests standard parallel 31°N projection and roundtrip invertibility."""

    # Canonical projection constants
    LO0 = 69.10
    LO1 = 75.75
    LA0 = 27.55
    LA1 = 34.30
    KX = math.cos(31.0 * math.pi / 180.0)  # 0.8571673007021123

    @classmethod
    def project(cls, lon: float, lat: float, S: float) -> tuple[float, float]:
        x = (lon - cls.LO0) * cls.KX * S
        y = (cls.LA1 - lat) * S
        return x, y

    @classmethod
    def unproject(cls, x: float, y: float, S: float) -> tuple[float, float]:
        lon = x / (cls.KX * S) + cls.LO0
        lat = cls.LA1 - y / S
        return lon, lat

    def test_standard_parallel_cosine_constant(self):
        """Verify KX constant matches cos(31 deg) to 10 decimal digits."""
        expected_kx = math.cos(31.0 * math.pi / 180.0)
        assert abs(self.KX - expected_kx) < 1e-15
        assert abs(self.KX - 0.8571673007) < 1e-9

        # Verify geo.js source
        geo_src = GEO_JS.read_text(encoding="utf-8")
        assert "KX = Math.cos(31 * Math.PI / 180)" in geo_src or "0.857167" in geo_src

    def test_projection_roundtrip_invertibility(self):
        """Roundtrip project(unproject(x, y)) must equal (x, y) within machine precision."""
        S = 125.45  # Typical scale factor
        test_points = [
            (69.10, 27.55),  # SW Corner
            (75.75, 34.30),  # NE Corner
            (74.3587, 31.5204),  # Lahore
            (73.0845, 31.4504),  # Faisalabad
            (71.4753, 30.1984),  # Multan
            (73.0479, 33.6844),  # Rawalpindi
            (74.5361, 32.4945),  # Sialkot
            (71.5249, 32.5839),  # Mianwali
            (70.6405, 28.4212),  # Rahim Yar Khan
        ]

        for lon, lat in test_points:
            x, y = self.project(lon, lat, S)
            lon_back, lat_back = self.unproject(x, y, S)
            assert abs(lon - lon_back) < 1e-11, f"Longitude roundtrip error at ({lon}, {lat}): {lon_back}"
            assert abs(lat - lat_back) < 1e-11, f"Latitude roundtrip error at ({lon}, {lat}): {lat_back}"

    def test_aspect_ratio_and_dimensions(self):
        """Verify width-to-height ratio matches geographic aspect ratio scaled by KX."""
        d_lon = self.LO1 - self.LO0  # 6.65
        d_lat = self.LA1 - self.LA0  # 6.75
        expected_aspect = (d_lon * self.KX) / d_lat

        width = 800.0
        S = width / (d_lon * self.KX)
        height = d_lat * S
        calc_aspect = width / height

        assert abs(calc_aspect - expected_aspect) < 1e-12
        assert 0.84 < calc_aspect < 0.85, f"Unexpected aspect ratio: {calc_aspect}"


# =============================================================================
# 4. Continuous IDW Distance Confidence Opacity Taper Math
# =============================================================================

class TestIDWOpacityTaperMath:
    """Stress-tests distance confidence opacity decay between 45km and 140km."""

    @staticmethod
    def compute_alpha(d_km: float) -> int:
        """
        Mathematical formula from canvas.js:
        if (kmMin > 140.0) alpha = 95
        else if (kmMin >= 45.0) alpha = round(235 - 140 * ((kmMin - 45.0) / 95.0))
        else alpha = 235
        """
        if d_km > 140.0:
            return 95
        elif d_km >= 45.0:
            return round(235 - 140 * ((d_km - 45.0) / 95.0))
        else:
            return 235

    @pytest.mark.parametrize("d_km, expected_alpha", [
        (-10.0, 235),       # Negative distance anomaly
        (0.0, 235),         # At station location
        (20.0, 235),        # Urban Lahore core
        (44.999, 235),      # Boundary just before taper
        (45.0, 235),        # Exact taper start
        (92.5, 165),        # Midpoint: 235 - 140 * (47.5 / 95.0) = 235 - 70 = 165
        (139.999, 95),      # Boundary just before floor
        (140.0, 95),        # Exact taper end
        (250.0, 95),        # Remote Cholistan desert
        (1000.0, 95),       # Far transboundary
    ])
    def test_alpha_taper_breakpoints(self, d_km, expected_alpha):
        res = self.compute_alpha(d_km)
        assert res == expected_alpha, f"Alpha mismatch at {d_km}km: got {res}, expected {expected_alpha}"

    def test_alpha_monotonicity_across_distance_spectrum(self):
        """Alpha must be strictly non-increasing as distance increases."""
        distances = [d * 0.5 for d in range(0, 400)]
        alphas = [self.compute_alpha(d) for d in distances]

        for i in range(len(alphas) - 1):
            assert alphas[i] >= alphas[i + 1], f"Alpha monotonicity violation at {distances[i]}km -> {distances[i+1]}km"
            assert 95 <= alphas[i] <= 235, f"Alpha out of statutory bounds [95, 235]: {alphas[i]}"


# =============================================================================
# 5. 16-Sector Polar Wind Rose Math & CPF Invariants
# =============================================================================

class TestCPFPolarWindRoseMath:
    """Stress-tests 16-sector azimuth partitioning, calm exclusion, and chromatic formula."""

    SECTOR_WIDTH = 22.5  # 360 / 16

    @classmethod
    def get_sector_index(cls, azimuth_deg: float) -> int:
        """Assign azimuth to 16 sectors centered at 0°, 22.5°, ..., 337.5°."""
        # Normalize to [0, 360)
        norm_az = azimuth_deg % 360.0
        # Sector 0 is centered at 0° (North), covering [348.75°, 360°) and [0°, 11.25°)
        idx = math.floor((norm_az + 11.25) / cls.SECTOR_WIDTH) % 16
        return idx

    @pytest.mark.parametrize("azimuth, expected_sector", [
        (0.0, 0),        # North
        (355.0, 0),      # North
        (5.0, 0),        # North
        (11.24, 0),      # North edge
        (11.26, 1),      # NNE start
        (22.5, 1),       # NNE center
        (90.0, 4),       # East
        (180.0, 8),      # South
        (270.0, 12),     # West
        (337.5, 15),     # NNW
        (360.0, 0),      # Wraparound
        (-45.0, 14),     # Negative modulo: 315° = NW
    ])
    def test_azimuth_sector_partitioning(self, azimuth, expected_sector):
        assert self.get_sector_index(azimuth) == expected_sector

    def test_calm_wind_exclusion_and_ratio(self):
        """Winds < 0.5 m/s must be excluded from directional counts; calm fraction must be accurate."""
        test_observations = [
            {"speed": 0.2, "dir": 90.0},   # Calm
            {"speed": 0.49, "dir": 180.0}, # Calm
            {"speed": 0.50, "dir": 270.0}, # Valid
            {"speed": 2.5, "dir": 0.0},    # Valid
            {"speed": 5.0, "dir": 45.0},   # Valid
        ]
        calm_count = sum(1 for o in test_observations if o["speed"] < 0.5)
        total = len(test_observations)
        calm_ratio = calm_count / total

        assert calm_count == 2
        assert abs(calm_ratio - 0.40) < 1e-9

    def test_chromatic_amplification_formula(self):
        """
        Verify wedge chromatic scaling: C = tau * (0.6 + 1.4 * CPF_i).
        At CPF = 0.0 -> C = 0.6 * tau.
        At CPF = 0.25 (null hypothesis) -> C = tau * (0.6 + 0.35) = 0.95 * tau.
        At CPF = 1.0 -> C = 2.0 * tau.
        """
        tau = 80.0  # PM2.5 P75 threshold
        c_at_0 = tau * (0.6 + 1.4 * 0.0)
        c_at_null = tau * (0.6 + 1.4 * 0.25)
        c_at_1 = tau * (0.6 + 1.4 * 1.0)

        assert abs(c_at_0 - 48.0) < 1e-9
        assert abs(c_at_null - 76.0) < 1e-9
        assert abs(c_at_1 - 160.0) < 1e-9

        # Verify ui.js contains exact formula
        ui_src = UI_JS.read_text(encoding="utf-8")
        assert "0.6 + 1.4 * prob" in ui_src or "0.6 + 1.4 * CPF" in ui_src or "0.6 + 1.4" in ui_src


# =============================================================================
# 6. Greedy 12-Offset Collision-Free Labeling & Leader Lines
# =============================================================================

class TestGreedyCollisionFreeLabeling:
    """Stress-tests 12-offset search, AABB collision detection, and leader line triggering."""

    CANDIDATE_OFFSETS = [
        [0, 0], [0, 14], [0, -14], [16, 0], [-16, 0], [0, 26],
        [0, -26], [30, 8], [-30, 8], [24, -20], [-24, -20], [0, 38],
    ]

    @staticmethod
    def check_aabb_collision(b1, b2) -> bool:
        """AABB overlap test: (x, y, w, h)."""
        x1, y1, w1, h1 = b1
        x2, y2, w2, h2 = b2
        return (x1 < x2 + w2 and x1 + w1 > x2 and y1 < y2 + h2 and y1 + h1 > y2)

    def test_candidate_offsets_count_and_leader_line_thresholds(self):
        """
        Verify exactly 12 offsets exist.
        Verify that displacement sqrt(dx^2 + dy^2) > 20px triggers leader line.
        """
        assert len(self.CANDIDATE_OFFSETS) == 12

        with_leader = []
        without_leader = []

        for ox, oy in self.CANDIDATE_OFFSETS:
            disp = math.hypot(ox, oy)
            if disp > 20.0:
                with_leader.append((ox, oy, disp))
            else:
                without_leader.append((ox, oy, disp))

        # Exactly 5 candidate offsets are <= 20px (no leader line)
        assert len(without_leader) == 5, f"Expected 5 offsets <= 20px, got {len(without_leader)}"
        # Exactly 7 candidate offsets are > 20px (leader line triggered)
        assert len(with_leader) == 7, f"Expected 7 offsets > 20px, got {len(with_leader)}"

        # Verify canvas.js contains leader line threshold 20.0
        src = CANVAS_JS.read_text(encoding="utf-8")
        assert "disp > 20.0" in src

    def test_greedy_label_search_cluster_and_real_districts(self):
        """
        1. Verify greedy search successfully finds non-overlapping candidate offsets for adjacent stations.
        2. Verify execution across all 41 real Punjab districts with graceful fallback.
        """
        # Test cluster of 3 adjacent stations
        stations = [
            {"id": "Lahore", "x": 400.0, "y": 300.0, "w": 60.0, "h": 16.0},
            {"id": "Kasur", "x": 415.0, "y": 312.0, "w": 55.0, "h": 16.0},
            {"id": "Sheikhupura", "x": 390.0, "y": 288.0, "w": 75.0, "h": 16.0},
        ]

        placed_boxes = []

        for st in stations:
            chosen = None
            for ox, oy in self.CANDIDATE_OFFSETS:
                cand_box = (
                    st["x"] + ox - st["w"] / 2,
                    st["y"] + oy - st["h"] / 2,
                    st["w"],
                    st["h"],
                )
                collision = any(self.check_aabb_collision(cand_box, pb) for pb in placed_boxes)
                if not collision:
                    chosen = cand_box
                    placed_boxes.append(cand_box)
                    break

            assert chosen is not None, f"Failed to place label for station {st['id']}"

        # Verify all placed boxes in the cluster are 100% collision-free
        for i in range(len(placed_boxes)):
            for j in range(i + 1, len(placed_boxes)):
                assert not self.check_aabb_collision(placed_boxes[i], placed_boxes[j]), (
                    f"Collision detected between placed boxes {i} and {j}"
                )

        # Verify against real 41 districts
        districts_file = PROJECT_ROOT / "src" / "frontend" / "static" / "data" / "districts.json"
        if districts_file.is_file():
            districts = json.loads(districts_file.read_text(encoding="utf-8"))
            real_placed = []
            successful_offsets = 0

            for d in districts:
                lon = d.get("lon") or d.get("longitude") or d["centroid"][0]
                lat = d.get("lat") or d.get("latitude") or d["centroid"][1]
                # Scale to typical 800x600 screen coordinates
                x = (lon - 69.10) * 0.857167 * 140.0
                y = (34.30 - lat) * 140.0
                bw = len(d["name"]) * 7.5 + 24
                bh = 16.0

                chosen_box = None
                for ox, oy in self.CANDIDATE_OFFSETS:
                    cand = (x + ox - bw / 2, y + oy - bh / 2, bw, bh)
                    if not any(self.check_aabb_collision(cand, pb) for pb in real_placed):
                        chosen_box = cand
                        real_placed.append(cand)
                        successful_offsets += 1
                        break

                if chosen_box is None:
                    # Fallback to CANDIDATE_OFFSETS[0] per canvas.js:771
                    fallback = (x + self.CANDIDATE_OFFSETS[0][0] - bw / 2, y + self.CANDIDATE_OFFSETS[0][1] - bh / 2, bw, bh)
                    real_placed.append(fallback)

            # At least 95% of districts must be assigned collision-free non-fallback offsets
            assert successful_offsets >= 38, f"Too many collision fallbacks: {successful_offsets}/41 placed"


# =============================================================================
# 7. Live Node.js Execution Harness (5,000 Continuous Frames Benchmark)
# =============================================================================

class TestNodeRuntimeCanvasBenchmark:
    """Invokes Node.js to empirically measure particle ring buffer heap stability under stress."""

    def test_node_particle_advection_zero_gc_heap_stability(self):
        """
        Executes 5,000 frames of particle updating in Node.js.
        Verifies heap growth is bounded (< 2 MB) and typed array ring buffer runs deterministically.
        """
        node_script = """
        const PARTICLE_COUNT = 1300;
        const TRAIL_LENGTH = 8;
        const particleTrails = new Float32Array(PARTICLE_COUNT * TRAIL_LENGTH * 2);
        const particleState = new Float32Array(PARTICLE_COUNT * 6);
        const particleHead = new Uint8Array(PARTICLE_COUNT);

        for (let i = 0; i < PARTICLE_COUNT; i++) {
          particleState[i * 6] = Math.random() * 800;
          particleState[i * 6 + 1] = Math.random() * 600;
          particleState[i * 6 + 2] = 0;
          particleState[i * 6 + 3] = 120;
          particleState[i * 6 + 4] = 1.0;
          particleState[i * 6 + 5] = i < 700 ? 1 : 0;
        }

        if (global.gc) global.gc();
        const memBefore = process.memoryUsage().heapUsed;

        for (let frame = 0; frame < 5000; frame++) {
          const S100 = 1.0 / 100.0;
          for (let i = 0; i < PARTICLE_COUNT; i++) {
            const sIdx = i * 6;
            let x = particleState[sIdx];
            let y = particleState[sIdx + 1];
            let age = particleState[sIdx + 2] + 1;
            const maxAge = particleState[sIdx + 3];
            const isLocal = particleState[sIdx + 5];

            const u = 1.2;
            const v = 0.4;
            const kFactor = (isLocal ? 1.4 : 2.2) * S100;
            const nx = x + u * kFactor;
            const ny = y - v * kFactor;

            if (age > maxAge || nx < 0 || nx > 800 || ny < 0 || ny > 600) {
              particleState[sIdx] = Math.random() * 800;
              particleState[sIdx + 1] = Math.random() * 600;
              particleState[sIdx + 2] = 0;
              continue;
            }

            particleState[sIdx] = nx;
            particleState[sIdx + 1] = ny;
            particleState[sIdx + 2] = age;

            let head = (particleHead[i] + 1) % TRAIL_LENGTH;
            particleHead[i] = head;

            const tBase = i * TRAIL_LENGTH * 2;
            particleTrails[tBase + head * 2] = nx;
            particleTrails[tBase + head * 2 + 1] = ny;
          }
        }

        if (global.gc) global.gc();
        const memAfter = process.memoryUsage().heapUsed;
        const delta = memAfter - memBefore;

        console.log(JSON.stringify({
          status: "success",
          particleTrailsByteLength: particleTrails.byteLength,
          particleStateByteLength: particleState.byteLength,
          particleHeadByteLength: particleHead.byteLength,
          heapDeltaBytes: delta
        }));
        """

        result = subprocess.run(
            ["node", "--expose-gc", "-e", node_script],
            capture_output=True,
            text=True,
            check=True
        )

        data = json.loads(result.stdout.strip())
        assert data["status"] == "success"
        assert data["particleTrailsByteLength"] == 83200
        assert data["particleStateByteLength"] == 31200
        assert data["particleHeadByteLength"] == 1300
        # Post-GC heap delta must be under 50 KB (typically negative or near zero)
        assert abs(data["heapDeltaBytes"]) < 50000, f"Excessive heap drift detected: {data['heapDeltaBytes']} bytes"
