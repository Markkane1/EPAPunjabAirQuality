import re

with open("original System/index.html", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# Let's find script boundaries
scripts = []
for idx, line in enumerate(lines):
    if "<script" in line:
        scripts.append(idx)
    if "</script>" in line:
        scripts.append(idx)

print("Script tags at lines:", [s+1 for s in scripts])

# Let's inspect line 377 to 786
mainsrc_lines = lines[376:786]
print(f"mainsrc has {len(mainsrc_lines)} lines")

for idx, line in enumerate(mainsrc_lines):
    line_num = 377 + idx
    # match function definitions, canvas setup, particle setup, etc.
    if re.search(r'(function\s+\w+|const\s+\w+\s*=|let\s+\w+\s*=|class\s+\w+)', line):
        clean = line.strip()[:120]
        if not clean.startswith("const GEO"): # GEO is huge
            print(f"L{line_num}: {clean}")
