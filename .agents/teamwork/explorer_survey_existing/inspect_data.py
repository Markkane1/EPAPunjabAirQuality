import json

with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

line_262 = lines[261]
json_str = line_262[len('<script>window.DATA='):].rstrip().rstrip(';</script>')
data = json.loads(json_str)

print("=== STATIONS DETAILS ===")
print("First 10 stations:")
for i, s in enumerate(data['stations'][:10]):
    print(f"[{i}] {s}")

print("\nNetwork list count:", len(data.get('network', [])))
print("Network list sample (first 10):", data.get('network', [])[:10])

print("\nCoordsrc sample (first 10):")
for k in list(data.get('coordsrc', {}).keys())[:10]:
    print(f"  {k}: {data['coordsrc'][k]}")

print("\nSkipped:", data.get('skipped'))

print("\n=== HOURS ===")
print(f"Total hours: {len(data['hours'])}")
print(f"Start: {data['hours'][0]}, End: {data['hours'][-1]}")
print(f"Sample hours: {data['hours'][:3]} ... {data['hours'][-3:]}")

print("\n=== WIND ===")
print(f"Total wind entries: {len(data['wind'])}")
print(f"Wind sample [0]: {data['wind'][0]}")

print("\n=== POL PM2.5 DETAILS ===")
pm25 = data['pol']['PM2.5']
for k in pm25.keys():
    v = pm25[k]
    if isinstance(v, list):
        print(f"  PM2.5[{k}]: list len={len(v)}, sample_elem_type={type(v[0]) if v else None}")
        if v and isinstance(v[0], list):
            print(f"    nested len={len(v[0])}, first nested sample={v[0][:5]}")
        elif v and isinstance(v[0], dict):
            print(f"    first dict keys={list(v[0].keys())}")
        elif v and isinstance(v[0], (int, float, str)):
            print(f"    first 5 values={v[:5]}")
    elif isinstance(v, dict):
        print(f"  PM2.5[{k}]: dict keys={list(v.keys())}")
    else:
        print(f"  PM2.5[{k}]: {v}")

print("\n=== QA SAMPLE ===")
for k in list(data['qa'].keys())[:5]:
    print(f"  QA[{k}]: {data['qa'][k]}")

print("\n=== TBGEO ===")
print(f"tbgeo keys: {list(data['tbgeo'].keys())}")
print(f"tbgeo['districts']: {data['tbgeo']['districts']}")
print(f"tbgeo['border'] len: {len(data['tbgeo']['border'])}")

print("\n=== ADM SAMPLE ===")
print(f"adm districts count: {len(data['adm'])}")
d0 = list(data['adm'].keys())[0]
print(f"adm['{d0}'] keys: {list(data['adm'][d0].keys()) if isinstance(data['adm'][d0], dict) else type(data['adm'][d0])}")
