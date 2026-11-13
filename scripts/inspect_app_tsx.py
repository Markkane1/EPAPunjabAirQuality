with open('src/App.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

print("src/App.tsx length:", len(text))
lines = text.split('\n')
print("Total lines in src/App.tsx:", len(lines))
for i in range(min(50, len(lines))):
    print(f"{i+1}: {lines[i]}")
