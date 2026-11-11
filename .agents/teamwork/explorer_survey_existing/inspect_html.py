import re

with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Find scripts
scripts = re.findall(r'<script\b[^>]*>(.*?)</script>', text, flags=re.DOTALL)
print(f"Total script tags: {len(scripts)}")
for i, s in enumerate(scripts):
    s_clean = s.strip()
    prefix = s_clean[:80].replace('\n', ' ')
    print(f"Script #{i+1}: length={len(s_clean)} chars, starts with: {prefix}...")

# Check functions in script #2
if len(scripts) >= 2:
    func_names = re.findall(r'function\s+([A-Za-z0-9_$]+)\s*\(', scripts[1])
    const_funcs = re.findall(r'(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:\([^)]*\)|[A-Za-z0-9_$]+)\s*=>', scripts[1])
    print(f"\nFunctions declared in main script: {len(func_names)}")
    print("Function names:", func_names[:30])
    print(f"Arrow functions declared: {len(const_funcs)}")
    print("Arrow function names:", const_funcs[:30])

# Check HTML sections/structure
divs = re.findall(r'<div\s+class="([^"]+)"', text)
print(f"\nDiv classes in HTML: {set(divs)}")
