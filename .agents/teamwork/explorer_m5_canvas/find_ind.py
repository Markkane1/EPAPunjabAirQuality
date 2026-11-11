with open("original System/index.html", "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

pos = text.find("const IND=")
if pos != -1:
    print("Found const IND= at", pos)
    print(text[pos:pos+300])
else:
    # let's find IND
    pos2 = text.find("IND=")
    print("Found IND= at", pos2)
    print(text[pos2-50:pos2+200])
