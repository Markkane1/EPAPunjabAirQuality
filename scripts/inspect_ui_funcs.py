with open('src/frontend/static/js/ui.js', encoding='utf-8') as f:
    text = f.read()

idx = text.find('switchView(viewName)')
print("=== switchView to renderSelectedDistrictTelemetry ===")
print(text[idx:idx+2500])
