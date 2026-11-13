import re

with open('original System/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Search for grid, mini, multi
for m in re.finditer(r'grid|mini|3x3|multi', text, re.IGNORECASE):
    snippet = text[max(0, m.start()-40):min(len(text), m.start()+160)]
    # filter out css grid: display:grid
    if 'display:grid' not in snippet and 'display: grid' not in snippet and 'grid-template' not in snippet and 'gap:' not in snippet:
        print(f"Match at {m.start()}: {snippet.strip()}\n")
