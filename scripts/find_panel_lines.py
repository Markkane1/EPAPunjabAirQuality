with open('src/frontend/dashboard.html', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'panel-console' in line or 'panel-grid' in line:
        print(f"Line {i+1}: {line.strip()}")
