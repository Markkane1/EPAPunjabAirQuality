with open('src/frontend/static/js/ui.js', encoding='utf-8') as f:
    text = f.read()

idx = text.find('switchDeepDiveTab')
print(text[idx:idx+600])
