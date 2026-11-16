/**
 * Geographic Equirectangular Projection and Collision-Free Greedy Labeling in TypeScript.
 * Implements:
 * 1. T11: Equirectangular Plate Carree projection centered on standard parallel 31 deg N.
 * 2. Forward and inverse coordinate transforms.
 * 3. Greedy 12-offset Axis-Aligned Bounding Box (AABB) collision-free label search with leader line detection.
 * Zero external framework dependencies.
 */

// Provincial Geographic Bounds (TRANSFORMATION_LOGIC_SPEC.md §2.11.1)
export const LON_MIN_DEG = 69.10;
export const LON_MAX_DEG = 75.75;
export const LAT_MIN_DEG = 27.55;
export const LAT_MAX_DEG = 34.30;
export const STANDARD_PARALLEL_DEG = 31.0;

// Meridional distortion correction factor K_X = cos(31 deg)
export const KX_MERIDIONAL = Math.cos((STANDARD_PARALLEL_DEG * Math.PI) / 180.0);

// Greedy 12-Candidate Offset Priority Vector (§2.11.2)
export const LABEL_CANDIDATE_OFFSETS: ReadonlyArray<[dx: number, dy: number]> = [
  [0.0, 0.0],
  [0.0, 14.0],
  [0.0, -14.0],
  [16.0, 0.0],
  [-16.0, 0.0],
  [0.0, 26.0],
  [0.0, -26.0],
  [30.0, 8.0],
  [-30.0, 8.0],
  [24.0, -20.0],
  [-24.0, -20.0],
  [0.0, 38.0],
];

export const LEADER_LINE_THRESHOLD_PX = 20.0;

export interface LabelRequestItem {
  district_id?: string;
  id?: string;
  text?: string;
  anchor_x?: number;
  x?: number;
  anchor_y?: number;
  y?: number;
  width?: number;
  w?: number;
  height?: number;
  h?: number;
  [key: string]: any;
}

export interface PlacedLabelResult {
  district_id: string;
  text: string;
  anchor_x: number;
  anchor_y: number;
  placed_x: number;
  placed_y: number;
  offset_x: number;
  offset_y: number;
  has_leader_line: boolean;
  bounding_box: [x: number, y: number, width: number, height: number];
}

/**
 * Projects geographic WGS-84 coordinates (lat, lon) to 2D canvas pixel coordinates (X, Y)
 * using Equirectangular Plate Carree projection centered on standard parallel 31 deg N
 * (TRANSFORMATION_LOGIC_SPEC.md §2.11.1).
 */
export function equirectangularProject(
  lat: number,
  lon: number,
  widthPx: number = 1200.0,
  _heightPx: number = 900.0
): [x: number, y: number] {
  const scale = widthPx / ((LON_MAX_DEG - LON_MIN_DEG) * KX_MERIDIONAL);
  const x = (lon - LON_MIN_DEG) * KX_MERIDIONAL * scale;
  const y = (LAT_MAX_DEG - lat) * scale;
  return [x, y];
}

/**
 * Inverse projection: maps canvas pixel coordinates (X, Y) back to geographic coordinates (lat, lon).
 */
export function equirectangularUnproject(
  x: number,
  y: number,
  widthPx: number = 1200.0,
  _heightPx: number = 900.0
): [lat: number, lon: number] {
  const scale = widthPx / ((LON_MAX_DEG - LON_MIN_DEG) * KX_MERIDIONAL);
  const lon = x / (KX_MERIDIONAL * scale) + LON_MIN_DEG;
  const lat = LAT_MAX_DEG - y / scale;
  return [lat, lon];
}

/**
 * Evaluates whether two Axis-Aligned Bounding Boxes (AABB) overlap.
 * Each box is defined as [x, y, width, height] where (x, y) is the top-left corner.
 */
export function checkAabbCollision(
  box1: [x: number, y: number, width: number, height: number],
  box2: [x: number, y: number, width: number, height: number]
): boolean {
  const [x1, y1, w1, h1] = box1;
  const [x2, y2, w2, h2] = box2;

  return (
    x1 < x2 + w2 &&
    x1 + w1 > x2 &&
    y1 < y2 + h2 &&
    y1 + h1 > y2
  );
}

/**
 * Places district text labels on canvas without visual overlap using a greedy 12-offset search
 * (TRANSFORMATION_LOGIC_SPEC.md §2.11.2).
 */
export function greedyLabelPlacement(
  labels: LabelRequestItem[],
  candidateOffsets: ReadonlyArray<[dx: number, dy: number]> = LABEL_CANDIDATE_OFFSETS,
  leaderLineThresh: number = LEADER_LINE_THRESHOLD_PX
): PlacedLabelResult[] {
  const placedBoxes: Array<[x: number, y: number, width: number, height: number]> = [];
  const results: PlacedLabelResult[] = [];

  for (const item of labels) {
    const dId = String(item.district_id ?? item.id ?? '');
    const text = String(item.text ?? '');
    const ax = Number(item.anchor_x ?? item.x ?? 0.0);
    const ay = Number(item.anchor_y ?? item.y ?? 0.0);
    const w = Number(item.width ?? item.w ?? 48.0);
    const h = Number(item.height ?? item.h ?? 16.0);

    let chosenOffset: [number, number] = candidateOffsets[candidateOffsets.length - 1];
    let chosenBox: [number, number, number, number] | null = null;

    for (const [dx, dy] of candidateOffsets) {
      const boxX = ax + dx - w / 2.0 - 1.0;
      const boxY = ay + dy - h / 2.0;
      const boxW = w + 2.0;
      const boxH = h;
      const candidateBox: [number, number, number, number] = [boxX, boxY, boxW, boxH];

      let collides = false;
      for (const pBox of placedBoxes) {
        if (checkAabbCollision(candidateBox, pBox)) {
          collides = true;
          break;
        }
      }

      if (!collides) {
        chosenOffset = [dx, dy];
        chosenBox = candidateBox;
        break;
      }
    }

    if (!chosenBox) {
      const [dx, dy] = chosenOffset;
      chosenBox = [ax + dx - w / 2.0 - 1.0, ay + dy - h / 2.0, w + 2.0, h];
    }

    placedBoxes.push(chosenBox);
    const [dx, dy] = chosenOffset;
    const disp = Math.sqrt(dx * dx + dy * dy);
    const hasLeader = disp > leaderLineThresh;

    results.push({
      district_id: dId,
      text,
      anchor_x: Number(ax.toFixed(2)),
      anchor_y: Number(ay.toFixed(2)),
      placed_x: Number((ax + dx).toFixed(2)),
      placed_y: Number((ay + dy).toFixed(2)),
      offset_x: Number(dx.toFixed(2)),
      offset_y: Number(dy.toFixed(2)),
      has_leader_line: hasLeader,
      bounding_box: [
        Number(chosenBox[0].toFixed(2)),
        Number(chosenBox[1].toFixed(2)),
        Number(chosenBox[2].toFixed(2)),
        Number(chosenBox[3].toFixed(2)),
      ],
    });
  }

  return results;
}
