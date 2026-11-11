import re

with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
    html_content = f.read()

# Extract script mainsrc
p1 = html_content.find('<script id="mainsrc" type="text/plain">')
p2 = html_content.find('</script>', p1)
mainsrc = html_content[p1:p2]

# Look for DOM event listeners and queries
listeners = re.findall(r'(\$\([\'\"][a-zA-Z0-9_-]+[\'\"]\)|document\.getElementById\([\'\"][a-zA-Z0-9_-]+[\'\"]\)|document\.querySelectorAll\([^\)]+\)|[a-zA-Z0-9_$]+)\.(addEventListener|onclick|onchange|oninput)\s*=', mainsrc)
print("Event listeners in mainsrc:")
for l in listeners:
    print(" ", l)

# Check all element IDs in HTML
ids = re.findall(r'id=["\']([a-zA-Z0-9_-]+)["\']', html_content)
print(f"\nTotal element IDs in HTML: {len(ids)}")
print("IDs:", ids)

# Check classes in HTML
classes = re.findall(r'class=["\']([a-zA-Z0-9_\s-]+)["\']', html_content)
unique_classes = set()
for c in classes:
    for item in c.split():
        unique_classes.add(item)
print(f"\nUnique classes in HTML ({len(unique_classes)}):", sorted(list(unique_classes)))
