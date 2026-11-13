with open('original System/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

start = text.find('/* pollutant comparison maps */')
if start == -1:
    start = text.find('CMP=')
end = text.find('/* panels */', start)
print(f"Start: {start}, End: {end}")
print(text[start:end])
