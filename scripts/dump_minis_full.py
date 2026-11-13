with open('original System/index.html', encoding='utf-8') as f:
    text = f.read()

idx = text.find('/* four-pollutant comparison maps */')
print(text[idx:idx+3500])
