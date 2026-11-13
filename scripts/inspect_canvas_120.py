with open('src/frontend/static/js/canvas.js', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.split('\n')
for i in range(120):
    print(f"{i+1}: {lines[i]}")
