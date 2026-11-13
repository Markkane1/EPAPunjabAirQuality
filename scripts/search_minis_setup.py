with open('original System/index.html', encoding='utf-8') as f:
    text = f.read()

idx = text.find("$('minis').innerHTML")
if idx == -1:
    idx = text.find("minis.innerHTML")
if idx == -1:
    idx = text.find("id=\"minis\"")
    # let's look for minis container manipulation
    idx = text.find("mc_")

print("Found mc_ at:", idx)
if idx != -1:
    print(text[idx-400:idx+800])
