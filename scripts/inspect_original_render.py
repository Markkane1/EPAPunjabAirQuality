with open('original System/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Find render function in mainsrc
idx = text.find('function render(')
if idx != -1:
    print("=== function render ===")
    print(text[idx:idx+2000])
else:
    # search for render=
    for m in re.finditer(r'function render|const render\s*=|let render\s*=', text):
        print(text[m.start():m.start()+1000])
