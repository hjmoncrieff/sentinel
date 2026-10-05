// Build-time map geometry: decode a TopoJSON topology and project it to SVG paths.
// Written out by hand (no d3) so the build has no dependencies and the maps ship
// as plain SVG that needs no script to draw.

/** Decode one TopoJSON object into features: [{id, polygons: [[[lon, lat], ...ring], ...polygon]}]. */
export function topoFeatures(topology, objectName) {
  const {scale = [1, 1], translate = [0, 0]} = topology.transform || {};
  const arcs = topology.arcs.map(arc => {
    let x = 0, y = 0;
    return arc.map(([dx, dy]) => { x += dx; y += dy; return [x * scale[0] + translate[0], y * scale[1] + translate[1]]; });
  });
  const ring = indexes => {
    const out = [];
    for (const i of indexes) {
      const pts = i >= 0 ? arcs[i] : [...arcs[~i]].reverse();
      out.push(...(out.length ? pts.slice(1) : pts));
    }
    return out;
  };
  return topology.objects[objectName].geometries.map(g => ({
    id: g.id,
    polygons: (g.type === 'Polygon' ? [g.arcs] : g.type === 'MultiPolygon' ? g.arcs : []).map(poly => poly.map(ring)),
  }));
}

const mercY = lat => Math.log(Math.tan(Math.PI / 4 + (Math.max(-85, Math.min(85, lat)) * Math.PI / 180) / 2));
const lonLatBounds = features => {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const f of features) for (const poly of f.polygons) for (const [lon, lat] of poly[0]) {
    const y = mercY(lat);
    if (lon < x0) x0 = lon; if (lon > x1) x1 = lon; if (y < y0) y0 = y; if (y > y1) y1 = y;
  }
  return [x0, y0, x1, y1];
};

/** A Mercator projection that fits `features` to `width`, with `pad` px around. */
export function fitMercator(features, width, pad = 6) {
  const [x0, y0, x1, y1] = lonLatBounds(features);
  const k = (width - 2 * pad) / ((x1 - x0) * Math.PI / 180);
  const height = Math.ceil((y1 - y0) * k + 2 * pad);
  const project = ([lon, lat]) => [pad + (lon - x0) * Math.PI / 180 * k, pad + (y1 - mercY(lat)) * k];
  return {project, width, height};
}

const ringArea = pts => { let a = 0; for (let i = 0, n = pts.length; i < n; i++) { const [x1, y1] = pts[i], [x2, y2] = pts[(i + 1) % n]; a += x1 * y2 - x2 * y1; } return a / 2; };

/** Project a feature: SVG path data, pixel area, centroid of its largest polygon, and bounds. */
export function shape(feature, project) {
  let d = '', area = 0, best = null, bx0 = Infinity, by0 = Infinity, bx1 = -Infinity, by1 = -Infinity;
  for (const poly of feature.polygons) {
    const rings = poly.map(r => r.map(project));
    for (const pts of rings) {
      d += 'M' + pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join('L') + 'Z';
      for (const [x, y] of pts) { if (x < bx0) bx0 = x; if (x > bx1) bx1 = x; if (y < by0) by0 = y; if (y > by1) by1 = y; }
    }
    const a = Math.abs(ringArea(rings[0]));
    area += a;
    if (!best || a > best.a) best = {a, pts: rings[0]};
  }
  let cx = 0, cy = 0;
  if (best) {
    const pts = best.pts, A = ringArea(pts) || 1;
    for (let i = 0, n = pts.length; i < n; i++) {
      const [x1, y1] = pts[i], [x2, y2] = pts[(i + 1) % n], f = x1 * y2 - x2 * y1;
      cx += (x1 + x2) * f; cy += (y1 + y2) * f;
    }
    cx /= 6 * A; cy /= 6 * A;
  }
  return {d, area, centroid: [cx, cy], bounds: [bx0, by0, bx1, by1]};
}

export const intersects = (b, w, h, margin = 40) => b[2] > -margin && b[0] < w + margin && b[3] > -margin && b[1] < h + margin;
