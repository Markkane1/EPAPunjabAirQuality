import json, re

with open("original System/index.html", "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

pos = text.find('"tbgeo":')
if pos != -1:
    sub = text[pos+8:pos+80000]
    # let's find border: [[...]]
    border_idx = sub.find('"border":')
    samples_idx = sub.find('"samples":')
    districts_idx = sub.find('"districts":')
    print(f"Indices: border={border_idx}, samples={samples_idx}, districts={districts_idx}")
    
    # samples: [[lon, lat, nx, ny], ...]
    if samples_idx != -1:
        s_end = sub.find(']]', samples_idx) + 2
        samples_str = sub[samples_idx+10:s_end].strip()
        samples = json.loads(samples_str)
        print(f"TBG.samples has {len(samples)} nodes")
        print("First sample:", samples[0])
        print("Middle sample:", samples[len(samples)//2])
        print("Last sample:", samples[-1])
    
    if border_idx != -1:
        b_end = sub.find(']]', border_idx) + 2
        border_str = sub[border_idx+9:b_end].strip()
        border = json.loads(border_str)
        print(f"TBG.border has {len(border)} points")
        print("First border pt:", border[0])
        print("Last border pt:", border[-1])
