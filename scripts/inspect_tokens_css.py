with open('src/frontend/static/css/tokens.css', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'multi-pollutant-grid|mini', text)]
print("Matches in tokens.css:", len(matches))
for m in matches:
    print(text[m-20:m+200])
