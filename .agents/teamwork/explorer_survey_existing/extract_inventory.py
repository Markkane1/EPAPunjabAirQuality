import json

with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

line_262 = lines[261]
json_str = line_262[len('<script>window.DATA='):].rstrip().rstrip(';</script>')
data = json.loads(json_str)

stations = data['stations']
print(f"Total stations: {len(stations)}")

# Count by district
by_dist = {}
mobiles = []
for s in stations:
    d = s.get('d', 'Unknown')
    by_dist[d] = by_dist.get(d, 0) + 1
    if s.get('mobile'):
        mobiles.append(s['name'])

print(f"Districts with stations: {len(by_dist)}")
print("Mobile stations:", len(mobiles), mobiles)
print("\nStations per district:")
for d in sorted(by_dist.keys()):
    print(f"  {d}: {by_dist[d]} stations")

# Compare with network
print(f"\nNetwork list count: {len(data.get('network', []))}")
net_names = {x['name'] for x in data.get('network', [])}
station_names = {s['name'] for s in stations}
print(f"Common names: {len(station_names.intersection(net_names))}")
print(f"In stations but not net_names: {len(station_names - net_names)}")

# Coordsrc
print("\nCoordsrc breakdown:")
csrc_counts = {}
for k, v in data.get('coordsrc', {}).items():
    csrc_counts[v] = csrc_counts.get(v, 0) + 1
for k, v in csrc_counts.items():
    print(f"  {k}: {v}")

# District list
print(f"\nTotal districts in data['districts']: {len(data['districts'])}")
monitored = [d for d, v in data['districts'].items() if not v.get('est')]
estimated = [d for d, v in data['districts'].items() if v.get('est')]
print(f"Monitored districts ({len(monitored)}): {sorted(monitored)}")
print(f"Estimated (unmonitored) districts ({len(estimated)}): {sorted(estimated)}")

# Airports
print("\nAirports:")
for ap in data['airports']:
    print(f"  {ap['id']}: {ap['name']} [{ap['lat']}, {ap['lon']}], obs count: {len(ap.get('u', []))}")
