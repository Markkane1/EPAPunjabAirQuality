with open('src/frontend/static/js/ui.js', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# Look for grid or mini in ui.js
for m in re.finditer(r'grid|mini', text, re.IGNORECASE):
    print(text[max(0, m.start()-40):min(len(text), m.start()+160)])
    print("-" * 50)

print("\nMethod names in UIController:")
for m in re.finditer(r'^\s*([a-zA-Z0-9_]+)\s*\([^)]*\)\s*\{', text, re.MULTILINE):
    print("  ", m.group(1))
