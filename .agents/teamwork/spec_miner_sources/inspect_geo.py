import re

with open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('GEO={')
end_idx = text.find('const D=DATA.districts', idx)
snippet = text[idx:end_idx]

keys = re.findall(r'"([^"]+)":\s*\[', snippet)
print("GEO Regions:", keys)
