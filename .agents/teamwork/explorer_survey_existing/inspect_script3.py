import re

with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

scripts = re.findall(r'<script\b[^>]*>(.*?)</script>', text, flags=re.DOTALL)
mainsrc = scripts[2] # Script #3

print(f"Script #3 total length: {len(mainsrc)} chars")
lines = mainsrc.splitlines()
print(f"Script #3 total lines: {len(lines)}")

# Let's inspect significant code blocks, functions, canvas rendering, DOM interactions
keywords = ['canvas', 'render', 'draw', 'play', 'pause', 'click', 'tab', 'chart', 'map', 'idw', 'polar', 'rose', 'flux', 'pepc', 'aqi']
for i, line in enumerate(lines[:100]):
    print(f"{i+1:3d}: {line[:100]}")
