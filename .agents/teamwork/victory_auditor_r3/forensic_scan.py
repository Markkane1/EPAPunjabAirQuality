import os
import re

patterns = [
    (r"pytest\s+in\s+sys\.modules", "pytest evasion"),
    (r"if\s+['\"]test['\"]\s+in", "test name branch"),
    (r"__CI__", "CI bypass branch"),
    (r"mock\s*=\s*True", "hardcoded mock active"),
]

print("=== FORENSIC SCAN OF SRC/ ===")
findings = []
for root, dirs, files in os.walk("src"):
    for f in files:
        if f.endswith((".py", ".ts", ".tsx", ".js")) and not f.endswith(".d.ts"):
            p = os.path.join(root, f)
            with open(p, "r", encoding="utf-8", errors="ignore") as fp:
                for idx, line in enumerate(fp, 1):
                    for pat, desc in patterns:
                        if re.search(pat, line):
                            findings.append((p, idx, desc, line.strip()))

print(f"Total findings: {len(findings)}")
for p, idx, desc, line in findings:
    print(f"  {p}:{idx} [{desc}] -> {line[:120]}")
