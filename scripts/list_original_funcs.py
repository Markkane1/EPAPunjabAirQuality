with open('original System/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
funcs = re.findall(r'(?:function\s+([a-zA-Z0-9_]+)\s*\(|(?:const|let|var)\s+([a-zA-Z0-9_]+)\s*=\s*(?:\([^)]*\)|[a-zA-Z0-9_]+)\s*=>)', text)
func_names = [f[0] or f[1] for f in funcs if f[0] or f[1]]
print(f"Total functions in original System: {len(func_names)}")
print("Unique functions:", sorted(set(func_names)))
