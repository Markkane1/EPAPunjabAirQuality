with open('src/frontend/static/js/geo.js', 'r', encoding='utf-8') as f:
    text = f.read()

print("geo.js length:", len(text))
print(text[:1500])
