with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print("Lines 1 to 100:")
for i in range(0, min(100, len(lines))):
    l = lines[i]
    if '<script' in l:
        print(f"Line {i+1}: SCRIPT TAG FOUND")
        break
    if len(l) > 200:
        print(f"{i+1:3d}: {l[:120]} ...")
    else:
        print(f"{i+1:3d}: {l.strip()}")
