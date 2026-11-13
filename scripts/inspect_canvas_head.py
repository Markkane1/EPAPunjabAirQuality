with open('src/frontend/static/js/canvas.js', 'r', encoding='utf-8') as f:
    text = f.read()

# Check for export statements and classes
lines = text.split('\n')
print(f"Total lines: {len(lines)}")
for i in range(min(50, len(lines))):
    print(f"{i+1}: {lines[i]}")
