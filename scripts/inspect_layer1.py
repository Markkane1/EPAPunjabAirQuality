with open('src/frontend/static/js/canvas.js', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('drawLayer1(')
if idx != -1:
    print(text[idx:idx+2500])
