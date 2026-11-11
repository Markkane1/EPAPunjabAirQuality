"""
Geographic Equirectangular Projection and Collision-Free Greedy Labeling.
Implements:
1. T11: Equirectangular Plate Carree projection centered on standard parallel 31 deg N.
2. Forward and inverse coordinate transforms.
3. Greedy 12-offset Axis-Aligned Bounding Box (AABB) collision-free label search with leader line detection.
Zero external framework dependencies (standard library and math only).
"""
import math
from typing import Any, Dict, List, Optional, Tuple

# Provincial Geographic Bounds (TRANSFORMATION_LOGIC_SPEC.md §2.11.1)
LON_MIN_DEG: float = 69.10
LON_MAX_DEG: float = 75.75
LAT_MIN_DEG: float = 27.55
LAT_MAX_DEG: float = 34.30
STANDARD_PARALLEL_DEG: float = 31.0

# Meridional distortion correction factor K_X = cos(31 deg)
KX_MERIDIONAL: float = math.cos(math.radians(STANDARD_PARALLEL_DEG))

# Greedy 12-Candidate Offset Priority Vector (§2.11.2)
LABEL_CANDIDATE_OFFSETS: Tuple[Tuple[float, float], ...] = (
    (0.0, 0.0),
    (0.0, 14.0),
    (0.0, -14.0),
    (16.0, 0.0),
    (-16.0, 0.0),
    (0.0, 26.0),
    (0.0, -26.0),
    (30.0, 8.0),
    (-30.0, 8.0),
    (24.0, -20.0),
    (-24.0, -20.0),
    (0.0, 38.0),
)

LEADER_LINE_THRESHOLD_PX: float = 20.0


def equirectangular_project(
    lat: float,
    lon: float,
    width_px: float = 1200.0,
    height_px: float = 900.0,
) -> Tuple[float, float]:
    """
    Projects geographic WGS-84 coordinates (lat, lon) to 2D canvas pixel coordinates (X, Y)
    using Equirectangular Plate Carree projection centered on standard parallel 31 deg N
    (TRANSFORMATION_LOGIC_SPEC.md §2.11.1).
    
    Formula:
        S = width_px / ((lon_max - lon_min) * cos(31 deg))
        X = (lon - lon_min) * cos(31 deg) * S
        Y = (lat_max - lat) * S
        
    Args:
        lat: Latitude in decimal degrees [27.55, 34.30].
        lon: Longitude in decimal degrees [69.10, 75.75].
        width_px: Canvas rendering width in pixels (default: 1200.0).
        height_px: Canvas rendering height in pixels (default: 900.0).
        
    Returns:
        (X, Y) pixel coordinates on canvas.
    """
    scale = width_px / ((LON_MAX_DEG - LON_MIN_DEG) * KX_MERIDIONAL)
    x = (lon - LON_MIN_DEG) * KX_MERIDIONAL * scale
    y = (LAT_MAX_DEG - lat) * scale
    return (x, y)


def equirectangular_unproject(
    x: float,
    y: float,
    width_px: float = 1200.0,
    height_px: float = 900.0,
) -> Tuple[float, float]:
    """
    Inverse projection: maps canvas pixel coordinates (X, Y) back to geographic coordinates (lat, lon).
    
    Formula:
        S = width_px / ((lon_max - lon_min) * cos(31 deg))
        lon = (X / (cos(31 deg) * S)) + lon_min
        lat = lat_max - (Y / S)
    """
    scale = width_px / ((LON_MAX_DEG - LON_MIN_DEG) * KX_MERIDIONAL)
    lon = (x / (KX_MERIDIONAL * scale)) + LON_MIN_DEG
    lat = LAT_MAX_DEG - (y / scale)
    return (lat, lon)


def check_aabb_collision(
    box1: Tuple[float, float, float, float],
    box2: Tuple[float, float, float, float],
) -> bool:
    """
    Evaluates whether two Axis-Aligned Bounding Boxes (AABB) overlap.
    Each box is defined as (x, y, width, height) where (x, y) is the top-left corner.
    
    Formula:
        Overlap = (R.x < Q.x + Q.w) and (R.x + R.w > Q.x) and
                  (R.y < Q.y + Q.h) and (R.y + R.h > Q.y)
    """
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2

    return (
        x1 < x2 + w2
        and x1 + w1 > x2
        and y1 < y2 + h2
        and y1 + h1 > y2
    )


def greedy_label_placement(
    labels: List[Dict[str, Any]],
    candidate_offsets: Tuple[Tuple[float, float], ...] = LABEL_CANDIDATE_OFFSETS,
    leader_line_thresh: float = LEADER_LINE_THRESHOLD_PX,
) -> List[Dict[str, Any]]:
    """
    Places district text labels on canvas without visual overlap using a greedy 12-offset search
    (TRANSFORMATION_LOGIC_SPEC.md §2.11.2).
    
    For each candidate offset [dx, dy] with text dimensions (w, h):
        Box: [anchor_x + dx - w/2 - 1.0, anchor_y + dy - h/2, w + 2.0, h]
        Accept the first offset that does not collide with any already-placed label box.
        If sqrt(dx^2 + dy^2) > 20.0 px, automatically flag leader line.
        
    Args:
        labels: List of label request dicts with:
            - 'district_id' or 'id'
            - 'text'
            - 'anchor_x', 'anchor_y' (or 'x', 'y')
            - 'width', 'height' (text bounding dimensions in pixels, defaults: 48.0, 16.0)
            
    Returns:
        List of placed label dicts with 'placed_x', 'placed_y', 'offset_x', 'offset_y',
        'has_leader_line', 'bounding_box'.
    """
    placed_boxes: List[Tuple[float, float, float, float]] = []
    results: List[Dict[str, Any]] = []

    for item in labels:
        d_id = item.get("district_id", item.get("id", ""))
        text = item.get("text", "")
        ax = float(item.get("anchor_x", item.get("x", 0.0)))
        ay = float(item.get("anchor_y", item.get("y", 0.0)))
        w = float(item.get("width", item.get("w", 48.0)))
        h = float(item.get("height", item.get("h", 16.0)))

        chosen_offset = candidate_offsets[-1]  # Default to last fallback offset
        chosen_box: Optional[Tuple[float, float, float, float]] = None

        for dx, dy in candidate_offsets:
            box_x = ax + dx - (w / 2.0) - 1.0
            box_y = ay + dy - (h / 2.0)
            box_w = w + 2.0
            box_h = h
            candidate_box = (box_x, box_y, box_w, box_h)

            collides = False
            for p_box in placed_boxes:
                if check_aabb_collision(candidate_box, p_box):
                    collides = True
                    break

            if not collides:
                chosen_offset = (dx, dy)
                chosen_box = candidate_box
                break

        if chosen_box is None:
            dx, dy = chosen_offset
            chosen_box = (ax + dx - (w / 2.0) - 1.0, ay + dy - (h / 2.0), w + 2.0, h)

        placed_boxes.append(chosen_box)
        dx, dy = chosen_offset
        disp = math.sqrt(dx * dx + dy * dy)
        has_leader = disp > leader_line_thresh

        results.append({
            "district_id": d_id,
            "text": text,
            "anchor_x": round(ax, 2),
            "anchor_y": round(ay, 2),
            "placed_x": round(ax + dx, 2),
            "placed_y": round(ay + dy, 2),
            "offset_x": round(dx, 2),
            "offset_y": round(dy, 2),
            "has_leader_line": has_leader,
            "bounding_box": tuple(round(v, 2) for v in chosen_box),
        })

    return results
