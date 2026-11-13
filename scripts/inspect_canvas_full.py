with open('src/frontend/static/js/canvas.js', 'r', encoding='utf-8') as f:
    text = f.read()

# Check lines 1 to 100
for l in text.split('\n')[:80]:
    print(l)
