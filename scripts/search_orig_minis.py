with open(r'c:\Users\Asif\Downloads\Punjab Air Quality\original System\index.html', encoding='utf-8') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'minis|CMP', text)]
for pos in matches[:5]:
    print(text[max(0, pos-100):min(len(text), pos+300)])
    print('='*50)
