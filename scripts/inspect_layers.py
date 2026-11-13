with open('src/frontend/static/js/canvas.js', 'r', encoding='utf-8') as f:
    text = f.read()

import re

for layer in ['drawLayer0', 'drawLayer1', 'drawLayer2', 'drawLayer3', 'drawLayer4', 'render']:
    idx = text.find(f'{layer}(')
    if idx != -1:
        print(f"=== {layer} ===")
        print(text[idx:idx+800])
        print()
