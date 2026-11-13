with open('src/frontend/static/css/tokens.css', encoding='utf-8') as f:
    text = f.read()

idx = text.find('/* 3x3 Multi-Pollutant Grid */')
print(text[idx-50:idx+800])
