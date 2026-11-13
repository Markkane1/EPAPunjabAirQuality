with open('original System/index.html', encoding='utf-8') as f:
    text = f.read()

idx = text.find('function drawMinis(){')
idx2 = text.find('function ', idx + 20)
print(text[idx:idx2])
