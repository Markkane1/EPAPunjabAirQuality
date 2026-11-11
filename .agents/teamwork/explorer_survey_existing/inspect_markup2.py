with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print("Lines 101 to 260:")
for i in range(100, min(260, len(lines))):
    l = lines[i]
    if '<script' in l:
        print(f"Line {i+1}: SCRIPT TAG FOUND")
        break
    if len(l) > 200:
        print(f"{i+1:3d}: {l[:120]} ...")
    else:
        print(f"{i+1:3d}: {l.strip()}")
