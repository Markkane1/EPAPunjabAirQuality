with open('original System/index.html', encoding='utf-8') as f:
    text = f.read()

idx = text.find('function stationPts')
print(text[idx:idx+1000])
