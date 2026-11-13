with open(r'c:\Users\Asif\Downloads\Punjab Air Quality\original System\index.html', encoding='utf-8') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'CMP\s*=', text)]
for pos in matches:
    print(text[max(0, pos-50):min(len(text), pos+200)])
