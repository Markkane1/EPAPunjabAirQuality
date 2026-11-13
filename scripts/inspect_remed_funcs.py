with open('tests/integration/test_m5_remediation_adversarial_deep.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
funcs = re.findall(r'def test_[a-zA-Z0-9_]+\([^)]*\):.*?(?=\ndef |\Z)', text, re.DOTALL)
for fn in funcs:
    lines = fn.split('\n')
    print(lines[0])
    for l in lines[1:]:
        if 'assert' in l:
            print("  ", l.strip())
