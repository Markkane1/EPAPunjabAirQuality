import json

with open('src/frontend/static/data/baseline_data.json', encoding='utf-8') as f:
    data = json.load(f)

print("Keys in baseline_data.json:", list(data.keys()))
if 'pol' in data:
    print("Pollutants in pol:", list(data['pol'].keys()))
    pm25 = data['pol']['PM2.5']
    print("PM2.5 keys:", list(pm25.keys()))
    if 'stations' in pm25:
        print("PM2.5 stations count:", len(pm25['stations']))
        print("Sample station:", list(pm25['stations'].items())[0])
    if 'frames' in pm25:
        print("PM2.5 frames count:", len(pm25['frames']))
        print("Frame 0 keys:", list(pm25['frames'][0].keys()))

if 'stations' in data:
    print("Top level stations count:", len(data['stations']))
    print("Station 0:", data['stations'][0])

if 'wind' in data:
    print("Wind count:", len(data['wind']))
