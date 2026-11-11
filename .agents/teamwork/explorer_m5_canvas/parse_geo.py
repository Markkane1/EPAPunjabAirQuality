import re

with open("original System/index.html", "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

# Let's inspect where GEO starts and ends
start_idx = text.find("const DATA=window.DATA, GEO={")
if start_idx != -1:
    snippet = text[start_idx:start_idx+1000]
    print("Snippet:", snippet[:300])

# Let's find all keys in GEO
geo_part = text[start_idx+29:] # from {"Sind":
end_idx = geo_part.find(';\nconst D=DATA.districts')
if end_idx == -1:
    end_idx = geo_part.find(';const D=DATA.districts')
if end_idx == -1:
    end_idx = geo_part.find('; const D=DATA.districts')
print(f"geo_part end_idx: {end_idx}")

geo_str = geo_part[:end_idx] if end_idx != -1 else geo_part[:50000]
import json
try:
    g = json.loads(geo_str)
    print("GEO keys:", list(g.keys()))
except Exception as e:
    print("Error parsing geo_str:", e)
    # Let's find keys via regex
    keys = re.findall(r'"([^"]+)":\[\[\[\[', geo_str)
    print("Regex found keys:", keys)
