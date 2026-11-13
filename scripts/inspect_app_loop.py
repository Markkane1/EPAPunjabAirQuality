with open('src/frontend/static/js/app.js', encoding='utf-8') as f:
    text = f.read()

print("\n".join(text.splitlines()[210:300]))
