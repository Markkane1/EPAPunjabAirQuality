"""
Automated Test Runner for Punjab Air Quality E2E Test Suite.
Executes Tiers 1-4 tests, provides formatted console reporting,
and emits structured JSON summary artifact (test_results_e2e.json).
"""
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
E2E_DIR = PROJECT_ROOT / "tests" / "e2e"
REPORT_PATH = PROJECT_ROOT / "test_results_e2e.json"


TIER_MAPPING = {
    "test_tier1_feature_coverage.py": {
        "tier": "Tier 1",
        "name": "Feature Coverage & Contract Validation",
        "description": "Happy-path isolation tests for pure transforms, schemas, and API contracts"
    },
    "test_tier2_boundary_corner.py": {
        "tier": "Tier 2",
        "name": "Boundary, Corner & Limit Cases",
        "description": "Extreme values, calm cutoffs, singularity clamping, sensor holds, and physical guards"
    },
    "test_tier3_pairwise_combinations.py": {
        "tier": "Tier 3",
        "name": "Pairwise Combinations & Cross-Feature Dataflow",
        "description": "Cross-pollutant interactions, wind kinematics, and multi-step pipeline cascades"
    },
    "test_tier4_real_world_scenarios.py": {
        "tier": "Tier 4",
        "name": "Real-World Operational Scenarios",
        "description": "Severe smog episode, offline fallback, user CSV upload, border plume, and multi-station"
    }
}


def print_banner():
    print("=" * 80)
    print("   PUNJAB AIR QUALITY MONITORING & ANALYTICS PLATFORM")
    print("   End-to-End (E2E) Test Suite Automated Runner")
    print("=" * 80)
    print(f" Timestamp:  {datetime.now(timezone.utc).isoformat()}")
    print(f" Platform:   {platform.system()} ({platform.release()})")
    print(f" Python:     {platform.python_version()} ({sys.executable})")
    print(f" Test Dir:   {E2E_DIR}")
    print("=" * 80 + "\n")


def run_tier(test_filename: str) -> Dict[str, Any]:
    """Runs a single test tier file via pytest and returns execution metrics."""
    test_file_path = E2E_DIR / test_filename
    info = TIER_MAPPING.get(test_filename, {"tier": "Unknown", "name": test_filename, "description": ""})

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(test_file_path),
        "-v",
        "--tb=short"
    ]

    start_time = time.perf_counter()
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    duration = time.perf_counter() - start_time

    output = proc.stdout + proc.stderr

    # Parse passed/failed counts from output
    passed = 0
    failed = 0
    tests_list = []

    for line in output.splitlines():
        if "::" in line and ("PASSED" in line or "FAILED" in line):
            parts = line.strip().split()
            test_id = parts[0]
            status = "PASSED" if "PASSED" in line else "FAILED"
            tests_list.append({"test_id": test_id, "status": status})
            if status == "PASSED":
                passed += 1
            else:
                failed += 1

    tier_status = "PASSED" if proc.returncode == 0 and failed == 0 else "FAILED"

    return {
        "tier": info["tier"],
        "name": info["name"],
        "filename": test_filename,
        "description": info["description"],
        "status": tier_status,
        "duration_seconds": round(duration, 3),
        "total": passed + failed,
        "passed": passed,
        "failed": failed,
        "tests": tests_list,
        "raw_output": output if tier_status == "FAILED" else ""
    }


def main():
    print_banner()

    results = []
    total_passed = 0
    total_failed = 0
    total_duration = 0.0

    for filename in TIER_MAPPING.keys():
        print(f"==> Executing {TIER_MAPPING[filename]['tier']}: {TIER_MAPPING[filename]['name']}...")
        tier_result = run_tier(filename)
        results.append(tier_result)

        total_passed += tier_result["passed"]
        total_failed += tier_result["failed"]
        total_duration += tier_result["duration_seconds"]

        status_symbol = "✓ PASS" if tier_result["status"] == "PASSED" else "✗ FAIL"
        print(f"    [{status_symbol}] {tier_result['passed']}/{tier_result['total']} passed in {tier_result['duration_seconds']}s\n")

    overall_status = "PASSED" if total_failed == 0 else "FAILED"

    # Print Summary Table
    print("\n" + "=" * 80)
    print("                      E2E TEST SUITE EXECUTION SUMMARY")
    print("=" * 80)
    print(f"{'Tier':<8} | {'Tier Name':<42} | {'Tests':<6} | {'Passed':<6} | {'Duration':<8} | {'Status'}")
    print("-" * 80)

    for r in results:
        status_label = "PASS" if r["status"] == "PASSED" else "FAIL"
        print(f"{r['tier']:<8} | {r['name']:<42} | {r['total']:<6} | {r['passed']:<6} | {r['duration_seconds']:>6.3f}s | {status_label}")

    print("-" * 80)
    print(f"{'TOTAL':<8} | {'All E2E Test Suites':<42} | {total_passed + total_failed:<6} | {total_passed:<6} | {total_duration:>6.3f}s | {overall_status}")
    print("=" * 80)

    # Generate JSON summary report
    report_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": overall_status,
        "environment": {
            "os": platform.system(),
            "os_release": platform.release(),
            "python_version": platform.python_version(),
            "pytest_installed": True
        },
        "summary": {
            "total_tests": total_passed + total_failed,
            "passed": total_passed,
            "failed": total_failed,
            "duration_seconds": round(total_duration, 3)
        },
        "tiers": results
    }

    with open(REPORT_PATH, mode="w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    print(f"\n[INFO] Structured JSON report generated at: {REPORT_PATH}")

    if overall_status == "PASSED":
        print("\n>>> ALL E2E TEST TIERS PASSED WITH 100% SUCCESS RATE. SYSTEM READY FOR CERTIFICATION. <<<\n")
        sys.exit(0)
    else:
        print(f"\n>>> TEST SUITE FAILED WITH {total_failed} FAILING TESTS. INVESTIGATE LOGS. <<<\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
