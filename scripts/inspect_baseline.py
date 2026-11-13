import json

with open('data/baseline/baseline_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("Keys in baseline_data.json:", data.keys())
if 'pol' in data:
    print("Keys in data['pol']:", data['pol'].keys())
    for k, v in data['pol'].items():
        print(f"Pollutant: {k}, keys: {v.keys()}")
        if 'unit' in v:
            print(f"  unit: {v['unit']}, ref: {v.get('ref')}, refavg: {v.get('refavg')}, scale: {v.get('scale')}")
        if 'frames' in v:
            print(f"  frames count: {len(v['frames'])}")
            print(f"  sample frame[0] keys: {v['frames'][0].keys()}")
