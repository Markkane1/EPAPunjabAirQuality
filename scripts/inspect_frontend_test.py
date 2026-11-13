with open('tests/integration/test_frontend.py', encoding='utf-8') as f:
    text = f.read()

idx = text.find('panel-grid')
print(text[idx-200:idx+600])
