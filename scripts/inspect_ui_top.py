with open('src/frontend/static/js/ui.js', encoding='utf-8') as f:
    text = f.read()

print("Length of ui.js:", len(text))
print("First 40 lines:")
print("\n".join(text.splitlines()[:40]))
