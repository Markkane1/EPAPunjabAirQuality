"""
Empirical Challenge & Stress Harness: Milestone M1-M2 Challenger 2 (Iteration 2)
Author: challenger_m1m2_r2_2
Date: 2026-11-14

Probes:
1. Production Build & Bundle Cleanliness (`npm run build`).
2. Absence of Banned Imports & Typings (`lucide-react`, `tailwind-merge`, `tailwindcss`, `heroicons`, `feather-icons`).
3. Total Absence of Unicode Emojis across `src/frontend/dashboard.html`, `index.html`, `src/workstation.html`, and `src/`.
4. Execution & Validation of WCAG 2.1 AAA Contrast Matrix (`python tests/challenge_contrast.py`).
"""

import os
import sys
import subprocess
import json
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_cmd(cmd, cwd=PROJECT_ROOT):
    result = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return result.returncode, result.stdout, result.stderr

def probe_build():
    print("================================================================================")
    print(" PROBE 1: PRODUCTION BUILD VERIFICATION (npm run build)")
    print("================================================================================")
    ret, stdout, stderr = run_cmd("npm run build")
    print(f"  Return code: {ret}")
    if ret != 0:
        print("  FAIL: Build exited with non-zero code!")
        print(f"  STDOUT: {stdout[:1000]}")
        print(f"  STDERR: {stderr[:1000]}")
        return False

    dist_dir = os.path.join(PROJECT_ROOT, "dist")
    if not os.path.isdir(dist_dir):
        print(f"  FAIL: dist directory missing at {dist_dir}")
        return False

    assets_dir = os.path.join(dist_dir, "assets")
    if not os.path.isdir(assets_dir):
        print(f"  FAIL: dist/assets directory missing at {assets_dir}")
        return False

    dist_files = os.listdir(dist_dir)
    asset_files = os.listdir(assets_dir)
    print(f"  Verified dist files: {dist_files}")
    print(f"  Verified {len(asset_files)} asset chunks generated.")
    print("  PASS: Production build compiled cleanly with zero errors.")
    return True

def probe_banned_imports():
    print("\n================================================================================")
    print(" PROBE 2: BANNED IMPORTS & AMBIENT EVASION SCAN")
    print("================================================================================")
    banned_tokens = ["lucide-react", "tailwind-merge", "tailwindcss", "heroicons", "feather-icons"]
    violations = []

    src_dir = os.path.join(PROJECT_ROOT, "src")
    for root, dirs, files in os.walk(src_dir):
        for f in files:
            path = os.path.join(root, f)
            with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                for line_no, line in enumerate(fp, 1):
                    for token in banned_tokens:
                        if token in line:
                            violations.append((path, line_no, token, line.strip()))

    ambient_path = os.path.join(src_dir, "domain", "math", "ambient.d.ts")
    if os.path.exists(ambient_path):
        violations.append((ambient_path, 0, "ambient.d.ts", "Ambient evasion file still exists!"))

    print(f"  Violations found in src/: {len(violations)}")
    if violations:
        for p, l, tok, line in violations:
            print(f"    FAIL: {p}:{l} contains banned token '{tok}': {line}")
        return False

    # Check package.json
    pkg_path = os.path.join(PROJECT_ROOT, "package.json")
    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg = json.load(f)
        all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        for tok in banned_tokens:
            if tok in all_deps:
                print(f"    FAIL: package.json declares banned dependency: {tok}")
                return False

    print("  PASS: Zero banned imports, zero ambient evasion facades, zero banned dependencies.")
    return True

def probe_emojis():
    print("\n================================================================================")
    print(" PROBE 3: UNICODE EMOJI AUDIT")
    print("================================================================================")
    def check_for_emojis(filepath):
        if not os.path.exists(filepath):
            return [(filepath, 0, "FILE_NOT_FOUND", "")]
        matches = []
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line_no, line in enumerate(f, 1):
                for ch in line:
                    cp = ord(ch)
                    is_emoji = (
                        (0x1F300 <= cp <= 0x1F9FF) or
                        (0x1FA00 <= cp <= 0x1FAFF) or
                        (0x2600 <= cp <= 0x26FF) or
                        (0x2700 <= cp <= 0x27BF) or
                        (0xFE00 <= cp <= 0xFE0F) or
                        (0x1F1E6 <= cp <= 0x1F1FF)
                    )
                    if is_emoji:
                        matches.append((filepath, line_no, ch, hex(cp)))
        return matches

    critical_files = [
        os.path.join(PROJECT_ROOT, "src", "frontend", "dashboard.html"),
        os.path.join(PROJECT_ROOT, "index.html"),
        os.path.join(PROJECT_ROOT, "src", "workstation.html")
    ]

    total_emojis = []
    for cf in critical_files:
        found = check_for_emojis(cf)
        rel = os.path.relpath(cf, PROJECT_ROOT)
        print(f"  Checking {rel}: {len(found)} emojis found.")
        total_emojis.extend(found)

    # Also scan all files in src/
    for root, dirs, files in os.walk(os.path.join(PROJECT_ROOT, "src")):
        for f in files:
            if f.endswith((".ts", ".tsx", ".html", ".css")):
                p = os.path.join(root, f)
                if p not in critical_files:
                    found = check_for_emojis(p)
                    if found:
                        total_emojis.extend(found)

    if total_emojis:
        for p, l, ch, cp in total_emojis[:10]:
            print(f"    FAIL: Emoji '{ch}' (U+{cp[2:].upper()}) at {os.path.relpath(p, PROJECT_ROOT)}:{l}")
        return False

    print("  PASS: Zero Unicode emojis detected across HTML entrypoints and src/ tree.")
    return True

def probe_contrast_script():
    print("\n================================================================================")
    print(" PROBE 4: CONTRAST MATRIX & DEPENDENCY CHALLENGE (challenge_contrast.py)")
    print("================================================================================")
    ret, stdout, stderr = run_cmd(f"{sys.executable} tests/challenge_contrast.py")
    print(stdout)
    if ret != 0:
        print("  FAIL: tests/challenge_contrast.py exited with non-zero code!")
        if stderr:
            print(stderr)
        return False
    if "All 56 pairs meet WCAG 2.1 AAA (>= 7.000:1): True" not in stdout:
        print("  FAIL: Contrast verification assertion did not report True!")
        return False
    if "Zero banned dependencies present" not in stdout:
        print("  FAIL: Banned dependency audit failed!")
        return False

    print("  PASS: challenge_contrast.py passed with 100% compliance across all 56 pairs.")
    return True

def main():
    b_ok = probe_build()
    i_ok = probe_banned_imports()
    e_ok = probe_emojis()
    c_ok = probe_contrast_script()

    print("\n================================================================================")
    if b_ok and i_ok and e_ok and c_ok:
        print(" EMPIRICAL CHALLENGE VERDICT: ALL ADVERSARIAL CHECKS PASSED -> APPROVE")
        print("================================================================================")
        sys.exit(0)
    else:
        print(" EMPIRICAL CHALLENGE VERDICT: ONE OR MORE CHECKS FAILED -> REQUEST_CHANGES")
        print("================================================================================")
        sys.exit(1)

if __name__ == "__main__":
    main()
