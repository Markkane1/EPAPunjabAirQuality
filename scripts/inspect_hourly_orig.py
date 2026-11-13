with open('original System/index.html', encoding='utf-8') as f:
    text = f.read()

idx = text.find('buildHourly')
if idx != -1:
    print(text[idx-50:idx+1500])
else:
    idx2 = text.find('hrTable')
    print(text[idx2-50:idx2+1500])
