import re

with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

scripts = re.findall(r'<script\b[^>]*>(.*?)</script>', text, flags=re.DOTALL)
print("=== SCRIPT #2 ===")
print(scripts[1][:3000])
print("\n... (length is", len(scripts[1]), ")\n")
print(scripts[1][-1000:])
