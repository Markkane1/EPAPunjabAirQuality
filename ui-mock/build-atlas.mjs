// Builds ui-mock/atlas.js from the local baseline and Natural Earth 50m.
// Reads only. Does not modify application source.
import fs from "fs";
import path from "path";
import os from "os";

const root = path.resolve(import.meta.dirname, "..");
const baseline = JSON.parse(fs.readFileSync(path.join(root, "data/baseline/baseline_data.json"), "utf8"));
const stationFile = JSON.parse(fs.readFileSync(path.join(root, "data/baseline/stations.json"), "utf8"));
const geo = JSON.parse(fs.readFileSync(path.join(os.tmpdir(), "ne_50m_admin_0_countries.geojson"), "utf8"));

const COUNTRIES = ["Pakistan", "India", "Afghanistan", "Iran", "China"];

// Pakistan and the countries on its border. China, India, and Iran continue
// past the frame, so the camera cannot open onto the rest of the region.
const frame = { lo0: 59.0, lo1: 78.8, la0: 23.2, la1: 38.7 };

function distPointSeg(p, a, b) {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const l2 = dx * dx + dy * dy;
  if (l2 === 0) return (p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2;
  let t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2;
  t = Math.max(0, Math.min(1, t));
  const x = a[0] + t * dx;
  const y = a[1] + t * dy;
  return (p[0] - x) ** 2 + (p[1] - y) ** 2;
}

function simplify(pts, eps) {
  if (pts.length < 4) return pts;
  const e2 = eps * eps;
  const out = [pts[0]];
  (function rec(a, b) {
    let maxD = 0;
    let idx = -1;
    for (let i = a + 1; i < b; i++) {
      const d = distPointSeg(pts[i], pts[a], pts[b]);
      if (d > maxD) {
        maxD = d;
        idx = i;
      }
    }
    if (idx !== -1 && maxD > e2) {
      rec(a, idx);
      rec(idx, b);
    } else out.push(pts[b]);
  })(0, pts.length - 1);
  return out;
}

function collectRings(node, acc) {
  if (!Array.isArray(node) || node.length === 0) return;
  if (typeof node[0] === "number") return;
  if (Array.isArray(node[0]) && typeof node[0][0] === "number") {
    acc.push(node);
    return;
  }
  for (const child of node) collectRings(child, acc);
}

function cleanRing(ring, eps) {
  const pts = ring
    .filter((p) => Array.isArray(p) && Number.isFinite(p[0]) && Number.isFinite(p[1]))
    .map((p) => [Math.round(p[0] * 1000) / 1000, Math.round(p[1] * 1000) / 1000]);
  if (pts.length < 4) return null;
  const simplified = simplify(pts, eps);
  if (simplified.length < 4) return null;
  const first = simplified[0];
  const last = simplified[simplified.length - 1];
  if (first[0] !== last[0] || first[1] !== last[1]) simplified.push([first[0], first[1]]);
  return simplified;
}

function ringsOf(geometry, eps) {
  const raw = [];
  collectRings(geometry.coordinates, raw);
  return raw.map((ring) => cleanRing(ring, eps)).filter(Boolean);
}

const countries = [];
for (const feature of geo.features) {
  const name = feature.properties.NAME || feature.properties.ADMIN;
  if (!COUNTRIES.includes(name)) continue;
  const eps = name === "China" || name === "India" || name === "Iran" ? 0.08 : 0.05;
  const rings = ringsOf(feature.geometry, eps);
  if (!rings.length) continue;
  let sx = 0;
  let sy = 0;
  let n = 0;
  for (const ring of rings) {
    for (const p of ring) {
      sx += p[0];
      sy += p[1];
      n++;
    }
  }
  countries.push({ name, lon: Math.round((sx / n) * 100) / 100, lat: Math.round((sy / n) * 100) / 100, rings });
}

const hoursAll = baseline.hours;
const start = Math.max(0, hoursAll.length - 72);
const hours = hoursAll.slice(start).map((h) => h.slice(5, 16));

function nearestWind(lon, lat, hour) {
  const las = baseline.ecm.la;
  const los = baseline.ecm.lo;
  let best = Infinity;
  let n = 0;
  let near = Infinity;
  for (let j = 0; j < las.length; j++) {
    for (let i = 0; i < los.length; i++) {
      const dlat = las[j] - lat;
      const dlon = los[i] - lon;
      const d = dlat * dlat + dlon * dlon;
      if (d < best) {
        best = d;
        near = Math.sqrt(d);
        n = j * los.length + i;
      }
    }
  }
  if (near > 0.75) return [null, null, null, null];
  const r = (x) => (x == null || !Number.isFinite(Number(x)) ? null : Math.round(Number(x) * 100) / 100);
  return [
    r(baseline.ecm.u10[hour][n]),
    r(baseline.ecm.v10[hour][n]),
    r(baseline.ecm.u925[hour][n]),
    r(baseline.ecm.v925[hour][n]),
  ];
}

function windSeries(lon, lat) {
  const out = [];
  for (let h = start; h < hoursAll.length; h++) out.push(nearestWind(lon, lat, h));
  return out;
}

function seriesFrom(arr) {
  if (!Array.isArray(arr)) return null;
  return arr.slice(start).map((v) => {
    const n = Array.isArray(v) ? v[0] : v;
    if (n == null || !Number.isFinite(Number(n))) return null;
    return Math.round(Number(n) * 10) / 10;
  });
}

const POLS = ["AQI", "PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "NO", "NOX"];

const byName = new Map(stationFile.map((s) => [s.name, s]));

const stations = [];
for (const name of Object.keys(baseline.pol.AQI.stations)) {
  const meta = byName.get(name);
  if (!meta) continue;
  const series = {};
  for (const pol of POLS) series[pol] = seriesFrom(baseline.pol[pol].stations[name]);
  stations.push({
    name,
    id: String(meta.station_id || meta.id || ""),
    district: meta.district,
    lon: meta.lon,
    lat: meta.lat,
    mobile: !!meta.mobile,
    network: meta.network_type || (meta.mobile ? "mobile" : "fixed"),
    coordSource: meta.coord_source || "",
    series,
    wind: windSeries(meta.lon, meta.lat),
  });
}

const districtMeta = baseline.districts;
const districts = [];
for (const name of Object.keys(districtMeta)) {
  const meta = districtMeta[name];
  const raw = [];
  collectRings(meta.boundary || meta.polys, raw);
  const rings = raw.map((ring) => cleanRing(ring, 0.025)).filter(Boolean);
  const members = stations.filter((s) => s.district === name || s.district === meta.name);
  const series = {};
  for (const pol of POLS) {
    series[pol] = hours.map((_, i) => {
      const vals = members.map((s) => s.series[pol][i]).filter((v) => v != null);
      if (!vals.length) return null;
      return Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 10) / 10;
    });
  }
  districts.push({
    name,
    lon: meta.lon ?? meta.longitude,
    lat: meta.lat ?? meta.latitude,
    rings,
    series,
    wind: windSeries(meta.lon ?? meta.longitude, meta.lat ?? meta.latitude),
  });
}

const lahore = districts.find((d) => d.name === "Lahore");
const anchors = [
  ["Amritsar", "Punjab, India", 74.87, 31.64, 0.96],
  ["Ludhiana", "Punjab, India", 75.85, 30.9, 0.9],
  ["Chandigarh", "Chandigarh", 76.78, 30.73, 0.84],
  ["Delhi", "Delhi", 77.21, 28.61, 0.8],
  ["Jaipur", "Rajasthan", 75.79, 26.91, 0.7],
  ["Srinagar", "Jammu and Kashmir", 74.8, 34.08, 0.52],
].map(([name, place, lon, lat, k]) => ({
  name,
  place,
  lon,
  lat,
  kind: "anchor",
  wind: windSeries(lon, lat),
  series: {
    AQI: lahore.series.AQI.map((v, i) => (v == null ? null : Math.round(v * k + Math.sin(i / 5) * 6))),
  },
}));

const airports = baseline.airports.map((a) => ({
  id: a.icao || a.id,
  name: a.name,
  lon: a.lon,
  lat: a.lat,
  u: a.u.slice(start).map((v) => Math.round(v * 100) / 100),
  v: a.v.slice(start).map((v) => Math.round(v * 100) / 100),
}));

const border = simplify(baseline.tbgeo.border, 0.03).map((p) => [
  Math.round(p[0] * 1000) / 1000,
  Math.round(p[1] * 1000) / 1000,
]);

const fireFile = JSON.parse(
  fs.readFileSync(path.join(root, "data/baseline/fire_anomalies_history.json"), "utf8"),
);
const origin = Date.parse(hoursAll[start].replace(" ", "T") + "Z");
const fires = [];
for (const f of fireFile.fires) {
  // Rajasthan petrochemical flares sit south of 27°N and are not crop fires.
  if ((f.region || "").includes("Rajasthan") && f.latitude < 27) continue;
  const hh = String(f.acq_time || "0000").padStart(4, "0");
  const stamp = Date.parse(`${f.acq_date}T${hh.slice(0, 2)}:${hh.slice(2, 4)}:00Z`);
  if (!Number.isFinite(stamp)) continue;
  const h = (stamp - origin) / 3600000;
  // Keep the pass before the episode so the first hours still have a trail.
  if (h < -18 || h > hours.length) continue;
  fires.push({
    lon: Math.round(f.longitude * 1000) / 1000,
    lat: Math.round(f.latitude * 1000) / 1000,
    frp: Math.round((f.frp || 0) * 10) / 10,
    bright: Math.round((f.brightness || 0) * 10) / 10,
    scan: Math.round((f.scan || 0.4) * 1000) / 1000,
    track: Math.round((f.track || 0.4) * 1000) / 1000,
    h: Math.round(h * 10) / 10,
    region: f.region || "Other",
    conf: f.confidence || "nominal",
    sat: f.satellite || "",
    day: f.daynight || "",
  });
}
fires.sort((a, b) => a.h - b.h);

const province = {
  AQI: seriesFrom(baseline.pol.AQI.series.map((pair) => pair[0])),
};

const atlas = {
  frame,
  hours,
  hourLabel: "1–9 Nov 2026 baseline, last 72 hours",
  countries,
  districts,
  stations,
  anchors,
  airports,
  border,
  fires,
  province,
};

const out = path.join(import.meta.dirname, "atlas.js");
fs.writeFileSync(out, "window.ATLAS = " + JSON.stringify(atlas) + ";\n");
const kb = Math.round(fs.statSync(out).size / 1024);
console.log(
  `atlas.js ${kb} KB · countries ${countries.length} · districts ${districts.length} · stations ${stations.length} · hours ${hours.length} · fires ${fires.length}`,
);
