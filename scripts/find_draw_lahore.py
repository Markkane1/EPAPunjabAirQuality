with open('original System/index.html', encoding='utf-8') as f:
    text = f.read()

idx = text.find('function drawLahore')
if idx != -1:
    print(text[idx:idx+1500])
else:
    print("Not found function drawLahore")
    import re
    print(re.findall(r'drawLahore\w*', text))
