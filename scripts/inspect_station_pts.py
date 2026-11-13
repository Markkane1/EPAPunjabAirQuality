with open('original System/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = text.find('function stationPts(')
if idx != -1:
    print(text[idx:idx+1500])
else:
    for m in re.finditer(r'stationPts|fieldAt', text):
        print(text[m.start():m.start()+400])
