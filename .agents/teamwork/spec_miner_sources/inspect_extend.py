with open('index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("Lines 310 to 345:")
for i in range(309, min(345, len(lines))):
    print(f"{i+1}: {lines[i].rstrip()}")
