import json, re

with open("original System/index.html", "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

# find tbgeo
pos = text.find('"tbgeo":')
if pos != -1:
    sub = text[pos+8:pos+50000]
    # let's find the closing brace of tbgeo
    # tbgeo has { "border": [...], "samples": [...], "districts": {...} }
    # Let's see keys
    print("Found tbgeo snippet:", sub[:300])
    m_border = re.search(r'"border":\s*(\[[^\]]+\])', sub)
    if m_border:
        b = json.loads(m_border.group(1))
        print(f"TBG.border has {len(b)} coordinates")
    
    m_samples = re.search(r'"samples":\s*(\[\[.*?\]\])', sub)
    if m_samples:
        s = json.loads(m_samples.group(1))
        print(f"TBG.samples has {len(s)} nodes")
        print("First 3 samples [lon, lat, nx, ny]:", s[:3])
        print("Last 3 samples [lon, lat, nx, ny]:", s[-3:])
