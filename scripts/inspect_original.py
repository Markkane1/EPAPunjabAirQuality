with open('original System/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = text.find('function setPol(p)')
if idx != -1:
    print("setPol implementation:")
    print(text[idx:idx+1500])

idx_btns = text.find('id="polBtns"')
if idx_btns != -1:
    print("\n#polBtns HTML:")
    print(text[max(0, idx_btns-100):min(len(text), idx_btns+800)])
else:
    print("polBtns not found as id='polBtns', searching for polBtns in text...")
    for m in re.finditer(r'polBtns', text):
        print(text[max(0, m.start()-50):min(len(text), m.start()+150)])
