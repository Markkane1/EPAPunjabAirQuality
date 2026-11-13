with open('src/frontend/static/js/canvas.js', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('const px = gx * 5 + 2.5')
if idx != -1:
    print(text[idx:idx+1500])
