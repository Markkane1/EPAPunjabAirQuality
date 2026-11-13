with open('original System/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = text.find('function drawMinis()')
if idx != -1:
    print(text[idx:idx+2500])
