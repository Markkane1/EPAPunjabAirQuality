with open('original System/index.html', encoding='utf-8') as f:
    text = f.read()

idx = text.find('drawLahore')
if idx != -1:
    print("=== drawLahore ===")
    print(text[idx-50:idx+1500])

idx2 = text.find('lahoreTable')
if idx2 != -1:
    print("=== lahoreTable ===")
    print(text[idx2-50:idx2+1500])
