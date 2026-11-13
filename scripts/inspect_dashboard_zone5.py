with open('src/frontend/dashboard.html', encoding='utf-8') as f:
    text = f.read()

idx = text.find('ZONE 5: DEEP-DIVE PANELS')
print(text[idx-50:idx+1200])
