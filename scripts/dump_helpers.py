with open('original System/index.html', encoding='utf-8') as f:
    text = f.read()

for helper in ['refFor', 'barFor', 'isAQI', 'limLabel', 'aqiTicks', 'bpTicks', 'colArr', 'col']:
    idx = text.find(helper)
    print(f"=== {helper} ===")
    print(text[idx-50:idx+350])
