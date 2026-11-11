import json

with open("original System/index.html", "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

# Let's find GEO keys
import re
m_geo = re.search(r'const DATA=window\.DATA,\s*GEO=(\{.*?\});', text)
if m_geo:
    print("Found GEO definition in index.html!")
    try:
        geo = json.loads(m_geo.group(1))
        print("GEO keys:", list(geo.keys()))
        for k in geo:
            polys = geo[k]
            print(f"  {k}: {len(polys)} polygons, first poly has {len(polys[0][0]) if polys and polys[0] else 0} coords")
    except Exception as e:
        print("JSON parse error:", e)

# Let's find IND
m_ind = re.search(r'IND\s*=\s*(\{.*?\});', text)
if m_ind:
    print("Found IND definition!")
    try:
        ind = json.loads(m_ind.group(1))
        print("IND keys:", list(ind.keys()))
    except Exception as e:
        print("IND parse error:", e)
else:
    # let's search where IND is defined
    ind_match = re.search(r'const\s+IND\s*=\s*[^;]+;', text)
    if ind_match:
        print("IND declaration:", ind_match.group(0)[:200])

# Let's check TBG / tbgeo in DATA
print("Searching for tbgeo in DATA...")
tbgeo_match = re.search(r'"tbgeo"\s*:\s*\{', text)
if tbgeo_match:
    print("Found 'tbgeo' in DATA!")
