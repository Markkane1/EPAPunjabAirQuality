with open('original System/index.html', encoding='utf-8') as f:
    text = f.read()

idx = text.find('function polTable')
print(text[idx-50:idx+800])
