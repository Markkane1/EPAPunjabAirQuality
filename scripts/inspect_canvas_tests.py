with open('tests/integration/test_m5_canvas_challenge.py', 'r', encoding='utf-8') as f:
    text = f.read()

for l in text.split('\n'):
    if 'def test_' in l or 'class Test' in l:
        print(l)
