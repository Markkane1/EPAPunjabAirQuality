"""
Independent Victory Verification Test Suite
Project: Punjab Air Quality Decoupled Architecture
Auditor: Victory Auditor (Independent)
"""

import os
import sys
import hashlib
import re

PROJECT_ROOT = r"c:\Users\Asif\Downloads\Punjab Air Quality"
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")

PASS_COUNT = 0
FAIL_COUNT = 0

def log_test(name, passed, detail=""):
    global PASS_COUNT, FAIL_COUNT
    if passed:
        PASS_COUNT += 1
        print(f"[PASS] {name} {detail}")
    else:
        FAIL_COUNT += 1
        print(f"[FAIL] {name} {detail}")

def check_file_sha256(filepath, expected_hash, expected_size=None):
    if not os.path.isfile(filepath):
        return False, f"File not found: {filepath}"
    size = os.path.getsize(filepath)
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    digest = hasher.hexdigest().upper()
    if expected_size is not None and size != expected_size:
        return False, f"Size mismatch: observed {size}, expected {expected_size}"
    if digest != expected_hash.upper():
        return False, f"Hash mismatch: observed {digest}, expected {expected_hash}"
    return True, f"Size={size}, SHA256={digest}"

print("=== STARTING INDEPENDENT VICTORY VERIFICATION ===")

# Test 1: Non-Invasive Baseline Files (R6)
expected_index_hash = "0154B0204275D20327686CEE1C585E75A1E51153611878906A8A7C210A7ECE3F"
res, detail = check_file_sha256(os.path.join(PROJECT_ROOT, "index.html"), expected_index_hash, 9609848)
log_test("R6.1 - index.html integrity", res, detail)

expected_collector_hash = "63F714DB676362A5B095F2FC67DA342EBB319952819424DA46DC7B0D3BC801B1"
res, detail = check_file_sha256(os.path.join(PROJECT_ROOT, "collector", "collector.py"), expected_collector_hash, 16362)
log_test("R6.2 - collector/collector.py integrity", res, detail)

# Test 2: Cleanliness of root and source directories
non_agent_files = []
for root, dirs, files in os.walk(PROJECT_ROOT):
    if ".agents" in root:
        continue
    for f in files:
        rel = os.path.relpath(os.path.join(root, f), PROJECT_ROOT)
        non_agent_files.append(rel)

expected_files = {
    "index.html",
    os.path.normpath("collector/collector.py"),
    os.path.normpath("docs/ARCHITECTURE_OVERVIEW.md"),
    os.path.normpath("docs/DATA_PIPELINES_ARCHITECTURE.md"),
    os.path.normpath("docs/DATA_SOURCES_AND_STREAMS.md"),
    os.path.normpath("docs/SYSTEM_ARCHITECTURE.md"),
    os.path.normpath("docs/TRANSFORMATION_LOGIC_SPEC.md"),
    os.path.normpath("docs/UI_UX_SPECIFICATION.md"),
}
normalized_found = {os.path.normpath(f) for f in non_agent_files}
extra_files = normalized_found - expected_files
missing_files = expected_files - normalized_found

log_test("R6.3 - Directory isolation (no extra files)", len(extra_files) == 0, f"Extra: {extra_files}" if extra_files else "Clean")
log_test("R6.4 - Deliverable presence (all 6 docs present)", len(missing_files) == 0, f"Missing: {missing_files}" if missing_files else "All 6 present")

# Test 3: Anti-Cheat & Prohibited Pattern Check (Phase B)
prohibited_regex = re.compile(r'\b(TODO|TBD|FIXME|PLACEHOLDER|LOREM|XXX|dummy|facade|NotImplemented)\b', re.IGNORECASE)
found_prohibited = []
for doc in expected_files:
    if not doc.startswith("docs"):
        continue
    full_path = os.path.join(PROJECT_ROOT, doc)
    with open(full_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            if prohibited_regex.search(line):
                found_prohibited.append((doc, idx, line.strip()))

log_test("Phase B.1 - Zero stubs/placeholders", len(found_prohibited) == 0, f"Violations: {found_prohibited}" if found_prohibited else "Zero occurrences")

# Test 4: R1 - Data Sources & Stream Inventory Coverage
sources_file = os.path.join(DOCS_DIR, "DATA_SOURCES_AND_STREAMS.md")
with open(sources_file, "r", encoding="utf-8") as f:
    sources_content = f.read()

required_sources = [
    ("EPA Punjab", ["aqi.punjab.gov.pk", "station_id", "pm25", "aqi"]),
    ("NOAA METAR", ["aviationweather.gov", "OPLA", "VIAR", "wspd", "visib"]),
    ("WMO SYNOP", ["ogimet.com", "AAXX", "41640", "i_w"]),
    ("ECMWF IFS", ["open-meteo.com", "ecmwf_ifs025", "wind_speed_10m", "925 hPa"]),
    ("NASA FIRMS", ["firms.modaps.eosdis.nasa.gov", "VIIRS", "FRP", "Rajasthan"]),
    ("IQAir", ["api.airvisual.com", "Peshawar", "Bathinda", "PEPC"]),
    ("CAMS", ["117", "39", "tbgeo", "particulate_matter_2.5um"]),
]

for src_name, tokens in required_sources:
    missing_tokens = [tok for tok in tokens if tok.lower() not in sources_content.lower()]
    log_test(f"R1 - Source '{src_name}' specified with technical detail", len(missing_tokens) == 0, f"Missing tokens: {missing_tokens}" if missing_tokens else "Verified")

# Test 5: R2 - Transformation Logic & Algorithmic Rigor
transforms_file = os.path.join(DOCS_DIR, "TRANSFORMATION_LOGIC_SPEC.md")
with open(transforms_file, "r", encoding="utf-8") as f:
    trans_content = f.read()

required_transforms = [
    ("Geodesic IDW", ["Haversine", "d_0", "5.0", "clamped"]),
    ("Anisotropic IDW", ["cos", "alpha", "epsilon", "0.70", "downwind"]),
    ("Planar Raster IDW", ["power", "cell", "5.0", "soften"]),
    ("Vector Wind Blending", ["polar", "cartesian", "u", "v"]),
    ("16-Sector CPF Polar Roses", ["P_{75}", "0.25", "N_k < 6", "null", "small-sample"]),
    ("Physical Advection Flux", ["Flux", "exp(-", "cone", "35", "AQI"]),
    ("Receptor Coupling", ["Omega", "0.25", "top 60", "net transport"]),
    ("Transboundary Border Index", ["120", "tbval", "39", "117"]),
    ("PEPC AQI Breakpoints", ["continuous", "half-open", "350", "500", "table"]),
    ("Quality Control Filters", ["7-hour", "median", "3-hour", "hold", "index guard", "wazirabad"]),
    ("Equirectangular Projection", ["31", "AABB", "collision"]),
]

for t_name, tokens in required_transforms:
    missing_tokens = [tok for tok in tokens if tok.lower() not in trans_content.lower()]
    log_test(f"R2 - Transform '{t_name}' mathematically formulated", len(missing_tokens) == 0, f"Missing tokens: {missing_tokens}" if missing_tokens else "Verified")

# Test 6: R3 - Modular Data Pipelines Architecture
pipelines_file = os.path.join(DOCS_DIR, "DATA_PIPELINES_ARCHITECTURE.md")
with open(pipelines_file, "r", encoding="utf-8") as f:
    pipe_content = f.read()

required_pipe_elements = [
    ("Pydantic Validation Schemas", ["BaseModel", "RawStationMeasurement", "le=5000.0", "Optional[float] = None"]),
    ("TimescaleDB Primary Key & Upsert", ["PRIMARY KEY (time, station_id)", "ON CONFLICT (time, station_id) DO UPDATE"]),
    ("Redis Caching & Lock", ["lock:ingest", "TTL", "180"]),
    ("Error Handling & Backoff", ["Full Jitter", "circuit breaker", "DLQ"]),
    ("Worker Starvation Prevention", ["short-circuit", "Semaphore", "15"]),
]

for p_name, tokens in required_pipe_elements:
    missing_tokens = [tok for tok in tokens if tok.lower() not in pipe_content.lower()]
    log_test(f"R3 - Pipeline '{p_name}' implemented", len(missing_tokens) == 0, f"Missing tokens: {missing_tokens}" if missing_tokens else "Verified")

# Test 7: R4 - Decoupled System Architecture & Code Simplification
system_file = os.path.join(DOCS_DIR, "SYSTEM_ARCHITECTURE.md")
with open(system_file, "r", encoding="utf-8") as f:
    sys_content = f.read()

required_sys_elements = [
    ("Multi-Tier Service Decomposition", ["Tier 1", "Tier 2", "Tier 3", "Tier 4"]),
    ("OpenAPI 3.1 REST Specification", ["OpenAPI 3.1", "/api/v1/meta", "/api/v1/spatial/surface"]),
    ("Server-Sent Events Real-Time Streaming", ["text/event-stream", "hourly_tick"]),
    ("Code Simplification (Eliminate 60+ globals)", ["60+", "Zustand", "SpatialInterpolationService"]),
    ("PostGIS Spatial Cast ::geography", ["::geography", "ST_DWithin"]),
]

for s_name, tokens in required_sys_elements:
    missing_tokens = [tok for tok in tokens if tok.lower() not in sys_content.lower()]
    log_test(f"R4 - System Architecture '{s_name}' documented", len(missing_tokens) == 0, f"Missing tokens: {missing_tokens}" if missing_tokens else "Verified")

# Test 8: R5 - High-Quality Interface Design Specification (/impeccable)
ui_file = os.path.join(DOCS_DIR, "UI_UX_SPECIFICATION.md")
with open(ui_file, "r", encoding="utf-8") as f:
    ui_content = f.read()

required_ui_elements = [
    ("Aesthetic & Layout (/impeccable)", ["Operate", "Zone", "8pt"]),
    ("Design Tokens & Contrast", ["--color-bg-canvas", "WCAG 2.1 AAA", "tabular-nums"]),
    ("State Store Slices (Zustand)", ["TemporalSlice", "SpatialSlice", "PollutantSlice", "TelemetrySlice"]),
    ("Continuous Sub-Hourly Lerp (60 FPS)", ["0.00", "215.00", "60 FPS"]),
    ("Multi-Layer Rendering Pipeline", ["Layer 0", "Layer 1", "Layer 2", "Layer 3", "Layer 4"]),
]

for u_name, tokens in required_ui_elements:
    missing_tokens = [tok for tok in tokens if tok.lower() not in ui_content.lower()]
    log_test(f"R5 - UI/UX Architecture '{u_name}' defined", len(missing_tokens) == 0, f"Missing tokens: {missing_tokens}" if missing_tokens else "Verified")

# Test 9: Master Overview Synthesis & Roadmap
overview_file = os.path.join(DOCS_DIR, "ARCHITECTURE_OVERVIEW.md")
with open(overview_file, "r", encoding="utf-8") as f:
    over_content = f.read()

required_over_elements = [
    ("Cross-Reference Inventory", ["PAQ-CAT-R1-SOURCES", "PAQ-SPEC-R2-TRANSFORMS", "PAQ-ARCH-R3-PIPELINES"]),
    ("End-to-End Sequence Diagram", ["sequenceDiagram", "autonumber"]),
    ("6-Phase Migration Roadmap", ["Phase 1", "Phase 2", "Phase 3", "Phase 4", "Phase 5", "Phase 6"]),
    ("Cryptographic Compliance Attestation", ["0154B0204275D20327686CEE1C585E75A1E51153611878906A8A7C210A7ECE3F", "63F714DB676362A5B095F2FC67DA342EBB319952819424DA46DC7B0D3BC801B1"]),
]

for o_name, tokens in required_over_elements:
    missing_tokens = [tok for tok in tokens if tok.lower() not in over_content.lower()]
    log_test(f"Overview - '{o_name}' synthesized", len(missing_tokens) == 0, f"Missing tokens: {missing_tokens}" if missing_tokens else "Verified")

print(f"\n=== SUMMARY ===")
print(f"Total Tests Executed: {PASS_COUNT + FAIL_COUNT}")
print(f"Passed: {PASS_COUNT}")
print(f"Failed: {FAIL_COUNT}")

if FAIL_COUNT == 0:
    print("\nVERDICT: ALL TESTS PASSED UNCONDITIONALLY.")
    sys.exit(0)
else:
    print(f"\nVERDICT: {FAIL_COUNT} TESTS FAILED.")
    sys.exit(1)
