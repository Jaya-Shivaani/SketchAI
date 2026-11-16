"""
Feature Extraction Pipeline for Sketch Classification
Extracts geometric, stroke-level, and rasterized spatial features from drawing sketches.
Compatible with both raw stroke sequences (from HTML5 Canvas) and raster images.
"""

import numpy as np
import math
from typing import List, Dict, Any, Union

CATEGORY_MAP = {
    0: "Animal",
    1: "Object",
    2: "Food",
    3: "Vehicle",
    4: "Nature"
}

CATEGORY_TO_ID = {v: k for k, v in CATEGORY_MAP.items()}


def normalize_strokes(strokes: List[List[List[float]]], target_size: int = 256) -> List[List[List[float]]]:
    """
    Normalizes stroke coordinates into a standard [0, target_size] bounding box
    while preserving aspect ratio with proportional margins.
    Input strokes format: [ [[x1, x2, ...], [y1, y2, ...]], ... ]
    """
    all_x = []
    all_y = []
    for stroke in strokes:
        if len(stroke) >= 2 and len(stroke[0]) > 0:
            all_x.extend(stroke[0])
            all_y.extend(stroke[1])

    if not all_x or not all_y:
        return strokes

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)

    w = max(max_x - min_x, 1.0)
    h = max(max_y - min_y, 1.0)
    
    # Proportional margin (8% of target_size) ensures correct scaling at any target_size
    margin = max(1.0, target_size * 0.08)
    scale = (target_size - 2.0 * margin) / max(w, h)

    offset_x = (target_size - w * scale) / 2.0
    offset_y = (target_size - h * scale) / 2.0

    norm_strokes = []
    for stroke in strokes:
        if len(stroke) >= 2 and len(stroke[0]) > 0:
            nx = [float((x - min_x) * scale + offset_x) for x in stroke[0]]
            ny = [float((y - min_y) * scale + offset_y) for y in stroke[1]]
            norm_strokes.append([nx, ny])

    return norm_strokes


def rasterize_strokes(strokes: List[List[List[float]]], grid_size: int = 28) -> np.ndarray:
    """
    Rasterizes vector strokes onto a grid_size x grid_size binary/grayscale matrix
    using Bresenham line algorithm.
    """
    grid = np.zeros((grid_size, grid_size), dtype=np.float32)
    norm = normalize_strokes(strokes, target_size=grid_size - 1)

    for stroke in norm:
        if len(stroke) < 2 or len(stroke[0]) == 0:
            continue
        xs, ys = stroke[0], stroke[1]
        for i in range(len(xs) - 1):
            x0, y0 = int(round(xs[i])), int(round(ys[i]))
            x1, y1 = int(round(xs[i + 1])), int(round(ys[i + 1]))

            # Bresenham line drawing
            dx = abs(x1 - x0)
            dy = abs(y1 - y0)
            sx = 1 if x0 < x1 else -1
            sy = 1 if y0 < y1 else -1
            err = dx - dy

            while True:
                if 0 <= x0 < grid_size and 0 <= y0 < grid_size:
                    grid[y0, x0] = 1.0
                if x0 == x1 and y0 == y1:
                    break
                e2 = 2 * err
                if e2 > -dy:
                    err -= dy
                    x0 += sx
                if e2 < dx:
                    err += dx
                    y0 += sy

        # If single point stroke
        if len(xs) == 1:
            px, py = int(round(xs[0])), int(round(ys[0]))
            if 0 <= px < grid_size and 0 <= py < grid_size:
                grid[py, px] = 1.0

    return grid


def resample_stroke(xs: List[float], ys: List[float], step: float = 8.0):
    """
    Resamples stroke points to equidistant intervals.
    Eliminates mouse speed / polling rate variance between fast and slow drawings.
    """
    if len(xs) < 2:
        return xs, ys
    new_xs = [float(xs[0])]
    new_ys = [float(ys[0])]
    accum = 0.0
    for i in range(len(xs) - 1):
        dx = xs[i + 1] - xs[i]
        dy = ys[i + 1] - ys[i]
        seg = math.hypot(dx, dy)
        if seg == 0:
            continue
        accum += seg
        while accum >= step:
            ratio = (seg - (accum - step)) / seg
            new_xs.append(float(xs[i] + dx * ratio))
            new_ys.append(float(ys[i] + dy * ratio))
            accum -= step
    if len(new_xs) == 1:
        new_xs.append(float(xs[-1]))
        new_ys.append(float(ys[-1]))
    return new_xs, new_ys


def extract_features_from_strokes(strokes: List[List[List[float]]]) -> np.ndarray:
    """
    Extracts comprehensive feature vector from stroke coordinates:
    - 15 Geometric features: aspect ratio, diagonal, bounding box dimensions,
      center of mass, spread (std_x, std_y), extent, compactness, and normalized stroke metrics.
    - 8 Orientation features: 8-bin histogram of stroke trajectory angles (0 to 2*pi).
    - 5 Curvature & symmetry features: mean curvature, std curvature, pixel density, horizontal & vertical symmetry.
    - 49 Spatial features: 7x7 spatial pooling grid from a 28x28 rasterized representation.
    Total feature dimensions: 15 + 8 + 5 + 49 = 77 features.
    """
    # 1. Normalize strokes into standard [0, 256] coordinate space
    norm = normalize_strokes(strokes, target_size=256)

    # 2. Resample points along every stroke for consistent density
    resampled_strokes = []
    for s in norm:
        if len(s) >= 2 and len(s[0]) > 0:
            rx, ry = resample_stroke(s[0], s[1], step=8.0)
            resampled_strokes.append([rx, ry])

    all_x = []
    all_y = []
    total_length = 0.0
    stroke_lengths = []
    angles = []
    curvature_changes = []

    stroke_count = len(resampled_strokes)
    total_points = 0
    prev_angle = None

    for stroke in resampled_strokes:
        if len(stroke) < 2 or len(stroke[0]) == 0:
            continue
        xs = stroke[0]
        ys = stroke[1]
        n_pts = len(xs)
        total_points += n_pts

        current_stroke_len = 0.0
        for i in range(n_pts - 1):
            dx = xs[i + 1] - xs[i]
            dy = ys[i + 1] - ys[i]
            seg_len = math.hypot(dx, dy)
            current_stroke_len += seg_len

            angle = math.atan2(dy, dx)
            # Map to [0, 2pi)
            if angle < 0:
                angle += 2 * math.pi
            angles.append(angle)

            if prev_angle is not None:
                d_angle = abs(angle - prev_angle)
                if d_angle > math.pi:
                    d_angle = 2 * math.pi - d_angle
                curvature_changes.append(d_angle)
            prev_angle = angle

        all_x.extend(xs)
        all_y.extend(ys)
        total_length += current_stroke_len
        stroke_lengths.append(current_stroke_len)

    if not all_x:
        return np.zeros(77, dtype=np.float32)

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    bbox_w = max(max_x - min_x, 1.0)
    bbox_h = max(max_y - min_y, 1.0)
    aspect_ratio = bbox_w / bbox_h
    diagonal = math.hypot(bbox_w, bbox_h)
    bbox_area = bbox_w * bbox_h

    # Log-damped stroke metrics so pen-lift habits do not overpower visual shape
    log_stroke_count = float(math.log1p(stroke_count))
    extent = total_length / max(diagonal, 1.0)
    compactness = (total_length ** 2) / max(bbox_area, 1.0)

    # Center of mass normalized to bounding box
    mean_x = (np.mean(all_x) - min_x) / bbox_w
    mean_y = (np.mean(all_y) - min_y) / bbox_h
    std_x = np.std(all_x) / bbox_w
    std_y = np.std(all_y) / bbox_h

    # Curvature statistics
    mean_curvature = float(np.mean(curvature_changes)) if curvature_changes else 0.0
    std_curvature = float(np.std(curvature_changes)) if curvature_changes else 0.0

    # 8-bin orientation histogram
    angle_hist, _ = np.histogram(angles, bins=8, range=(0, 2 * math.pi), density=True)
    if np.isnan(angle_hist).any() or len(angles) == 0:
        angle_hist = np.zeros(8, dtype=np.float32)

    # Rasterize to 28x28 and compute spatial cell pooling (7x7 blocks of 4x4 pixels)
    raster_28 = rasterize_strokes(resampled_strokes, grid_size=28)
    pixel_density = float(np.mean(raster_28))

    # Horizontal and vertical symmetry
    h_flipped = np.fliplr(raster_28)
    v_flipped = np.flipud(raster_28)
    h_symmetry = float(np.sum(raster_28 * h_flipped) / max(np.sum(raster_28), 1.0))
    v_symmetry = float(np.sum(raster_28 * v_flipped) / max(np.sum(raster_28), 1.0))

    # 7x7 spatial pooling from 28x28 (4x4 pixels per block) = 49 features
    pooled_cells = []
    for r in range(0, 28, 4):
        for c in range(0, 28, 4):
            block = raster_28[r:r + 4, c:c + 4]
            pooled_cells.append(float(np.mean(block)))

    geo_features = [
        log_stroke_count,                     # 1. log-scaled stroke count
        float(total_points) / 100.0,          # 2. normalized point count
        float(total_length) / 500.0,          # 3. normalized path length
        float(bbox_w) / 256.0,                # 4. normalized width
        float(bbox_h) / 256.0,                # 5. normalized height
        float(aspect_ratio),                  # 6. aspect ratio (key for vehicle vs nature/object)
        float(diagonal) / 256.0,              # 7. normalized diagonal
        float(bbox_area) / (256.0 * 256.0),   # 8. normalized area
        float(extent),                        # 9. path complexity relative to diagonal
        float(compactness) / 50.0,            # 10. perimeter-to-area compactness
        float(mean_x),                        # 11. center of mass X
        float(mean_y),                        # 12. center of mass Y
        float(std_x),                         # 13. spread X
        float(std_y),                         # 14. spread Y
        float(pixel_density) * 10.0,          # 15. active ink density
    ]

    curvature_features = [
        mean_curvature,
        std_curvature,
        pixel_density,
        h_symmetry,
        v_symmetry,
    ]

    features = np.concatenate([
        np.array(geo_features, dtype=np.float32),          # 15
        np.array(angle_hist, dtype=np.float32),            # 8
        np.array(curvature_features, dtype=np.float32),    # 5
        np.array(pooled_cells, dtype=np.float32),          # 49
    ])

    return features
