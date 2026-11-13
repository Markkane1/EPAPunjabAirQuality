with open('src/frontend/static/js/canvas.js', 'r', encoding='utf-8') as f:
    text = f.read()

import re

for m in re.finditer(r'^\s*([a-zA-Z0-9_]+)\s*\([^)]*\)\s*\{', text, re.MULTILINE):
    print("  ", m.group(1))

# Check where pollutant is used in canvas.js
matches = [m.start() for m in re.finditer(r'pollutant', text)]
print("\nPollutant occurrences in canvas.js:", len(matches))
for m in matches[:10]:
    print(text[max(0, m.start()-30):min(len(text), m.start()+120)])
    print("-" * 40)
