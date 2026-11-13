with open('original System/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

for fn in ['function drawChoro', 'function drawValues', 'function drawLahore']:
    idx = text.find(fn)
    if idx != -1:
        print(f"=== {fn} ===")
        print(text[idx:idx+1500])
