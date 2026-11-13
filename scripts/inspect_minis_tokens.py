with open('src/frontend/static/css/tokens.css', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('.multi-pollutant-grid')
if idx != -1:
    print(text[idx:idx+1200])
