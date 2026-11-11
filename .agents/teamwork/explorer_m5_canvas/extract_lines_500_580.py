with open("original System/index.html", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

for i in range(500, 580):
    print(f"L{i+1}: {lines[i]}", end="")
