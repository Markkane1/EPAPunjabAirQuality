import json

with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

line_262 = lines[261]
json_str = line_262[len('<script>window.DATA='):].rstrip().rstrip(';</script>')
data = json.loads(json_str)

stations = data['stations']
coordsrc = data.get('coordsrc', {})
qa = data.get('qa', {})
network_list = {x['name']: x for x in data.get('network', [])}

catalog = []
for s in stations:
    name = s['name']
    d = s['d']
    lat = s['lat']
    lon = s['lon']
    mobile = s.get('mobile', False)
    csrc = coordsrc.get(name, 'unknown')
    qa_info = qa.get(name, {})
    net_info = network_list.get(name, {})
    
    catalog.append({
        'name': name,
        'district': d,
        'lat': lat,
        'lon': lon,
        'mobile': mobile,
        'coord_source': csrc,
        'type': net_info.get('type', 'Mobile' if mobile else 'Fixed'),
        'phase': net_info.get('phase', 'Operational'),
        'valid_hours_wind': qa_info.get('wind_valid', 0),
        'valid_hours_aqi': qa_info.get('AQI', 0),
        'valid_hours_pm25': qa_info.get('PM2.5', 0),
        'valid_hours_pm10': qa_info.get('PM10', 0),
        'valid_hours_no2': qa_info.get('NO2', 0),
        'valid_hours_so2': qa_info.get('SO2', 0),
        'valid_hours_co': qa_info.get('CO', 0),
        'valid_hours_o3': qa_info.get('O3', 0),
        'valid_hours_no': qa_info.get('NO', 0),
        'valid_hours_nox': qa_info.get('NOX', 0)
    })

print(f"Extracted {len(catalog)} station catalog entries.")
print("Sample station catalog entry [0]:")
print(json.dumps(catalog[0], indent=2))

# Save summary to explorer folder
with open('.agents/teamwork/explorer_survey_existing/station_catalog_summary.json', 'w', encoding='utf-8') as f:
    json.dump(catalog, f, indent=2)

print("Saved station_catalog_summary.json")
