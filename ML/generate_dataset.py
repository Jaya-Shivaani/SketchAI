"""
Dataset Generator & Preprocessor for Drawing Game (5 Categories)
Generates high-diversity sketch stroke data and 28x28 bitmaps modeled after QuickDraw patterns
across 5 categories: Animal, Object, Food, Vehicle, Nature.
Supports diverse drawing styles (multi-stroke, continuous outline, single-stroke).
"""

import os
import sys
import math
import random
import json
import argparse
import numpy as np

# Ensure current ML dir is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from feature_extraction import (
    CATEGORY_MAP,
    CATEGORY_TO_ID,
    extract_features_from_strokes,
    rasterize_strokes,
    normalize_strokes
)


def add_noise(points_x, points_y, jitter_amount=2.0):
    """Adds natural human hand-drawing tremor and jitter."""
    noisy_x = []
    noisy_y = []
    for x, y in zip(points_x, points_y):
        jx = x + random.uniform(-jitter_amount, jitter_amount)
        jy = y + random.uniform(-jitter_amount, jitter_amount)
        noisy_x.append(jx)
        noisy_y.append(jy)
    return noisy_x, noisy_y


def make_circle_stroke(cx, cy, r, num_pts=20, jitter=1.5):
    angles = np.linspace(0, 2 * math.pi, num_pts)
    xs = [cx + r * math.cos(a) for a in angles]
    ys = [cy + r * math.sin(a) for a in angles]
    return add_noise(xs, ys, jitter)


def make_line_stroke(x1, y1, x2, y2, num_pts=10, jitter=1.5):
    xs = np.linspace(x1, x2, num_pts).tolist()
    ys = np.linspace(y1, y2, num_pts).tolist()
    return add_noise(xs, ys, jitter)


def make_arc_stroke(cx, cy, r, start_ang, end_ang, num_pts=15, jitter=1.5):
    angles = np.linspace(start_ang, end_ang, num_pts)
    xs = [cx + r * math.cos(a) for a in angles]
    ys = [cy + r * math.sin(a) for a in angles]
    return add_noise(xs, ys, jitter)


# ---- ANIMAL SKETCH GENERATORS ----
def sketch_cat():
    hx, hy = make_circle_stroke(128, 120, 45)
    e1x, e1y = make_line_stroke(95, 85, 105, 50, 6)
    e1x_b, e1y_b = make_line_stroke(105, 50, 120, 80, 6)
    e2x, e2y = make_line_stroke(136, 80, 151, 50, 6)
    e2x_b, e2y_b = make_line_stroke(151, 50, 161, 85, 6)
    w1x, w1y = make_line_stroke(70, 125, 110, 125, 5)
    w2x, w2y = make_line_stroke(146, 125, 186, 125, 5)
    bx, by = make_arc_stroke(128, 180, 50, 0.2, math.pi - 0.2, 16)
    tx, ty = make_arc_stroke(180, 200, 35, math.pi, 1.8 * math.pi, 10)
    return [
        [hx, hy], [e1x + e1x_b, e1y + e1y_b], [e2x + e2x_b, e2y + e2y_b],
        [w1x, w1y], [w2x, w2y], [bx, by], [tx, ty]
    ]


def sketch_dog():
    hx, hy = make_circle_stroke(110, 110, 40)
    e1x, e1y = make_arc_stroke(80, 120, 25, -math.pi/2, math.pi/2, 10)
    e2x, e2y = make_arc_stroke(140, 120, 25, math.pi/2, 1.5*math.pi, 10)
    bx, by = make_line_stroke(140, 140, 210, 150, 10)
    l1x, l1y = make_line_stroke(120, 150, 120, 210, 6)
    l2x, l2y = make_line_stroke(190, 150, 190, 210, 6)
    tx, ty = make_line_stroke(210, 150, 230, 110, 6)
    return [[hx, hy], [e1x, e1y], [e2x, e2y], [bx, by], [l1x, l1y], [l2x, l2y], [tx, ty]]


def sketch_fish():
    angles = np.linspace(0, 2 * math.pi, 25)
    bx = [128 + 65 * math.cos(a) for a in angles]
    by = [128 + 35 * math.sin(a) for a in angles]
    bx, by = add_noise(bx, by)
    t1x, t1y = make_line_stroke(63, 128, 30, 95, 6)
    t2x, t2y = make_line_stroke(30, 95, 30, 161, 6)
    t3x, t3y = make_line_stroke(30, 161, 63, 128, 6)
    ex, ey = make_circle_stroke(165, 120, 5, 8)
    gx, gy = make_arc_stroke(145, 128, 20, -math.pi/3, math.pi/3, 8)
    return [[bx, by], [t1x + t2x + t3x, t1y + t2y + t3y], [ex, ey], [gx, gy]]


def sketch_bird():
    hx, hy = make_circle_stroke(90, 90, 22)
    bkx, bky = make_line_stroke(68, 90, 50, 95, 4)
    w1x, w1y = make_arc_stroke(128, 120, 35, 0, math.pi, 12)
    w2x, w2y = make_arc_stroke(170, 120, 35, 0, math.pi, 12)
    tx, ty = make_line_stroke(160, 130, 200, 145, 6)
    return [[hx, hy], [bkx, bky], [w1x, w1y], [w2x, w2y], [tx, ty]]


def sketch_snake():
    # S-curved single stroke animal
    t = np.linspace(0, 4 * math.pi, 30)
    xs = (60 + 10 * t).tolist()
    ys = [128 + 40 * math.sin(val) for val in t]
    xs, ys = add_noise(xs, ys, 1.5)
    eye_x, eye_y = make_circle_stroke(xs[-1] + 5, ys[-1], 3, 6)
    return [[xs, ys], [eye_x, eye_y]]


# ---- OBJECT SKETCH GENERATORS ----
def sketch_chair():
    b1x, b1y = make_line_stroke(90, 60, 90, 140, 8)
    b2x, b2y = make_line_stroke(130, 60, 130, 140, 8)
    btopx, btopy = make_line_stroke(90, 60, 130, 60, 6)
    sx, sy = make_line_stroke(80, 140, 160, 140, 10)
    l1x, l1y = make_line_stroke(90, 140, 90, 210, 8)
    l2x, l2y = make_line_stroke(150, 140, 150, 210, 8)
    return [[b1x, b1y], [b2x, b2y], [btopx, btopy], [sx, sy], [l1x, l1y], [l2x, l2y]]


def sketch_cup():
    rx = [128 + 40 * math.cos(a) for a in np.linspace(0, 2*math.pi, 16)]
    ry = [90 + 12 * math.sin(a) for a in np.linspace(0, 2*math.pi, 16)]
    rx, ry = add_noise(rx, ry)
    b1x, b1y = make_line_stroke(88, 90, 95, 175, 8)
    b2x, b2y = make_line_stroke(168, 90, 161, 175, 8)
    botx, boty = make_arc_stroke(128, 170, 33, 0.1, math.pi - 0.1, 10)
    hx, hy = make_arc_stroke(170, 130, 25, -math.pi/2, math.pi/2, 10)
    return [[rx, ry], [b1x, b1y], [b2x, b2y], [botx, boty], [hx, hy]]


def sketch_clock():
    cx, cy = make_circle_stroke(128, 128, 60, 24)
    h1x, h1y = make_line_stroke(128, 128, 128, 88, 6)
    h2x, h2y = make_line_stroke(128, 128, 160, 128, 6)
    dx, dy = make_circle_stroke(128, 128, 4, 6)
    return [[cx, cy], [h1x, h1y], [h2x, h2y], [dx, dy]]


def sketch_umbrella():
    cx, cy = make_arc_stroke(128, 130, 65, math.pi, 2 * math.pi, 20)
    scallopx, scallopy = make_line_stroke(63, 130, 193, 130, 12)
    sx, sy = make_line_stroke(128, 70, 128, 185, 10)
    hx, hy = make_arc_stroke(140, 185, 12, math.pi, 2 * math.pi, 8)
    return [[cx, cy], [scallopx, scallopy], [sx, sy], [hx, hy]]


def sketch_table():
    top_x, top_y = make_line_stroke(60, 100, 196, 100, 14)
    top2_x, top2_y = make_line_stroke(60, 115, 196, 115, 14)
    l1x, l1y = make_line_stroke(80, 115, 80, 190, 8)
    l2x, l2y = make_line_stroke(176, 115, 176, 190, 8)
    return [[top_x, top_y], [top2_x, top2_y], [l1x, l1y], [l2x, l2y]]


# ---- FOOD SKETCH GENERATORS ----
def sketch_apple():
    ax = [128 + 50 * math.cos(a) for a in np.linspace(0, 2*math.pi, 22)]
    ay = [135 + 52 * math.sin(a) for a in np.linspace(0, 2*math.pi, 22)]
    ax, ay = add_noise(ax, ay)
    sx, sy = make_line_stroke(128, 85, 136, 60, 5)
    lx, ly = make_arc_stroke(145, 65, 12, -0.5, 1.8, 6)
    return [[ax, ay], [sx, sy], [lx, ly]]


def sketch_pizza():
    s1x, s1y = make_line_stroke(128, 70, 75, 180, 10)
    s2x, s2y = make_line_stroke(128, 70, 181, 180, 10)
    cx, cy = make_arc_stroke(128, 150, 60, 0.6, math.pi - 0.6, 12)
    p1x, p1y = make_circle_stroke(128, 120, 8, 8)
    p2x, p2y = make_circle_stroke(110, 155, 7, 8)
    p3x, p3y = make_circle_stroke(145, 155, 7, 8)
    return [[s1x, s1y], [s2x, s2y], [cx, cy], [p1x, p1y], [p2x, p2y], [p3x, p3y]]


def sketch_cake():
    t1x, t1y = make_line_stroke(90, 100, 166, 100, 8)
    t2x, t2y = make_line_stroke(90, 100, 90, 140, 6)
    t3x, t3y = make_line_stroke(166, 100, 166, 140, 6)
    t4x, t4y = make_line_stroke(90, 140, 166, 140, 8)
    b1x, b1y = make_line_stroke(70, 140, 186, 140, 10)
    b2x, b2y = make_line_stroke(70, 140, 70, 190, 6)
    b3x, b3y = make_line_stroke(186, 140, 186, 190, 6)
    b4x, b4y = make_line_stroke(70, 190, 186, 190, 10)
    cx, cy = make_line_stroke(128, 100, 128, 75, 4)
    fx, fy = make_circle_stroke(128, 70, 4, 6)
    return [[t1x, t1y], [t2x, t2y], [t3x, t3y], [t4x, t4y],
            [b1x, b1y], [b2x, b2y], [b3x, b3y], [b4x, b4y], [cx, cy], [fx, fy]]


def sketch_ice_cream():
    c1x, c1y = make_line_stroke(95, 120, 128, 205, 10)
    c2x, c2y = make_line_stroke(161, 120, 128, 205, 10)
    c3x, c3y = make_line_stroke(95, 120, 161, 120, 8)
    sx, sy = make_arc_stroke(128, 115, 36, math.pi, 2 * math.pi, 16)
    return [[c1x, c1y], [c2x, c2y], [c3x, c3y], [sx, sy]]


def sketch_burger():
    # Top bun arc
    b1x, b1y = make_arc_stroke(128, 110, 50, math.pi, 2 * math.pi, 16)
    bun_base_x, bun_base_y = make_line_stroke(78, 110, 178, 110, 10)
    # Patty
    px, py = make_line_stroke(75, 125, 181, 125, 10)
    # Bottom bun
    botx, boty = make_arc_stroke(128, 130, 48, 0.2, math.pi - 0.2, 14)
    return [[b1x, b1y], [bun_base_x, bun_base_y], [px, py], [botx, boty]]


# ---- VEHICLE SKETCH GENERATORS ----
def sketch_car():
    c1x, c1y = make_line_stroke(90, 120, 120, 90, 6)
    c2x, c2y = make_line_stroke(120, 90, 165, 90, 6)
    c3x, c3y = make_line_stroke(165, 90, 195, 120, 6)
    b1x, b1y = make_line_stroke(60, 120, 220, 120, 12)
    b2x, b2y = make_line_stroke(60, 120, 60, 155, 6)
    b3x, b3y = make_line_stroke(220, 120, 220, 155, 6)
    bottomx, bottomy = make_line_stroke(60, 155, 220, 155, 12)
    w1x, w1y = make_circle_stroke(95, 160, 16, 12)
    w2x, w2y = make_circle_stroke(185, 160, 16, 12)
    return [[c1x, c1y], [c2x, c2y], [c3x, c3y], [b1x, b1y], [b2x, b2y], [b3x, b3y], [bottomx, bottomy], [w1x, w1y], [w2x, w2y]]


def sketch_car_outline():
    # Continuous contour outline of a car silhouette
    pts_x = [60, 75, 95, 125, 165, 195, 220, 220, 205, 175, 105, 75, 60, 60]
    pts_y = [150, 125, 120, 90, 90, 120, 125, 155, 155, 155, 155, 155, 155, 150]
    bx, by = add_noise(pts_x, pts_y, 1.5)
    w1x, w1y = make_circle_stroke(95, 160, 14, 10)
    w2x, w2y = make_circle_stroke(185, 160, 14, 10)
    return [[bx, by], [w1x, w1y], [w2x, w2y]]


def sketch_bus():
    bx, by = make_line_stroke(60, 85, 220, 85, 12)
    b2x, b2y = make_line_stroke(220, 85, 220, 155, 8)
    b3x, b3y = make_line_stroke(220, 155, 60, 155, 12)
    b4x, b4y = make_line_stroke(60, 155, 60, 85, 8)
    w1x, w1y = make_line_stroke(75, 100, 105, 100, 5)
    w2x, w2y = make_line_stroke(120, 100, 150, 100, 5)
    w3x, w3y = make_line_stroke(165, 100, 195, 100, 5)
    wh1x, wh1y = make_circle_stroke(95, 162, 16, 12)
    wh2x, wh2y = make_circle_stroke(185, 162, 16, 12)
    return [[bx, by], [b2x, b2y], [b3x, b3y], [b4x, b4y], [w1x, w1y], [w2x, w2y], [w3x, w3y], [wh1x, wh1y], [wh2x, wh2y]]


def sketch_bus_outline():
    # Outer box + front window + 2 bottom wheels
    box_x = [60, 220, 220, 60, 60]
    box_y = [85, 85, 160, 160, 85]
    bx, by = add_noise(box_x, box_y, 1.5)
    win_x = [170, 205, 205, 170, 170]
    win_y = [95, 95, 125, 125, 95]
    wh1x, wh1y = make_circle_stroke(95, 168, 14, 10)
    wh2x, wh2y = make_circle_stroke(185, 168, 14, 10)
    return [[bx, by], [win_x, win_y], [wh1x, wh1y], [wh2x, wh2y]]


def sketch_airplane_stick():
    # Stick figure airplane (cross pattern)
    fx, fy = make_line_stroke(55, 128, 215, 128, 14)
    w1x, w1y = make_line_stroke(135, 128, 100, 50, 8)
    w2x, w2y = make_line_stroke(135, 128, 100, 206, 8)
    tx, ty = make_line_stroke(195, 128, 220, 95, 6)
    return [[fx, fy], [w1x, w1y], [w2x, w2y], [tx, ty]]


def sketch_airplane_outline():
    """
    Realistic aerodynamic airplane outline matching how humans draw airplanes:
    Fuselage contour with nose, swept wings, and vertical tail fin in continuous contour.
    """
    # Continuous single-stroke perimeter: nose at right (220, 128), tail at left (55, 128)
    fuselage_x = [220, 210, 180, 145, 130, 145, 125, 90, 55, 45, 65, 75, 110, 125, 105, 135, 180, 210, 220]
    fuselage_y = [128, 120, 120, 120, 60, 60, 120, 122, 125, 85, 125, 135, 135, 195, 195, 135, 136, 136, 128]
    fx, fy = add_noise(fuselage_x, fuselage_y, 1.8)
    return [[fx, fy]]


def sketch_airplane_swept_airliner():
    """
    Classic swept-wing airliner sketch matching human drawings (e.g. Shivaani's sketch):
    Horizontal fuselage, wide triangular swept wings, and tail stabilizer.
    Supports both multi-stroke and single-stroke variations.
    """
    if random.random() < 0.5:
        # Multi-stroke: Fuselage + Top Swept Wing + Bottom Swept Wing + Tail Fin
        body_x = [55, 100, 150, 190, 220, 220, 190, 150, 100, 55, 55]
        body_y = [120, 120, 120, 120, 125, 135, 140, 140, 140, 140, 120]
        bx, by = add_noise(body_x, body_y, 1.5)

        tw_x = [125, 155, 135]
        tw_y = [120, 45, 120]
        tx, ty = add_noise(tw_x, tw_y, 1.5)

        bw_x = [125, 100, 135]
        bw_y = [140, 215, 140]
        bx_w, by_w = add_noise(bw_x, bw_y, 1.5)

        tail_x = [55, 40, 65]
        tail_y = [120, 80, 120]
        tlx, tly = add_noise(tail_x, tail_y, 1.5)

        return [[bx, by], [tx, ty], [bx_w, by_w], [tlx, tly]]
    else:
        # 1 continuous stroke drawn by human without lifting pen
        all_x = [55, 100, 125, 155, 135, 150, 190, 220, 220, 190, 150, 135, 100, 125, 100, 55, 55, 40, 65, 55]
        all_y = [120, 120, 120, 45, 45, 120, 120, 125, 135, 140, 140, 140, 215, 215, 140, 140, 120, 80, 120, 120]
        ax, ay = add_noise(all_x, all_y, 2.0)
        return [[ax, ay]]


def sketch_airplane_facing_left():
    # Mirrored airliner flying to the left
    strokes = sketch_airplane_swept_airliner()
    mirrored = []
    for s in strokes:
        mx = [256.0 - x for x in s[0]]
        mirrored.append([mx, s[1]])
    return mirrored


def sketch_airplane_wide_flat():
    """
    Wide, flat airplane like a human quickly draws:
    Long horizontal fuselage with short swept wings above & below,
    plus a small tail fin. High aspect ratio (width >> height).
    Matches the style: long body + small wings on 1/3 point.
    """
    # Fuselage: very long horizontal body
    fuse_x = [30, 60, 90, 120, 150, 180, 210, 220]
    fuse_y = [128, 128, 128, 128, 128, 128, 128, 128]
    bx, by = add_noise(fuse_x, fuse_y, 2.0)

    # Top wing: short, swept back from 1/3 point
    tw_x = [100, 115, 140, 155]
    tw_y = [128, 110, 95, 128]
    tx, ty = add_noise(tw_x, tw_y, 2.0)

    # Bottom wing: mirror of top wing
    bw_x = [100, 115, 140, 155]
    bw_y = [128, 148, 162, 128]
    bx2, by2 = add_noise(bw_x, bw_y, 2.0)

    # Tail fin: small triangle at back
    tail_x = [30, 20, 45]
    tail_y = [128, 108, 128]
    tlx, tly = add_noise(tail_x, tail_y, 1.5)

    r = random.random()
    if r < 0.4:
        # Single continuous stroke
        all_x = fuse_x + tw_x[1:] + tw_x[-1::-1] + bw_x[1:] + bw_x[-1::-1] + tail_x[1:]
        all_y = fuse_y + tw_y[1:] + tw_y[-1::-1] + bw_y[1:] + bw_y[-1::-1] + tail_y[1:]
        ax, ay = add_noise(all_x, all_y, 2.5)
        return [[ax, ay]]
    else:
        return [[bx, by], [tx, ty], [bx2, by2], [tlx, tly]]


def sketch_airplane_commercial():
    """
    Commercial jet-style: long narrow body + delta-ish swept wings
    drawn from nose to tail in one or two strokes.
    """
    # Cigar-shaped body
    body_x = [40, 80, 120, 160, 200, 230]
    body_y = [125, 124, 123, 125, 128, 130]
    bx, by = add_noise(body_x, body_y, 2.0)

    # Combined wing stroke (up then down)
    wing_x = [110, 125, 150, 170, 150, 125, 110]
    wing_y = [124, 100, 78, 65, 78, 148, 124]
    wx, wy = add_noise(wing_x, wing_y, 2.0)

    # Tail
    tail_x = [45, 32, 55]
    tail_y = [124, 100, 124]
    tx, ty = add_noise(tail_x, tail_y, 1.5)

    if random.random() < 0.5:
        return [[bx, by], [wx, wy], [tx, ty]]
    else:
        all_x = body_x + wing_x[1:] + tail_x[1:]
        all_y = body_y + wing_y[1:] + tail_y[1:]
        ax, ay = add_noise(all_x, all_y, 2.5)
        return [[ax, ay]]


def sketch_bicycle():
    w1x, w1y = make_circle_stroke(80, 160, 28, 16)
    w2x, w2y = make_circle_stroke(185, 160, 28, 16)
    f1x, f1y = make_line_stroke(80, 160, 130, 160, 6)
    f2x, f2y = make_line_stroke(80, 160, 115, 110, 6)
    f3x, f3y = make_line_stroke(130, 160, 115, 110, 6)
    f4x, f4y = make_line_stroke(130, 160, 165, 100, 6)
    f5x, f5y = make_line_stroke(115, 110, 165, 100, 6)
    f6x, f6y = make_line_stroke(165, 100, 185, 160, 6)
    hx, hy = make_line_stroke(160, 95, 175, 95, 4)
    return [[w1x, w1y], [w2x, w2y], [f1x, f1y], [f2x, f2y], [f3x, f3y], [f4x, f4y], [f5x, f5y], [f6x, f6y], [hx, hy]]


def sketch_boat():
    # Hull curve + sail triangle
    hull_x, hull_y = make_arc_stroke(128, 140, 70, 0.2, math.pi - 0.2, 16)
    deck_x, deck_y = make_line_stroke(60, 155, 196, 155, 12)
    mast_x, mast_y = make_line_stroke(128, 70, 128, 155, 8)
    sail_x, sail_y = make_line_stroke(128, 75, 175, 145, 8)
    sail_b_x, sail_b_y = make_line_stroke(175, 145, 128, 145, 6)
    return [[hull_x, hull_y], [deck_x, deck_y], [mast_x, mast_y], [sail_x, sail_y], [sail_b_x, sail_b_y]]


# ---- NATURE SKETCH GENERATORS ----
def sketch_tree():
    t1x, t1y = make_line_stroke(120, 145, 120, 215, 8)
    t2x, t2y = make_line_stroke(136, 145, 136, 215, 8)
    cx, cy = make_circle_stroke(128, 110, 48, 24)
    c2x, c2y = make_circle_stroke(105, 120, 30, 16)
    c3x, c3y = make_circle_stroke(151, 120, 30, 16)
    return [[t1x, t1y], [t2x, t2y], [cx, cy], [c2x, c2y], [c3x, c3y]]


def sketch_sun():
    cx, cy = make_circle_stroke(128, 128, 35, 20)
    rays = []
    for ang in np.linspace(0, 2*math.pi, 8, endpoint=False):
        x1 = 128 + 42 * math.cos(ang)
        y1 = 128 + 42 * math.sin(ang)
        x2 = 128 + 65 * math.cos(ang)
        y2 = 128 + 65 * math.sin(ang)
        rx, ry = make_line_stroke(x1, y1, x2, y2, 5)
        rays.append([rx, ry])
    return [[cx, cy]] + rays


def sketch_mountain():
    p1x, p1y = make_line_stroke(50, 195, 128, 75, 12)
    p2x, p2y = make_line_stroke(128, 75, 210, 195, 12)
    p3x, p3y = make_line_stroke(165, 130, 215, 85, 8)
    p4x, p4y = make_line_stroke(215, 85, 245, 195, 8)
    gx, gy = make_line_stroke(40, 195, 255, 195, 14)
    return [[p1x, p1y], [p2x, p2y], [p3x, p3y], [p4x, p4y], [gx, gy]]


def sketch_flower():
    cx, cy = make_circle_stroke(128, 105, 18, 14)
    petals = []
    for a in np.linspace(0, 2*math.pi, 5, endpoint=False):
        px = 128 + 32 * math.cos(a)
        py = 105 + 32 * math.sin(a)
        prx, pry = make_circle_stroke(px, py, 14, 10)
        petals.append([prx, pry])
    sx, sy = make_line_stroke(128, 123, 128, 215, 8)
    lx, ly = make_arc_stroke(140, 165, 16, 0, math.pi, 8)
    return [[cx, cy]] + petals + [[sx, sy], [lx, ly]]


def sketch_cloud():
    # Puffy cloud with 4 arcs
    a1x, a1y = make_arc_stroke(90, 130, 28, math.pi, 2 * math.pi, 12)
    a2x, a2y = make_arc_stroke(130, 115, 34, math.pi, 2 * math.pi, 14)
    a3x, a3y = make_arc_stroke(170, 130, 28, math.pi, 2 * math.pi, 12)
    base_x, base_y = make_line_stroke(65, 130, 195, 130, 12)
    return [[a1x, a1y], [a2x, a2y], [a3x, a3y], [base_x, base_y]]


GENERATOR_REGISTRY = {
    "Animal": [sketch_cat, sketch_dog, sketch_fish, sketch_bird, sketch_snake],
    "Object": [sketch_chair, sketch_cup, sketch_clock, sketch_umbrella, sketch_table],
    "Food": [sketch_apple, sketch_pizza, sketch_cake, sketch_ice_cream, sketch_burger],
    "Vehicle": [sketch_car, sketch_car_outline, sketch_bus, sketch_bus_outline, sketch_airplane_stick, sketch_airplane_outline, sketch_airplane_swept_airliner, sketch_airplane_facing_left, sketch_airplane_wide_flat, sketch_airplane_commercial, sketch_bicycle, sketch_boat],
    "Nature": [sketch_tree, sketch_sun, sketch_mountain, sketch_flower, sketch_cloud],
}


def augment_stroke_style(strokes):
    """
    Simulates human drawing habits:
    - Continuous drawing (no pen lift: 1-2 strokes)
    - Normal multi-stroke drawing
    This ensures that all categories have diverse stroke counts (1, 2, 3, 5+ strokes).
    """
    if len(strokes) <= 1:
        return strokes

    r = random.random()
    if r < 0.35:
        # Merge into 1 single continuous stroke
        all_xs = []
        all_ys = []
        for s in strokes:
            all_xs.extend(s[0])
            all_ys.extend(s[1])
        return [[all_xs, all_ys]]
    elif r < 0.60 and len(strokes) >= 3:
        # Merge into 2 strokes
        mid = len(strokes) // 2
        s1_x, s1_y = [], []
        for s in strokes[:mid]:
            s1_x.extend(s[0])
            s1_y.extend(s[1])
        s2_x, s2_y = [], []
        for s in strokes[mid:]:
            s2_x.extend(s[0])
            s2_y.extend(s[1])
        return [[s1_x, s1_y], [s2_x, s2_y]]

    return strokes


def generate_dataset(samples_per_category: int = 600, seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)

    all_features = []
    all_labels = []
    all_bitmaps = []
    metadata = {
        "categories": list(CATEGORY_MAP.values()),
        "category_counts": {},
        "total_samples": 0,
        "feature_count": 77
    }

    for cat_name, cat_id in CATEGORY_TO_ID.items():
        generators = GENERATOR_REGISTRY[cat_name]
        cat_samples = 0
        print(f"Generating {samples_per_category} samples for category: {cat_name}...")

        while cat_samples < samples_per_category:
            gen_func = random.choice(generators)
            strokes = gen_func()

            # Apply stroke style diversity augmentation (single stroke / multi stroke)
            strokes = augment_stroke_style(strokes)

            # Random slight rotation, scaling, and offset
            angle_rot = random.uniform(-0.18, 0.18)
            scale_fac = random.uniform(0.82, 1.18)
            cos_a, sin_a = math.cos(angle_rot), math.sin(angle_rot)

            transformed_strokes = []
            for stroke in strokes:
                xs, ys = stroke[0], stroke[1]
                txs = []
                tys = []
                for x, y in zip(xs, ys):
                    # Center around 128
                    cx, cy = x - 128, y - 128
                    rx = (cx * cos_a - cy * sin_a) * scale_fac + 128 + random.uniform(-10, 10)
                    ry = (cx * sin_a + cy * cos_a) * scale_fac + 128 + random.uniform(-10, 10)
                    txs.append(rx)
                    tys.append(ry)
                transformed_strokes.append([txs, tys])

            features = extract_features_from_strokes(transformed_strokes)
            bitmap_28 = rasterize_strokes(transformed_strokes, grid_size=28)

            all_features.append(features)
            all_labels.append(cat_id)
            all_bitmaps.append(bitmap_28)
            cat_samples += 1

        metadata["category_counts"][cat_name] = cat_samples

    X = np.array(all_features, dtype=np.float32)
    y = np.array(all_labels, dtype=np.int64)
    bitmaps = np.array(all_bitmaps, dtype=np.float32)
    metadata["total_samples"] = len(y)

    return X, y, bitmaps, metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=600, help="Samples per category")
    parser.add_argument("--out_dir", type=str, default="", help="Output directory")
    args = parser.parse_args()

    out_dir = args.out_dir
    if not out_dir:
        out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset")
    os.makedirs(out_dir, exist_ok=True)

    X, y, bitmaps, meta = generate_dataset(samples_per_category=args.samples)
    print(f"Generated dataset shape: X={X.shape}, y={y.shape}, bitmaps={bitmaps.shape}")

    npz_path = os.path.join(out_dir, "quickdraw_sampled.npz")
    np.savez_compressed(npz_path, X=X, y=y, bitmaps=bitmaps)
    print(f"Saved dataset to: {npz_path}")

    meta_path = os.path.join(out_dir, "dataset_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Saved metadata to: {meta_path}")
