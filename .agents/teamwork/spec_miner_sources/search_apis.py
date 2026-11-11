import re

with open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

print(f'Total length of index.html: {len(text)} characters')

patterns = [
    r'fetch\s*\(',
    r'XMLHttpRequest',
    r'WebSocket',
    r'https?://[^\s"\'<>]+',
    r'extendData\s*\(',
    r'ArtifactData',
    r'collection\s*[\(\:]',
    r'batch\.json',
    r'raw\.json',
    r'\.json\b',
    r'tile',
    r'openstreetmap',
    r'carto',
    r'mapbox',
    r'open-meteo',
    r'aviationweather',
    r'ogimet',
    r'punjab\.gov\.pk',
    r'firms',
    r'iqair'
]

for pat in patterns:
    matches = list(re.finditer(pat, text, re.IGNORECASE))
    print(f'Pattern "{pat}": {len(matches)} matches')
    for m in matches[:5]:
        start = max(0, m.start() - 60)
        end = min(len(text), m.end() + 60)
        snippet = text[start:end].replace('\n', ' ')
        print(f'   [{m.start()}]: ...{snippet}...')
    if len(matches) > 5:
        print(f'   ... and {len(matches) - 5} more matches.')
    print('-'*50)
