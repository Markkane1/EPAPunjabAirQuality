with open('original System/index.html', encoding='utf-8') as f:
    text = f.read()

idx = text.find('id="minis"')
print("Found id='minis':", idx)
if idx != -1:
    print(text[idx-200:idx+2500])
else:
    idx2 = text.find('class="mcard"')
    print("Found mcard:", idx2)
    if idx2 != -1:
        print(text[idx2-200:idx2+1500])
