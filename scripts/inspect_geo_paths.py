with open('src/frontend/static/js/geo.js', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('export function compilePaths')
if idx != -1:
    print(text[idx:])
