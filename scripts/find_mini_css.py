with open('original System/index.html', encoding='utf-8') as f:
    text = f.read()

import re
matches = re.findall(r'(\.mini[^{]*\{[^}]+\})', text)
for m in matches[:10]:
    print(m)

matches2 = re.findall(r'(\.m[a-z]+[^{]*\{[^}]+\})', text)
for m in matches2[:10]:
    print(m)
