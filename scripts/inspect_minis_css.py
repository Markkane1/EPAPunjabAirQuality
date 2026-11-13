with open('original System/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'\.minis|\.mini\b', text)]
for m in matches[:10]:
    print(text[m-20:m+250])
    print("="*40)
