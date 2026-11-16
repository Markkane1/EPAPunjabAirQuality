import os
import re

patterns = [
    (r'if\s+[\'"]test[\'"]\s+in', 'test name check'),
    (r'pytest\s+in\s+sys\.modules', 'pytest detection bypass'),
    (r'__CI__', 'CI environment bypass'),
    (r'def\s+[a-zA-Z0-9_]+\([^)]*\):\s*(?:pass|\.\.\.|return\s+(?:None|True|False|0|\[\]|\{\}))\s*$', 'trivial facade function'),
]

findings = []
for root, dirs, files in os.walk('src'):
    for f in files:
        if f.endswith(('.py', '.ts', '.tsx', '.js')):
            p = os.path.join(root, f)
            with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                lines = fp.readlines()
                for line_idx, line in enumerate(lines):
                    for pat, desc in patterns:
                        if re.search(pat, line):
                            findings.append((p, line_idx + 1, desc, line.strip()))

print(f"Total findings: {len(findings)}")
for f in findings:
    print(f"{f[0]}:{f[1]} [{f[2]}] -> {f[3]}")
