import json

with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()
line_262 = lines[261]
json_str = line_262[len('<script>window.DATA='):].rstrip().rstrip(';</script>')
data = json.loads(json_str)

# From collector.py
PMAP = {"10": "DHQ Sheikhupura", "12": "FMDRC-LHR", "13": "GCU Faisalabad", "15": "Govt. Teaching Hospital Shahdara-LHR",
 "18": "Kahna Nau Hospital-LHR", "19": "LWMC-LHR", "27": "Gulberg III Lahore - Mobile 1", "22": "PKLI-LHR",
 "23": "Punjab University-LHR", "24": "Safari Park-LHR", "177": "Nankana Sahib", "171": "Sahiwal", "178": "Jhang",
 "25": "UET-LHR", "30": "Egerton Road - Mobile 4", "169": "Pakpattan",
 "20": "M. Nawaz Sharif University of Engineering & Technology Multan", "29": "Wagha Border LHR - Mobile 3",
 "33": "DC Office Narowal", "170": "Okara", "34": "DC Office Hafizabad", "28": "Lathepur LHR - Mobile 2",
 "37": "DC Office Khanewal", "172": "Wazirabad", "3": "BZU Multan", "5": "DC Office Faisalabad", "174": "Rajanpur",
 "175": "Vehari", "31": "BHU Jandiala Kalsan LHR - Mobile 5", "180": "Kot Addu", "35": "DC Office Gujrat",
 "21": "NTU Faisalabad", "179": "Attok", "173": "Mandi Bahauddin", "181": "Bhakkar", "2": "BISE Sargodha",
 "6": "DC Office Gujranwala", "39": "DC Office Rahim Yar Khan", "184": "Khushab", "185": "Mianwali",
 "9": "DC Office Sialkot", "38": "DC Office Muzaffargarh", "14": "GCW Gujranwala", "4": "DC Office DG Khan",
 "8": "DC Office Sargodha", "16": "IUB (Baghdad Campus) Bahawalpur", "17": "IUB (Khawaja Fareed Campus) Bahawalpur",
 "176": "Jhelum", "11": "Drug Testing Laboratory Rawalpindi", "7": "DC Office Rawalpindi", "36": "DC Office Chakwal",
 "183": "Talagang", "1": "ARID University Rawalpindi", "186": "Murree", "32": "DC Office Kasur"}

pmap_names = set(PMAP.values())
station_names = set(s['name'] for s in data['stations'])

print(f"Total stations in index.html: {len(station_names)}")
print(f"Total stations in collector PMAP: {len(pmap_names)}")
matched = station_names.intersection(pmap_names)
print(f"Direct match with PMAP: {len(matched)}")
unmatched = station_names - pmap_names
print(f"In index.html but not PMAP ({len(unmatched)}):")
for s in sorted(unmatched):
    # find which district it belongs to
    s_obj = [x for x in data['stations'] if x['name'] == s][0]
    print(f"  {s} ({s_obj['d']})")
