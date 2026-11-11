import json

with open("data/baseline/districts.json", "r", encoding="utf-8") as f:
    dists = json.load(f)

print(f"Districts in districts.json: {len(dists)}")
names = [d["name"] for d in dists]
print("First 10 names:", names[:10])
print("Last 10 names:", names[-10:])
print("All 41 districts:", sorted(names))
