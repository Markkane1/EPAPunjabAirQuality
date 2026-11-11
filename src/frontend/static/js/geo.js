/**
 * Geographic Projection & Topology Management Module.
 * Equirectangular Plate Carrée projection with standard parallel 31.0°N.
 * Hardware Path2D path compilation for Punjab, Indian border states, and Pakistan territories.
 */

export const B = {
  lo0: 69.1,
  lo1: 75.75,
  la0: 27.55,
  la1: 34.3,
};

export const KX = Math.cos(31 * Math.PI / 180); // 0.8571673007
export const RAD = Math.PI / 180;
export const R_EARTH = 6371.0; // Mean Earth radius in km

/**
 * Forward Equirectangular projection from (lon, lat) to screen (x, y).
 */
export function project(lon, lat, S) {
  const x = (lon - B.lo0) * KX * S;
  const y = (B.la1 - lat) * S;
  return [x, y];
}

/**
 * Inverse Equirectangular projection from screen (x, y) to (lon, lat).
 */
export function unproject(x, y, S) {
  const lon = x / (KX * S) + B.lo0;
  const lat = B.la1 - y / S;
  return [lon, lat];
}

/**
 * Great-circle distance (km) and forward azimuth (degrees) between two points.
 */
export function geoDistAndBearing(lon1, lat1, lon2, lat2) {
  const la1 = lat1 * RAD;
  const lo1 = lon1 * RAD;
  const la2 = lat2 * RAD;
  const lo2 = lon2 * RAD;
  const dl = lo2 - lo1;

  const d = 2 * R_EARTH * Math.asin(
    Math.sqrt(Math.sin((la2 - la1) / 2) ** 2 + Math.cos(la1) * Math.cos(la2) * Math.sin(dl / 2) ** 2)
  );

  const y = Math.sin(dl) * Math.cos(la2);
  const x = Math.cos(la1) * Math.sin(la2) - Math.sin(la1) * Math.cos(la2) * Math.cos(dl);
  const brg = ((Math.atan2(y, x) / RAD) + 360) % 360;

  return [d, brg];
}

function addRingToPath(path, ring, S) {
  ring.forEach((p, i) => {
    const [x, y] = project(p[0], p[1], S);
    if (i === 0) {
      path.moveTo(x, y);
    } else {
      path.lineTo(x, y);
    }
  });
  path.closePath();
}

/**
 * Compiles Path2D structures for base map rendering.
 */
export function compilePaths(GEO, IND, TBG, districts, S) {
  let pjPath = new Path2D();
  const provPaths = [];

  // Pakistan provinces & territories
  if (GEO) {
    for (const [name, polys] of Object.entries(GEO)) {
      const p = new Path2D();
      polys.forEach(po => po.forEach(r => addRingToPath(p, r, S)));
      if (name.toLowerCase() === 'punjab') {
        pjPath = p;
      } else {
        provPaths.push(p);
      }
    }
  }

  // Adjacent Indian States
  const indPath = new Path2D();
  if (IND) {
    Object.values(IND).forEach(polys => {
      polys.forEach(po => po.forEach(r => addRingToPath(indPath, r, S)));
    });
  }

  // International border line (440 coordinates)
  const borderPath = new Path2D();
  if (TBG && TBG.border) {
    TBG.border.forEach((coord, i) => {
      const [x, y] = project(coord[0], coord[1], S);
      if (i === 0) {
        borderPath.moveTo(x, y);
      } else {
        borderPath.lineTo(x, y);
      }
    });
  }

  // 41 Punjab Administrative District boundaries
  const admPaths = [];
  if (districts) {
    // districts can be an array of objects or an object dictionary
    const distList = Array.isArray(districts) ? districts : Object.values(districts);
    distList.forEach(dist => {
      const p = new Path2D();
      const polys = dist.polys || (dist.boundary && dist.boundary.coordinates) || dist.boundary;
      if (polys && Array.isArray(polys)) {
        polys.forEach(po => {
          if (Array.isArray(po)) {
            po.forEach(r => {
              if (Array.isArray(r) && r.length > 0) {
                if (Array.isArray(r[0])) {
                  addRingToPath(p, r, S);
                } else if (typeof r[0] === 'number') {
                  addRingToPath(p, po, S);
                }
              }
            });
          }
        });
      }
      admPaths.push({
        name: dist.name || dist.district,
        path: p,
        centroid: dist.centroid || [dist.lon || dist.longitude, dist.lat || dist.latitude],
        is_estimated: !!dist.est,
      });
    });
  }

  return {
    pjPath,
    provPaths,
    indPath,
    borderPath,
    admPaths,
  };
}
