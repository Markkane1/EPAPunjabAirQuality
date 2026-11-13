with open('src/frontend/static/js/api.js', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('getFallbackHourly(')
if idx != -1:
    print(text[idx:idx+800])
