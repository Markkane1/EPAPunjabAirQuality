with open('tests/integration/test_m5_remediation_adversarial_deep.py', 'r', encoding='utf-8') as f:
    text = f.read()

for l in text.split('\n'):
    if 'assert' in l and ('.js' in l or 'src' in l or 'read_text' in l or 'ui_js' in l or 'api_js' in l):
        print(l)
