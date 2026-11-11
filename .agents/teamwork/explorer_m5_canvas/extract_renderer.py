with open("original System/index.html", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

# Print lines 415 to 650
for i in range(414, 650):
    print(f"L{i+1}: {lines[i]}", end="")
