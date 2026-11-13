with open('original System/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

helpers = [
    'const BP=',
    'const AQI_B=',
    'const MULT=',
    'const RGB=',
    'const POLNAME=',
    'const isAQI=',
    'const refFor=',
    'const bpIdx=',
    'const colArr=',
    'function colArr(',
    'function col(',
    'const aqiBar=',
    'const aqiTicks=',
    'const bpTicks=',
    'const barFor=',
    'const limLabel=',
    'function stationPts(',
    'function fieldAt(',
    'function renderField('
]

for h in helpers:
    idx = text.find(h)
    if idx != -1:
        print(f"=== {h} ===")
        print(text[idx:idx+400])
        print()
