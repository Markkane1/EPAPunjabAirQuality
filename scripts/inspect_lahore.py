with open('original System/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = text.find('function drawLahore(')
if idx != -1:
    print("=== drawLahore ===")
    print(text[idx:idx+2000])

idx2 = text.find('function lahoreTable(')
if idx2 != -1:
    print("=== lahoreTable ===")
    print(text[idx2:idx2+1500])
