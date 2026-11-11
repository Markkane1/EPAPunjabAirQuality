import re

with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

s = '<script id="mainsrc" type="text/plain">'
p1 = text.find(s)
p2 = text.find('</script>', p1)
src = text[p1 + len(s):p2]

print(f"mainsrc length: {len(src)} chars")

# Find top-level variables and functions
vars_all = re.findall(r'^(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=', src, re.MULTILINE)
funcs_all = re.findall(r'^function\s+([a-zA-Z0-9_$]+)\s*\(', src, re.MULTILINE)

print(f"Top-level variables ({len(vars_all)}):", vars_all)
print(f"Top-level functions ({len(funcs_all)}):", funcs_all)
