with open('src/frontend/static/js/app.js', encoding='utf-8') as f:
    text = f.read()

idx = text.find('evaluateInterpolatedSlice(fp) {')
idx2 = text.find('updateThrottledUI', idx)
print(text[idx:idx2])
