import re

with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

scripts = re.findall(r'<script\b[^>]*>(.*?)</script>', text, flags=re.DOTALL)
print("=== SCRIPT #4 ===")
print(scripts[3])
