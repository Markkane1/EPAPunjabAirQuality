import re
with open('src/frontend/static/js/ui.js', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.split('\n')
print(f"Total lines in ui.js: {len(lines)}")
for i, l in enumerate(lines):
    if l.strip().startswith('constructor(') or re.match(r'^\s{2}[a-zA-Z0-9_]+\s*\([^)]*\)\s*\{', l):
        print(f"Line {i+1}: {l.strip()[:60]}")
