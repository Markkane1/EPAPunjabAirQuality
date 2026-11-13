with open('src/frontend/static/js/canvas.js', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('drawLayer1(')
lines = text[idx:idx+3000].split('\n')
for i, l in enumerate(lines[:80]):
    print(f"{i+1}: {l}")
