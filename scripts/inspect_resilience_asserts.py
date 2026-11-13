with open('tests/integration/test_m5_resilience_challenge.py', 'r', encoding='utf-8') as f:
    text = f.read()

for l in text.split('\n'):
    if 'assert' in l and ('.js' in l or 'src' in l or 'read_text' in l):
        print(l)
