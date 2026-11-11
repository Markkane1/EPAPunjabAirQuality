import json

with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

line_262 = lines[261]
json_str = line_262[len('<script>window.DATA='):].rstrip().rstrip(';</script>')
data = json.loads(json_str)

pm25 = data['pol']['PM2.5']

for k, v in pm25.items():
    t = type(v).__name__
    if isinstance(v, list):
        elem_t = type(v[0]).__name__ if v else 'empty'
        print(f"Key: {k:<10} | Type: {t} len={len(v)} | First elem: {elem_t} -> {str(v[0])[:120]}")
    elif isinstance(v, dict):
        print(f"Key: {k:<10} | Type: {t} keys={len(v)} | Keys sample: {list(v.keys())[:5]} | Sample val: {str(list(v.values())[0])[:120]}")
    else:
        print(f"Key: {k:<10} | Type: {t} = {v}")
