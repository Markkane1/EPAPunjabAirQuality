with open('src/frontend/static/js/ui.js', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('updateLegend(')
if idx != -1:
    print(text[idx:idx+1500])
