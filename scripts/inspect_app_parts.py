with open('src/frontend/static/js/app.js', encoding='utf-8') as f:
    text = f.read()

idx1 = text.find('evaluateInterpolatedSlice')
print("=== evaluateInterpolatedSlice ===")
print(text[idx1:idx1+1500])

idx2 = text.find('selectPollutant')
print("=== selectPollutant ===")
print(text[idx2:idx2+600])

idx3 = text.find('animationLoop')
print("=== animationLoop ===")
print(text[idx3:idx3+800])
