import re

with open('src/frontend/dashboard.html', encoding='utf-8') as f:
    text = f.read()

sections = re.findall(r'<section[^>]*id="([^"]+)"', text)
print('Section IDs in dashboard.html:', sections)
panels = re.findall(r'id="panel-([^"]+)"', text)
print('Panel IDs in dashboard.html:', panels)

# Find references to mini or grid
for line in text.splitlines():
    if 'mini' in line.lower() or 'grid' in line.lower() or 'pollutant' in line.lower():
        print("MATCH:", line[:120])
