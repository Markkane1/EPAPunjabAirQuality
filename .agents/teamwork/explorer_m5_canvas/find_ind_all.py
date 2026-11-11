import re
with open("original System/index.html", "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

matches = [m.start() for m in re.finditer(r'\bIND\b', text)]
print(f"Occurrences of IND: {len(matches)}")
for p in matches[:10]:
    print("---", text[max(0, p-30):p+50])
