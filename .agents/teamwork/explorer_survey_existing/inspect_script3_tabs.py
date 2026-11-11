import re

with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

scripts = re.findall(r'<script\b[^>]*>(.*?)</script>', text, flags=re.DOTALL)
mainsrc = scripts[2]
lines = mainsrc.splitlines()

for i in range(100, len(lines), 30):
    chunk = lines[i:i+30]
    print(f"\n--- Lines {i+1} to {i+len(chunk)} ---")
    for j, line in enumerate(chunk):
        if any(w in line for w in ['tab', 'render', 'click', 'function', 'const', 'let', 'table', 'chart', 'draw']):
            print(f"{i+j+1:3d}: {line[:110]}")
