// Builds ui-mock/cams-boundary.js from the Punjab outline and Copernicus CAMS
// global PM2.5 (Open-Meteo). Reads the baseline. Does not modify application source.
import fs from "fs";
import path from "path";

const root = path.resolve(import.meta.dirname, "..");
const baseline = JSON.parse(fs.readFileSync(path.join(root, "data/baseline/baseline_data.json"), "utf8"));
const hoursAll = baseline.hours;
const start = Math.max(0, hoursAll.length - 72);
const hours = hoursAll.slice(start);

function ringHas(ring, lon, lat) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0];
    const yi = ring[i][1];
    const xj = ring[j][0];
    const yj = ring[j][1];
    if ((yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

const polygons = [];
for (const meta of Object.values(baseline.districts)) {
  const boundary = meta.boundary || meta.polys;
  if (!Array.isArray(boundary) || !boundary.length) continue;
  if (typeof boundary[0][0][0] === "number") polygons.push(boundary);
  else for (const poly of boundary) polygons.push(poly);
}

function inProvince(lon, lat) {
  for (const poly of polygons) {
    if (!poly.length || !ringHas(poly[0], lon, lat)) continue;
    let hole = false;
    for (let h = 1; h < poly.length; h++) if (ringHas(poly[h], lon, lat)) hole = true;
    if (!hole) return true;
  }
  return false;
}

const lon0 = 69.2;
const lat0 = 27.6;
const dLon = 0.045;
const dLat = 0.045;
const cols = Math.ceil((76.2 - lon0) / dLon);
const rows = Math.ceil((34.6 - lat0) / dLat);
const grid = new Uint8Array(cols * rows);
for (let j = 0; j < rows; j++) {
  const lat = lat0 + (j + 0.5) * dLat;
  for (let i = 0; i < cols; i++) {
    const lon = lon0 + (i + 0.5) * dLon;
    if (inProvince(lon, lat)) grid[j * cols + i] = 1;
  }
}
const cell = (i, j) => i >= 0 && j >= 0 && i < cols && j < rows && grid[j * cols + i] === 1;

function cornerKey(i, j) {
  return `${i},${j}`;
}
const nexts = new Map();
function addEdge(i0, j0, i1, j1) {
  const ka = cornerKey(i0, j0);
  const kb = cornerKey(i1, j1);
  if (!nexts.has(ka)) nexts.set(ka, []);
  nexts.get(ka).push(kb);
}
for (let j = 0; j < rows; j++) {
  for (let i = 0; i < cols; i++) {
    if (!cell(i, j)) continue;
    if (!cell(i, j - 1)) addEdge(i, j, i + 1, j);
    if (!cell(i, j + 1)) addEdge(i + 1, j + 1, i, j + 1);
    if (!cell(i - 1, j)) addEdge(i, j + 1, i, j);
    if (!cell(i + 1, j)) addEdge(i + 1, j, i + 1, j + 1);
  }
}

const used = new Set();
const loops = [];
for (const startKey of nexts.keys()) {
  if ([...nexts.get(startKey)].every((n) => used.has(`${startKey}>${n}`))) continue;
  const loop = [];
  let key = startKey;
  let guard = 0;
  while (guard++ < 20000) {
    const options = (nexts.get(key) || []).filter((n) => !used.has(`${key}>${n}`));
    if (!options.length) break;
    const nxt = options[0];
    used.add(`${key}>${nxt}`);
    const [ci, cj] = key.split(",").map(Number);
    loop.push([lon0 + ci * dLon, lat0 + cj * dLat]);
    key = nxt;
    if (key === startKey) break;
  }
  if (loop.length > 30) loops.push(loop);
}

function area(loop) {
  let sum = 0;
  for (let i = 0; i < loop.length; i++) {
    const a = loop[i];
    const b = loop[(i + 1) % loop.length];
    sum += a[0] * b[1] - b[0] * a[1];
  }
  return sum / 2;
}

loops.sort((a, b) => Math.abs(area(b)) - Math.abs(area(a)));
const outline = loops[0];
if (!outline || outline.length < 40) {
  console.error("province outline failed", loops.map((l) => l.length));
  process.exit(1);
}

function km(lon1, lat1, lon2, lat2) {
  const r = 6371;
  const p1 = (lat1 * Math.PI) / 180;
  const p2 = (lat2 * Math.PI) / 180;
  const dp = ((lat2 - lat1) * Math.PI) / 180;
  const dl = ((lon2 - lon1) * Math.PI) / 180;
  const a = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
  return 2 * r * Math.asin(Math.min(1, Math.sqrt(a)));
}

const cum = [0];
for (let i = 1; i < outline.length; i++) {
  cum.push(cum[i - 1] + km(outline[i - 1][0], outline[i - 1][1], outline[i][0], outline[i][1]));
}
const total = cum[cum.length - 1] + km(outline[outline.length - 1][0], outline[outline.length - 1][1], outline[0][0], outline[0][1]);
const N = 117;
const step = total / N;
const ccw = area(outline) > 0;

function pointAt(dist) {
  let d = ((dist % total) + total) % total;
  if (d > cum[cum.length - 1]) {
    const a = outline[outline.length - 1];
    const b = outline[0];
    const seg = km(a[0], a[1], b[0], b[1]) || 1;
    const t = (d - cum[cum.length - 1]) / seg;
    return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, b[0] - a[0], b[1] - a[1]];
  }
  let lo = 0;
  let hi = cum.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (cum[mid] < d) lo = mid + 1;
    else hi = mid;
  }
  const i = Math.max(1, lo);
  const seg = cum[i] - cum[i - 1] || 1;
  const t = (d - cum[i - 1]) / seg;
  const a = outline[i - 1];
  const b = outline[i];
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, b[0] - a[0], b[1] - a[1]];
}

function sideOf(lon, lat, nx, ny) {
  // East-facing arc is India. The south edge is Sindh. The west edge splits
  // into Balochistan and Khyber Pakhtunkhwa. Staircase normals are ignored
  // where the position already decides the side.
  if (nx > 0.5 && lon > 73 && lat >= 29.15 && lat < 32.25) {
    return lat < 30.2 ? "Rajasthan" : "Indian Punjab";
  }
  if (lat >= 32.2 && lon >= 73.95 && (nx > 0.3 || ny > 0.3)) return "Jammu";
  if (lat < 29.25 && lon < 73.15) return "Sindh";
  if (ny < -0.5 && lat < 29.4) return "Sindh";
  if (lat < 30.25 && lon > 73.2 && lat >= 29.15) return "Rajasthan";
  if (lat > 33.55 && lon >= 72.85 && lon <= 73.55) return "Islamabad";
  if (lat > 32.75 && lon >= 73.35 && lon < 74.15) return "Azad Kashmir";
  if (lon < 71.35 && lat < 31.55) return "Balochistan";
  return "Khyber Pakhtunkhwa";
}

const points = [];
for (let i = 0; i < N; i++) {
  const [lon, lat, dx, dy] = pointAt(i * step + step * 0.5);
  const cos = Math.cos((lat * Math.PI) / 180);
  let ex = dx * cos;
  let ny = dy;
  const mag = Math.hypot(ex, ny) || 1;
  ex /= mag;
  ny /= mag;
  let nx = ccw ? ny : -ny;
  let nny = ccw ? -ex : ex;
  const side = sideOf(lon, lat, nx, nny);
  points.push({
    lon: Math.round(lon * 1000) / 1000,
    lat: Math.round(lat * 1000) / 1000,
    nx: Math.round(nx * 1000) / 1000,
    ny: Math.round(nny * 1000) / 1000,
    side,
  });
}

const counts = {};
for (const p of points) counts[p.side] = (counts[p.side] || 0) + 1;
console.log(`outline ${outline.length} pts, perimeter ${total.toFixed(0)} km, ccw ${ccw}`);
console.log("sides", counts);

const startDate = hours[0].slice(0, 10);
const endDate = hours[hours.length - 1].slice(0, 10);

async function fetchBatch(batch) {
  const lat = batch.map((p) => p.lat).join(",");
  const lon = batch.map((p) => p.lon).join(",");
  const url = `https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${lat}&longitude=${lon}&hourly=pm2_5&domains=cams_global&start_date=${startDate}&end_date=${endDate}&timezone=GMT`;
  const res = await fetch(url);
  const text = await res.text();
  if (!res.ok) throw new Error(`CAMS ${res.status}: ${text.slice(0, 280)}`);
  return JSON.parse(text);
}

const pm = Array.from({ length: hours.length }, () => new Array(points.length).fill(null));
const batchSize = 12;
for (let i = 0; i < points.length; i += batchSize) {
  const batch = points.slice(i, i + batchSize);
  const body = await fetchBatch(batch);
  const rows = Array.isArray(body) ? body : [body];
  if (rows.length !== batch.length) throw new Error(`expected ${batch.length} locations, got ${rows.length}`);
  rows.forEach((row, j) => {
    const times = row.hourly.time;
    const values = row.hourly.pm2_5;
    const byTime = new Map(times.map((t, k) => [t.slice(0, 13), values[k]]));
    hours.forEach((h, hi) => {
      const v = byTime.get(h.replace(" ", "T").slice(0, 13));
      pm[hi][i + j] = v == null || Number.isNaN(Number(v)) ? null : Math.round(Number(v) * 10) / 10;
    });
  });
  console.log(`fetched ${Math.min(i + batchSize, points.length)}/${points.length}`);
}

const known = pm[pm.length - 1].filter((v) => v != null).length;
if (known < points.length * 0.8) {
  console.error(`CAMS series is missing values (${known}/${points.length} on the last hour)`);
  process.exit(1);
}

const out = {
  source: "CAMS global PM2.5 via Open-Meteo air-quality, domains=cams_global",
  hours: hours.map((h) => h.slice(5, 16)),
  points,
  pm,
};
const dest = path.join(import.meta.dirname, "cams-boundary.js");
fs.writeFileSync(dest, "window.CAMS = " + JSON.stringify(out) + ";\n");
console.log(`wrote ${dest} ${(fs.statSync(dest).size / 1024).toFixed(0)} KB, last hour sample ${pm[pm.length - 1].slice(0, 4).join(", ")}`);
