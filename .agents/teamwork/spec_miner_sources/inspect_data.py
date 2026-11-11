import json

with open('index.html', 'r', encoding='utf-8') as f:
    for line in f:
        if line.startswith('<script>window.DATA='):
            s = line[len('<script>window.DATA='):].rstrip()
            if s.endswith(';</script>'):
                s = s[:-10]
            elif s.endswith('</script>'):
                s = s[:-9]
            data = json.loads(s)
            break

print("=== META ===")
print(json.dumps(data['meta'], indent=2))

print("\n=== STATIONS (Sample 2 stations) ===")
for st in data['stations'][:2]:
    print(json.dumps(st, indent=2))

print(f"\nTotal stations: {len(data['stations'])}")

print("\n=== DISTRICTS (Sample 2 districts) ===")
for k in list(data['districts'].keys())[:2]:
    print(k, json.dumps(data['districts'][k], indent=2))

print("\n=== AIRPORTS ===")
print(json.dumps(data['airports'], indent=2))

print("\n=== ECM Keys and Shapes ===")
ecm = data.get('ecm', {})
for k, v in ecm.items():
    if isinstance(v, list):
        print(f"  ecm['{k}'] (list, len={len(v)}), sample: {v[:5] if len(v)>0 and not isinstance(v[0], list) else (v[0][:5] if len(v)>0 else [])}")
    elif isinstance(v, dict):
        print(f"  ecm['{k}'] (dict, keys={list(v.keys())[:5]})")
    else:
        print(f"  ecm['{k}'] = {v}")

print("\n=== TBGEO ===")
print("tbgeo keys:", list(data.get('tbgeo', {}).keys()))
print("tbgeo['districts'] count:", len(data['tbgeo']['districts']))
sample_tbd = list(data['tbgeo']['districts'].keys())[0]
print(f"sample tbgeo['districts']['{sample_tbd}']:", data['tbgeo']['districts'][sample_tbd])
print("sample tbgeo['border'] len:", len(data['tbgeo']['border']))

print("\n=== POLLUTANTS (data['pol']) ===")
for p, pdata in data['pol'].items():
    print(f"Pollutant: {p}")
    print(f"  keys: {list(pdata.keys())}")
    print(f"  unit: {pdata.get('unit')}, ref: {pdata.get('ref')}, peqs: {pdata.get('peqs')}, scale: {pdata.get('scale')}")
    print(f"  frames len: {len(pdata.get('frames', []))}")
    if pdata.get('frames'):
        sample_frame = pdata['frames'][0]
        print(f"  sample frame keys: {list(sample_frame.keys())}")
        print(f"  sample frame c count: {len(sample_frame.get('c', {}))}")
        print(f"  sample frame l count: {len(sample_frame.get('l', []))}")
        if sample_frame.get('l'):
            print(f"    sample link: {sample_frame['l'][0]}")
    if 'daily' in pdata:
        print(f"  daily districts: {len(pdata['daily'])}")
        d0 = list(pdata['daily'].keys())[0]
        print(f"    sample daily[{d0}]: {pdata['daily'][d0]}")
    if 'links' in pdata:
        print(f"  top links count: {len(pdata['links'])}")
        if pdata['links']:
            print(f"    sample link: {pdata['links'][0]}")
    if 'cpf' in pdata:
        print(f"  cpf districts: {len(pdata['cpf'])}")
        c0 = list(pdata['cpf'].keys())[0]
        print(f"    sample cpf[{c0}] keys: {list(pdata['cpf'][c0].keys())}")
        print(f"    sample cpf[{c0}] q75: {pdata['cpf'][c0].get('q75')}, n: {pdata['cpf'][c0].get('n')}")
    if 'series' in pdata:
        print(f"  cross-border series len: {len(pdata['series'])}")
        if pdata['series']:
            print(f"    sample series[0]: {pdata['series'][0]}")
