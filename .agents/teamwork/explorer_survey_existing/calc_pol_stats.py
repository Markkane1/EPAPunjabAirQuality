import json

with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

line_262 = lines[261]
json_str = line_262[len('<script>window.DATA='):].rstrip().rstrip(';</script>')
data = json.loads(json_str)

pol_summary = {}
for p_name, p_data in data['pol'].items():
    stations_data = p_data.get('stations', {})
    all_vals = []
    station_count = len(stations_data)
    null_count = 0
    valid_count = 0
    for s_name, vals in stations_data.items():
        for v in vals:
            if v is not None:
                all_vals.append(v)
                valid_count += 1
            else:
                null_count += 1
    
    min_v = min(all_vals) if all_vals else None
    max_v = max(all_vals) if all_vals else None
    mean_v = sum(all_vals) / len(all_vals) if all_vals else None
    
    pol_summary[p_name] = {
        'unit': p_data.get('unit'),
        'scale': p_data.get('scale'),
        'ref': p_data.get('ref'),
        'refavg': p_data.get('refavg'),
        'stations_reporting': station_count,
        'valid_readings': valid_count,
        'null_readings': null_count,
        'min': round(min_v, 2) if min_v is not None else None,
        'max': round(max_v, 2) if max_v is not None else None,
        'mean': round(mean_v, 2) if mean_v is not None else None,
    }

print(json.dumps(pol_summary, indent=2))
