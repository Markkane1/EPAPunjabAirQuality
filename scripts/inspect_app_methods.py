with open('src/frontend/static/js/app.js', encoding='utf-8') as f:
    text = f.read()

print("Length of app.js:", len(text))
import re
methods = re.findall(r'(\w+)\s*\([^)]*\)\s*\{', text)
print("Methods in app.js:", methods)
