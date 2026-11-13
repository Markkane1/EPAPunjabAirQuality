with open('src/frontend/static/js/app.js', encoding='utf-8') as f:
    text = f.read()

idx = text.find('async loadInitialTelemetry')
print(text[idx:idx+1200])
