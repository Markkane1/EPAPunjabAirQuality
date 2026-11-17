// Pollution corridors for the mock. PM2.5 mass only. At most two paths.
// Inside Punjab the hops follow the ECMWF wind. Outside, the concentration
// is the Copernicus CAMS value at the boundary point.
(function () {
  const CALM = 0.5;
  const CONE = 35;
  const MAX_KM = 180;
  const DECAY = 100;
  const NORMAL = 0.25;
  const BELT = 120;
  const COMPASS = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"];

  function km(lon1, lat1, lon2, lat2) {
    const r = 6371;
    const p1 = (lat1 * Math.PI) / 180;
    const p2 = (lat2 * Math.PI) / 180;
    const dp = ((lat2 - lat1) * Math.PI) / 180;
    const dl = ((lon2 - lon1) * Math.PI) / 180;
    const a = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
    return 2 * r * Math.asin(Math.min(1, Math.sqrt(Math.max(0, a))));
  }
  function bearingTo(lon1, lat1, lon2, lat2) {
    const p1 = (lat1 * Math.PI) / 180;
    const p2 = (lat2 * Math.PI) / 180;
    const dl = ((lon2 - lon1) * Math.PI) / 180;
    const y = Math.sin(dl) * Math.cos(p2);
    const x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl);
    return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
  }
  function angDiff(a, b) {
    return Math.abs((((a - b + 180) % 360) + 360) % 360 - 180);
  }
  function windTo(u, v) {
    if (!u && !v) return 0;
    return (Math.atan2(u, v) * 180 / Math.PI + 360) % 360;
  }
  function compass(bearing) {
    return COMPASS[Math.round((((bearing % 360) + 360) % 360) / 45) % 8];
  }
  function pmOf(d, hour) {
    const series = d.series && d.series["PM2.5"];
    if (!series) return null;
    const v = series[hour];
    return v == null || !Number.isFinite(+v) ? null : +v;
  }

  let cacheKey = "";
  let cache = { paths: [] };

  function compute(hour) {
    window.corridorHour = hour;
    try {
      return computeBody(hour);
    } finally {
      window.corridorHour = null;
    }
  }
  function computeBody(hour) {
    const flow = window.flow;
    const cams = window.CAMS;
    const atlas = window.ATLAS;
    if (typeof flow !== "function" || !cams || !atlas) return { paths: [] };
    const list = atlas.districts.filter((d) => Number.isFinite(d.lon) && Number.isFinite(d.lat));
    const hops = [];
    for (let i = 0; i < list.length; i++) {
      const a = list[i];
      const c = pmOf(a, hour);
      if (!(c > 0)) continue;
      const wind = flow(a.lon, a.lat);
      const u = wind[0];
      const v = wind[1];
      const speed = Math.hypot(u, v);
      if (speed < CALM) continue;
      const wto = windTo(u, v);
      for (let j = 0; j < list.length; j++) {
        if (i === j) continue;
        const b = list[j];
        const dist = km(a.lon, a.lat, b.lon, b.lat);
        if (dist <= 1 || dist > MAX_KM) continue;
        const theta = bearingTo(a.lon, a.lat, b.lon, b.lat);
        const delta = angDiff(wto, theta);
        if (delta > CONE) continue;
        const flux = c * speed * Math.cos((delta * Math.PI) / 180) * Math.exp(-dist / DECAY);
        if (!(flux > 0)) continue;
        hops.push({
          from: a.name, to: b.name, flux, km: dist, bearing: theta,
          fromLon: a.lon, fromLat: a.lat, toLon: b.lon, toLat: b.lat,
        });
      }
    }

    const out = new Map();
    const inn = new Map();
    for (const h of hops) {
      if (!out.has(h.from)) out.set(h.from, []);
      out.get(h.from).push(h);
      if (!inn.has(h.to)) inn.set(h.to, []);
      inn.get(h.to).push(h);
    }
    for (const arr of out.values()) arr.sort((a, b) => b.flux - a.flux);
    for (const arr of inn.values()) arr.sort((a, b) => b.flux - a.flux);
    const used = new Set();
    const edgeKey = (h) => h.from + ">" + h.to;
    const paths = [];
    const seeds = hops.slice().sort((a, b) => b.flux - a.flux);
    for (const seed of seeds) {
      if (used.has(edgeKey(seed))) continue;
      const edges = [seed];
      used.add(edgeKey(seed));
      let guard = 0;
      while (guard++ < 5) {
        const prev = edges[edges.length - 1];
        const next = (out.get(prev.to) || []).find((h) => !used.has(edgeKey(h)) && angDiff(h.bearing, prev.bearing) <= 40 && h.flux >= seed.flux * 0.35);
        if (!next) break;
        used.add(edgeKey(next));
        edges.push(next);
      }
      guard = 0;
      while (guard++ < 5) {
        const prev = edges[0];
        const back = (inn.get(prev.from) || []).find((h) => !used.has(edgeKey(h)) && angDiff(h.bearing, prev.bearing) <= 40 && h.flux >= seed.flux * 0.35);
        if (!back) break;
        used.add(edgeKey(back));
        edges.unshift(back);
      }
      paths.push({ edges, score: Math.max(...edges.map((e) => e.flux)), crossing: null });
    }
    paths.sort((a, b) => b.score - a.score);

    const crosses = [];
    cams.points.forEach((p, i) => {
      const wind = flow(p.lon, p.lat);
      const u = wind[0];
      const v = wind[1];
      const speed = Math.hypot(u, v);
      if (speed < CALM) return;
      const outward = u * p.nx + v * p.ny;
      let kind = null;
      let normal = 0;
      if (outward <= -NORMAL) {
        kind = "in";
        normal = -outward;
      } else if (outward >= NORMAL) {
        kind = "out";
        normal = outward;
      } else return;
      let near = null;
      let best = Infinity;
      for (const d of list) {
        const dist = km(p.lon, p.lat, d.lon, d.lat);
        if (dist < best) {
          best = dist;
          near = d;
        }
      }
      if (!near || best > BELT) return;
      const theta = kind === "in"
        ? bearingTo(p.lon, p.lat, near.lon, near.lat)
        : bearingTo(near.lon, near.lat, p.lon, p.lat);
      if (angDiff(windTo(u, v), theta) > CONE) return;
      const conc = kind === "in" ? cams.pm[hour][i] : pmOf(near, hour);
      if (!(conc > 0)) return;
      crosses.push({
        lon: p.lon, lat: p.lat, side: p.side, kind, km: best, district: near.name,
        flux: conc * normal * Math.exp(-best / DECAY),
      });
    });
    crosses.sort((a, b) => b.flux - a.flux);

    const taken = new Set();
    for (const path of paths) {
      const names = new Set();
      for (const e of path.edges) {
        names.add(e.from);
        names.add(e.to);
      }
      const hit = crosses.find((c, n) => !taken.has(n) && names.has(c.district));
      if (!hit) continue;
      path.crossing = hit;
      taken.add(crosses.indexOf(hit));
    }
    const loose = crosses.filter((_, n) => !taken.has(n));

    const chosen = [];
    const namesOf = (p) => {
      const s = new Set();
      for (const e of p.edges) {
        s.add(e.from);
        s.add(e.to);
      }
      if (p.crossing) s.add(p.crossing.district);
      return s;
    };
    for (const path of paths) {
      if (chosen.length >= 2) break;
      if (chosen.length === 1) {
        const a = namesOf(chosen[0]);
        const b = namesOf(path);
        let share = 0;
        for (const n of b) if (a.has(n)) share++;
        if (b.size && share > b.size * 0.5) continue;
      }
      chosen.push(path);
    }
    for (const c of loose) {
      if (chosen.length >= 2) break;
      if (c.flux < 12) break;
      if (chosen.some((p) => namesOf(p).has(c.district))) continue;
      chosen.push({ edges: [], score: c.flux, crossing: c, standalone: true });
    }
    return { paths: chosen };
  }

  function frame(hour) {
    const key = String(hour);
    if (key === cacheKey) return cache;
    cacheKey = key;
    cache = compute(hour);
    return cache;
  }

  function nodesOf(path) {
    if (!path.edges.length) return path.crossing ? [path.crossing.district] : [];
    const nodes = [path.edges[0].from];
    for (const e of path.edges) nodes.push(e.to);
    return nodes;
  }

  function speak(hour, name) {
    if (!name) return { inside: null, outside: null, hops: [] };
    const paths = frame(hour).paths;
    const hits = paths.filter((p) => nodesOf(p).includes(name));
    if (!hits.length) return { inside: null, outside: null, hops: [] };
    const path = hits.sort((a, b) => nodesOf(b).length - nodesOf(a).length)[0];
    const nodes = nodesOf(path);
    const at = nodes.indexOf(name);
    let inside = null;
    if (path.edges.length && at === nodes.length - 1) {
      const hop = path.edges[path.edges.length - 1];
      inside = `Receiving from the ${compass(hop.bearing + 180)} through ${hop.from}.`;
    } else if (path.edges.length && at === 0) {
      inside = `Sending on toward ${path.edges[0].to}.`;
    } else if (path.edges.length && at > 0) {
      inside = `Passing through toward ${path.edges[at].to}.`;
    }
    let outside = null;
    if (path.crossing) {
      outside = path.crossing.kind === "in"
        ? `Coming in from ${path.crossing.side}.`
        : `Leaving toward ${path.crossing.side}.`;
    }
    const hops = [];
    if (path.crossing) {
      const c = path.crossing;
      hops.push(c.kind === "in" ? `${c.side} → ${c.district} · crossing` : `${c.district} → ${c.side} · crossing`);
    }
    for (const e of path.edges) {
      if (e.from === name || e.to === name) hops.push(`${e.from} → ${e.to} · ${Math.round(e.km)} km · inside`);
    }
    return { inside, outside, hops };
  }

  function track(lon, lat, maxKm) {
    const flow = window.flow;
    const pts = [[lon, lat]];
    let done = 0;
    let guard = 0;
    while (done < maxKm && guard++ < 28) {
      const wind = flow(lon, lat);
      const u = wind[0];
      const v = wind[1];
      const mag = Math.hypot(u, v);
      if (mag < 0.08) break;
      const step = 14;
      lon += ((u / mag) * step) / (111 * Math.cos((lat * Math.PI) / 180) || 1);
      lat += ((v / mag) * step) / 111;
      done += step;
      pts.push([lon, lat]);
    }
    return pts;
  }

  function geometry(path) {
    if (!path.edges.length && path.crossing) {
      return { pts: track(path.crossing.lon, path.crossing.lat, 80), kind: path.crossing.kind, mark: path.crossing };
    }
    let lon = path.edges[0].fromLon;
    let lat = path.edges[0].fromLat;
    let length = path.edges.reduce((sum, e) => sum + e.km, 0);
    if (path.crossing && path.crossing.kind === "in") {
      lon = path.crossing.lon;
      lat = path.crossing.lat;
      const nodes = [path.edges[0].from];
      for (const e of path.edges) nodes.push(e.to);
      const at = Math.max(0, nodes.indexOf(path.crossing.district));
      length = path.crossing.km + path.edges.slice(at).reduce((sum, e) => sum + e.km, 0);
    }
    return {
      pts: track(lon, lat, Math.max(48, Math.min(300, length))),
      kind: path.crossing ? path.crossing.kind : "through",
      mark: path.crossing,
    };
  }

  function draw(ctx, screenOf, hour) {
    const paths = frame(hour).paths;
    if (!paths.length) return;
    ctx.save();
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    for (const path of paths) {
      const geo = geometry(path);
      if (geo.pts.length < 2) continue;
      const screens = geo.pts.map((p) => screenOf(p[0], p[1]));
      const outflow = geo.kind === "out";
      ctx.beginPath();
      ctx.moveTo(screens[0][0], screens[0][1]);
      if (screens.length === 2) {
        ctx.lineTo(screens[1][0], screens[1][1]);
      } else {
        for (let i = 1; i < screens.length - 1; i++) {
          const mx = (screens[i][0] + screens[i + 1][0]) * 0.5;
          const my = (screens[i][1] + screens[i + 1][1]) * 0.5;
          ctx.quadraticCurveTo(screens[i][0], screens[i][1], mx, my);
        }
        const last = screens[screens.length - 1];
        ctx.lineTo(last[0], last[1]);
      }
      ctx.strokeStyle = outflow ? "rgba(255, 252, 248, 0.5)" : "rgba(255, 252, 248, 0.66)";
      ctx.lineWidth = outflow ? 4.4 : 6;
      ctx.stroke();
      if (geo.mark) {
        const wind = window.flow(geo.mark.lon, geo.mark.lat);
        const [x, y] = screenOf(geo.mark.lon, geo.mark.lat);
        const [x2, y2] = screenOf(geo.mark.lon + wind[0] * 0.02, geo.mark.lat + wind[1] * 0.02);
        const ang = Math.atan2(y2 - y, x2 - x);
        const px = Math.cos(ang + Math.PI / 2);
        const py = Math.sin(ang + Math.PI / 2);
        ctx.strokeStyle = "rgba(255, 252, 248, 0.72)";
        ctx.lineWidth = 1.6;
        ctx.beginPath();
        ctx.moveTo(x - px * 7, y - py * 7);
        ctx.lineTo(x + px * 7, y + py * 7);
        ctx.stroke();
      }
    }
    ctx.restore();
  }

  window.Corridor = { frame, speak, draw };
})();
