with open('src/frontend/static/css/tokens.css', encoding='utf-8') as f:
    text = f.read()

idx = text.find('multi-pollutant')
print(text[idx-100:idx+600])
