with open('original System/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = text.find('id="minis"')
print(text[idx-500:idx+600])
