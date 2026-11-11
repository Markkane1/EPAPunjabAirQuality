#!/usr/bin/env python3
"""Hourly cloud collector for 'Punjab Air Quality, November 2026'.

  python3 -I collector.py fetch OUT            pull every source into OUT/raw.json, print the doc ids to read
  python3 -I collector.py build OUT EXISTING   merge with existing docs (EXISTING/<id>.json from ArtifactData),
                                               write OUT/docs/<id>.json and OUT/batch.json, print a summary

One database document per PKT hour, collection "hours", id h<YYYYMMDDHH>:
  t   "YYYY-MM-DD HH:00" (PKT, hour as stamped by the portal)
  st  {network station name: [AQI, PM2.5, PM10, NO2, SO2, CO, O3, ws m/s, wd deg]}  (raw portal values)
  ap  {ICAO: [dir deg | "CALM" | "VRB", kt, visibility m, temp C, weather, gust kt, obs time UTC]}
  wmo {WMO id: [dir deg | null, m/s, obs time UTC]}
  ecm {district: [ws m/s, wd deg]}   ECMWF IFS 10-m wind via Open-Meteo
  src {portal, metar, wmo, ecmwf}: status strings
No values are invented: anything that cannot be fetched is left out and its status says why.
"""
import json, math, os, re, subprocess, sys, datetime as dt
from pathlib import Path

PORTAL = 'https://aqi.punjab.gov.pk'
PKT = dt.timezone(dt.timedelta(hours=5))
UA = 'EMC-EPA-Punjab-AQ-dashboard/1.0'

# portal station_id -> AQMS network station name (matched on coordinates and names, 3 Nov 2026)
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
NAME_FALLBACK = {"Chiniot": "Chiniot"}   # district-stations name -> network name, for stations missing from the dashboard feed

DIST = {"Attock": [33.773, 72.362], "Bahawalnagar": [29.618, 73.025], "Bahawalpur": [29.389, 71.728], "Bhakkar": [31.617, 71.08],
 "Chakwal": [32.925, 72.805], "Chiniot": [31.72, 72.989], "DG Khan": [30.052, 70.63], "Faisalabad": [31.436, 73.102],
 "Gujranwala": [32.216, 74.176], "Gujrat": [32.585, 74.079], "Hafizabad": [32.068, 73.711], "Jhang": [31.271, 72.324],
 "Jhelum": [32.943, 73.74], "Kasur": [31.116, 74.467], "Khanewal": [30.302, 71.929], "Khushab": [32.297, 72.352],
 "Kot Addu": [30.503, 70.956], "Lahore": [31.549, 74.364], "Layyah": [30.994, 71.28], "Lodhran": [29.649, 71.775],
 "Mandi Bahauddin": [32.543, 73.48], "Mianwali": [32.584, 71.546], "Multan": [30.214, 71.505], "Murree": [33.905, 73.402],
 "Muzaffargarh": [30.076, 71.19], "Nankana Sahib": [31.448, 73.698], "Narowal": [32.097, 74.894], "Okara": [30.801, 73.426],
 "Pakpattan": [30.362, 73.382], "Rahim Yar Khan": [28.423, 70.318], "Rajanpur": [29.104, 70.33], "Rawalpindi": [33.593, 73.055],
 "Sahiwal": [30.664, 73.106], "Sargodha": [32.055, 72.688], "Sheikhupura": [31.712, 73.976], "Sialkot": [32.407, 74.528],
 "Talagang": [32.928, 72.415], "Taunsa": [30.897, 70.619], "Toba Tek Singh": [30.955, 72.535], "Vehari": [30.05, 72.357],
 "Wazirabad": [32.32, 73.956]}

ICAO = ['OPLA', 'OPFA', 'OPMT', 'OPST', 'OPIS', 'OPRN', 'OPRK', 'OPBW', 'OPDG', 'OPSR', 'OPMI', 'VIAR']
# WMO synoptic stations kept (others found in the blocks are listed in the run report for checking)
WMO = {'41640': 'Lahore PBO', '41641': 'Lahore Airport', '41571': 'Islamabad', '41598': 'Jhelum', '41600': 'Sialkot',
       '41675': 'Multan', '41700': 'Bahawalpur'}
POLF = ['aqi', 'pm25', 'pm10', 'no2', 'so2', 'co', 'o3']


def get(url, timeout=40):
    """GET through the workspace proxy with curl; returns (text or None, error note)."""
    try:
        r = subprocess.run(['curl', '-sS', '-L', '--max-time', str(timeout), '-A', UA, '-w', '\n%{http_code}', url],
                           capture_output=True, text=True, timeout=timeout + 10)
    except Exception as e:
        return None, f'error {e}'
    body, _, code = r.stdout.rpartition('\n')
    if r.returncode != 0 or code != '200':
        return None, f'HTTP {code or "-"} {r.stderr.strip()[:120]}'
    return body, ''


def fnum(x):
    try:
        v = float(x)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


def parse_ts(s):
    s = s.strip().replace('Z', '+00:00')
    s = re.sub(r'\.\d+', '', s)
    t = dt.datetime.fromisoformat(s)
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


# ---------------------------------------------------------------- fetch
def fetch(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc)
    raw = dict(fetched=now.isoformat(timespec='seconds'), src={}, stations=[], metar=[], synop=[], ecm=None)

    # 1. EPA Punjab portal: all stations in one call; fill districts the feed leaves out
    txt, err = get(PORTAL + '/api/dashboard/current')
    if txt:
        try:
            j = json.loads(txt); rows = j.get('data', j) if isinstance(j, dict) else j
            if isinstance(rows, dict): rows = rows.get('stations') or rows.get('data') or []
            raw['stations'] = [r for r in rows if isinstance(r, dict) and 'station_name' in r]
            raw['src']['portal'] = f"ok {len(raw['stations'])} stations"
        except Exception as e:
            raw['src']['portal'] = f'error parsing dashboard feed: {e}'
    else:
        raw['src']['portal'] = 'blocked/unreachable: ' + err
    if raw['stations']:
        have = {r.get('district') for r in raw['stations']}
        dl, _ = get(PORTAL + '/api/districts')
        try:
            dj = json.loads(dl) if dl else {}
            dlist = dj.get('data', dj) if isinstance(dj, dict) else dj
            dnames = [x if isinstance(x, str) else (x.get('district') or x.get('name')) for x in dlist]
        except Exception:
            dnames = []
        for dn in [x for x in dnames if x and x not in have]:
            t2, _ = get(PORTAL + '/api/district-stations/' + dn.replace(' ', '%20'))
            try:
                for r in json.loads(t2).get('data', []):
                    r['district'] = dn; r['_extra'] = True; raw['stations'].append(r)
            except Exception:
                pass

    # 2. Airport METARs (last 6 h), aviationweather.gov data API
    txt, err = get('https://aviationweather.gov/api/data/metar?ids=' + ','.join(ICAO) + '&format=json&hours=6')
    if txt:
        try:
            raw['metar'] = json.loads(txt); raw['src']['metar'] = f"ok {len(raw['metar'])} reports"
        except Exception as e:
            raw['src']['metar'] = f'error {e}'
    else:
        raw['src']['metar'] = 'blocked/unreachable: ' + err

    # 3. WMO SYNOP via Ogimet (blocks 415, 416, 417 cover Punjab), last 7 h UTC
    b, e_ = (now - dt.timedelta(hours=7)).strftime('%Y%m%d%H00'), now.strftime('%Y%m%d%H59')
    lines, notes = [], []
    for blk in ('415', '416', '417'):
        txt, err = get(f'https://www.ogimet.com/cgi-bin/getsynop?block={blk}&begin={b}&end={e_}')
        if txt and 'AAXX' in txt: lines += [l for l in txt.splitlines() if 'AAXX' in l]
        elif txt is None: notes.append(err)
    raw['synop'] = lines
    raw['src']['wmo'] = f'ok {len(lines)} reports' if lines else ('blocked/unreachable: ' + notes[0] if notes else 'no reports')

    # 4. ECMWF IFS 10-m wind at every district centroid (Open-Meteo, one request)
    names = list(DIST)
    url = ('https://api.open-meteo.com/v1/forecast?latitude=' + ','.join(str(DIST[n][0]) for n in names) +
           '&longitude=' + ','.join(str(DIST[n][1]) for n in names) +
           '&hourly=wind_speed_10m,wind_direction_10m&models=ecmwf_ifs025&wind_speed_unit=ms&timezone=Asia%2FKarachi&past_days=1&forecast_days=1')
    txt, err = get(url, 60)
    if txt:
        try:
            j = json.loads(txt); j = j if isinstance(j, list) else [j]
            raw['ecm'] = {n: dict(time=x['hourly']['time'], ws=x['hourly']['wind_speed_10m'], wd=x['hourly']['wind_direction_10m'])
                          for n, x in zip(names, j)}
            raw['src']['ecmwf'] = f'ok {len(j)} points'
        except Exception as e:
            raw['src']['ecmwf'] = f'error {e}'
    else:
        raw['src']['ecmwf'] = 'blocked/unreachable: ' + err

    # hours to write: each PKT hour stamped by portal stations (last 6 h); else nothing new
    hrs = set()
    for r in raw['stations']:
        try:
            h = parse_ts(r['timestamp']).astimezone(PKT).replace(minute=0, second=0)
            if now - h <= dt.timedelta(hours=6): hrs.add(h.strftime('%Y-%m-%d %H:00'))
        except Exception:
            pass
    if not raw['stations']:
        # portal down: still record winds for the last completed PKT hour so the wind table keeps going
        hrs.add((now.astimezone(PKT) - dt.timedelta(hours=1)).replace(minute=0, second=0).strftime('%Y-%m-%d %H:00'))
    raw['hours'] = sorted(hrs)
    json.dump(raw, open(out / 'raw.json', 'w'))
    ids = ['h' + h.replace('-', '').replace(' ', '')[:10] for h in raw['hours']]
    print(json.dumps(dict(status=raw['src'], hours=raw['hours'], doc_ids=ids, t_values=raw['hours'])))


# ---------------------------------------------------------------- build
def synop_wind(line):
    """'41640,2026,11,03,00,00,AAXX 03001 41640 32970 70000 ...' -> (id, obs UTC iso, dir|None, m/s)"""
    p = line.split(',')
    if len(p) < 7: return None
    try:
        t = dt.datetime(int(p[1]), int(p[2]), int(p[3]), int(p[4]), int(p[5]), tzinfo=dt.timezone.utc)
    except ValueError:
        return None
    g = ','.join(p[6:]).replace('=', ' ').split()
    if len(g) < 5 or g[0] != 'AAXX': return None
    iw, sid, nddff = g[1][-1], g[2], g[4]
    if not re.fullmatch(r'\d{5}', nddff) or not re.fullmatch(r'\d{5}', sid): return None
    dd, ff = int(nddff[1:3]), int(nddff[3:5])
    if ff == 99 and len(g) > 5 and g[5].startswith('00'): ff = int(g[5][2:5])
    if dd == 99 or dd > 36: d_ = None
    else: d_ = 0 if dd == 0 else dd * 10
    ms = ff * 0.5144 if iw in '34' else ff if iw in '01' else None
    if ms is None: return None
    return sid, t.isoformat(timespec='minutes'), d_, round(ms, 1)


def build(out, existing):
    out = Path(out); raw = json.load(open(out / 'raw.json')); ex = Path(existing) if existing else None
    (out / 'docs').mkdir(exist_ok=True)
    unknown, flagged, wmo_other = [], 0, set()
    by_hour = {h: dict(st={}, ap={}, wmo={}, ecm={}) for h in raw['hours']}

    for r in raw['stations']:
        try: h = parse_ts(r['timestamp']).astimezone(PKT).strftime('%Y-%m-%d %H:00')
        except Exception: h = raw['hours'][-1] if r.get('_extra') and raw['hours'] else None
        if h not in by_hour: continue
        name = PMAP.get(str(r.get('station_id'))) or NAME_FALLBACK.get(r.get('station_name'))
        if not name:
            unknown.append(f"{r.get('station_id')} {r.get('station_name')} ({r.get('district')})"); continue
        vals = [fnum(r.get(k)) for k in POLF]
        fl = r.get('pollutant_flags')
        if fl:
            s = json.dumps(fl).lower()
            for i, k in enumerate(POLF):
                if k in s or k.replace('pm25', 'pm2.5') in s: vals[i] = None; flagged += 1
        vals += [fnum(r.get('wind_speed')), fnum(r.get('wind_direction'))]
        by_hour[h]['st'][name] = [None if v is None else round(v, 3) for v in vals]

    # METAR: report nearest each hour (within 35 min)
    for h, doc in by_hour.items():
        hc = dt.datetime.strptime(h, '%Y-%m-%d %H:00').replace(tzinfo=PKT)
        best = {}
        for m in raw.get('metar') or []:
            try: ot = dt.datetime.fromtimestamp(int(m['obsTime']), dt.timezone.utc)
            except Exception:
                try: ot = parse_ts(m.get('reportTime', ''))
                except Exception: continue
            gap = abs((ot - hc).total_seconds())
            if gap > 35 * 60: continue
            ic = m.get('icaoId')
            if ic not in best or gap < best[ic][0]: best[ic] = (gap, m, ot)
        for ic, (_, m, ot) in best.items():
            wd, ws = m.get('wdir'), m.get('wspd')
            d_ = 'VRB' if wd == 'VRB' else ('CALM' if (ws in (0, None) and wd in (0, None)) else fnum(wd))
            vis = m.get('visib'); vm = None
            if isinstance(vis, (int, float)): vm = round(vis * 1609.34)
            elif isinstance(vis, str) and vis.rstrip('+').replace('.', '', 1).isdigit(): vm = round(float(vis.rstrip('+')) * 1609.34)
            rawob = m.get('rawOb') or ''
            mv = re.search(r'\s(\d{4})\s', rawob)          # visibility group in metres, if reported that way
            if mv: vm = int(mv.group(1))
            wx = m.get('wxString') or ''
            WXN = {'FU': 'smoke', 'HZ': 'haze', 'BR': 'mist', 'FG': 'fog', 'DU': 'dust', 'RA': 'rain', 'TS': 'thunderstorm'}
            wxt = ', '.join(v for k, v in WXN.items() if k in wx)
            doc['ap'][ic] = [d_, fnum(ws) or 0, vm, fnum(m.get('temp')), wxt, fnum(m.get('wgst')), ot.isoformat(timespec='minutes')]

    # WMO SYNOP
    for line in raw.get('synop') or []:
        w = synop_wind(line)
        if not w: continue
        sid, ts, d_, ms = w
        if sid not in WMO: wmo_other.add(sid); continue
        h = dt.datetime.fromisoformat(ts).astimezone(PKT).strftime('%Y-%m-%d %H:00')
        if h in by_hour: by_hour[h]['wmo'][sid] = [d_, ms, ts]

    # ECMWF
    for n, e in (raw.get('ecm') or {}).items():
        idx = {t.replace('T', ' '): i for i, t in enumerate(e['time'])}
        for h, doc in by_hour.items():
            i = idx.get(h)
            if i is not None and e['ws'][i] is not None: doc['ecm'][n] = [round(e['ws'][i], 2), e['wd'][i]]

    writes, summary = [], []
    for h, new in by_hour.items():
        did = 'h' + h.replace('-', '').replace(' ', '')[:10]
        old, ver = {}, None
        if ex and (ex / f'{did}.json').exists():
            o = json.load(open(ex / f'{did}.json')); ver = o.get('version'); old = o.get('data', o)
        doc = dict(t=h, st={**old.get('st', {}), **new['st']}, ap={**old.get('ap', {}), **new['ap']},
                   wmo={**old.get('wmo', {}), **new['wmo']}, ecm={**old.get('ecm', {}), **new['ecm']},
                   src=raw['src'], upd=raw['fetched'])
        if not any((doc['st'], doc['ap'], doc['wmo'], doc['ecm'])): continue
        f = out / 'docs' / f'{did}.json'; json.dump(doc, open(f, 'w'), separators=(',', ':'))
        w = dict(op='set', collection='hours', doc_id=did, file_path=str(f.resolve()))
        if ver: w['if_version'] = ver
        writes.append(w)
        summary.append(f"{h}: {len(doc['st'])} stations, {len(doc['ap'])} METAR, {len(doc['wmo'])} WMO, {len(doc['ecm'])} ECMWF")
    json.dump(writes, open(out / 'batch.json', 'w'), indent=1)
    top = []
    if raw['hours']:
        last = by_hour[raw['hours'][-1]]['st']
        top = sorted(((v[0], k) for k, v in last.items() if v[0] is not None), reverse=True)[:5]
    print(json.dumps(dict(status=raw['src'], writes=len(writes), hours=summary, unmapped_stations=unknown,
                          flagged_values=flagged, other_wmo_ids=sorted(wmo_other), top_aqi_latest=top), indent=1))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'fetch': fetch(sys.argv[2])
    elif cmd == 'build': build(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
