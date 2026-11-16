import os
import re

print("=== PIPELINES SIMULATION & MOCK SCAN ===")
pipeline_files = [
    "src/pipelines/base.py",
    "src/pipelines/epa_punjab.py",
    "src/pipelines/metar.py",
    "src/pipelines/cams.py",
    "src/pipelines/firms.py",
    "src/pipelines/iqair.py",
    "src/pipelines/scheduler.py",
    "src/pipelines/cron_scheduler.py",
    "src/pipelines/staging_buffer.py",
]

terms = [r"random\.", r"simulation", r"synthetic", r"mock"]

for pf in pipeline_files:
    if not os.path.exists(pf):
        print(f"File not found: {pf}")
        continue
    with open(pf, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            for t in terms:
                if re.search(t, line, re.IGNORECASE):
                    # Check context: comments, jitter, mode checks
                    print(f"{pf}:{idx} [{t}] -> {line.strip()[:100]}")
