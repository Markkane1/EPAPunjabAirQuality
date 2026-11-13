with open('original System/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = text.find('id="minis"')
if idx != -1:
    print("Heading before #minis:")
    print(text[idx-1200:idx])
