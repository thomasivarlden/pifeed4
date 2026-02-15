#!/usr/bin/env python3
"""Generate 10 dark, cinematic 1920x1080 background images for PiFeed4."""

import math
import os
from PIL import Image, ImageDraw, ImageFilter

WIDTH, HEIGHT = 1920, 1080
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backgrounds")
os.makedirs(OUT_DIR, exist_ok=True)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def clamp(v, lo=0, hi=255):
    return max(lo, min(hi, int(v)))


# ---------------------------------------------------------------------------
# Gradient generators
# ---------------------------------------------------------------------------

def radial_gradient(img, cx_frac, cy_frac, c_inner, c_outer, radius_frac=1.0):
    """Draw a radial gradient centred at (cx_frac, cy_frac) of the image."""
    px = img.load()
    w, h = img.size
    cx, cy = cx_frac * w, cy_frac * h
    max_r = radius_frac * math.hypot(w, h)
    for y in range(h):
        for x in range(w):
            d = math.hypot(x - cx, y - cy)
            t = min(d / max_r, 1.0)
            px[x, y] = lerp_color(c_inner, c_outer, t)
    return img


def diagonal_gradient(img, c_tl, c_br, angle_deg=45):
    """Two-color gradient along an arbitrary angle."""
    px = img.load()
    w, h = img.size
    rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    proj_min = 0
    proj_max = cos_a * w + sin_a * h
    span = proj_max - proj_min if proj_max != proj_min else 1
    for y in range(h):
        for x in range(w):
            proj = cos_a * x + sin_a * y
            t = max(0.0, min(1.0, (proj - proj_min) / span))
            px[x, y] = lerp_color(c_tl, c_br, t)
    return img


def two_point_radial(img, cx1, cy1, c1, cx2, cy2, c2, base):
    """Blend two radial blobs of colour onto a dark base."""
    px = img.load()
    w, h = img.size
    max_r = 0.55 * math.hypot(w, h)
    for y in range(h):
        for x in range(w):
            d1 = math.hypot(x - cx1 * w, y - cy1 * h) / max_r
            d2 = math.hypot(x - cx2 * w, y - cy2 * h) / max_r
            t1 = max(0.0, 1.0 - d1)
            t2 = max(0.0, 1.0 - d2)
            r = clamp(base[0] + t1 * (c1[0] - base[0]) + t2 * (c2[0] - base[0]))
            g = clamp(base[1] + t1 * (c1[1] - base[1]) + t2 * (c2[1] - base[1]))
            b = clamp(base[2] + t1 * (c1[2] - base[2]) + t2 * (c2[2] - base[2]))
            px[x, y] = (r, g, b)
    return img


# ---------------------------------------------------------------------------
# Vignette overlay
# ---------------------------------------------------------------------------

def apply_vignette(img, strength=0.55, radius_frac=0.75):
    """Darken edges with a smooth vignette."""
    px = img.load()
    w, h = img.size
    cx, cy = w / 2, h / 2
    max_r = radius_frac * math.hypot(cx, cy)
    for y in range(h):
        for x in range(w):
            d = math.hypot(x - cx, y - cy)
            t = max(0.0, (d - max_r * 0.5) / (max_r * 0.5))
            t = min(1.0, t) * strength
            r, g, b = px[x, y]
            px[x, y] = (clamp(r * (1 - t)), clamp(g * (1 - t)), clamp(b * (1 - t)))
    return img


# ---------------------------------------------------------------------------
# Background definitions  (all colours kept in ~0.15-0.30 value range)
# ---------------------------------------------------------------------------

backgrounds = [
    # 1 - Deep blue radial
    {
        "name": "bg_01.png",
        "type": "radial",
        "cx": 0.5, "cy": 0.45,
        "c_inner": (20, 35, 75),
        "c_outer": (5, 8, 20),
        "vignette": 0.50,
    },
    # 2 - Teal diagonal
    {
        "name": "bg_02.png",
        "type": "diagonal",
        "angle": 35,
        "c_tl": (8, 50, 55),
        "c_br": (4, 15, 22),
        "vignette": 0.55,
    },
    # 3 - Indigo two-blob
    {
        "name": "bg_03.png",
        "type": "two_blob",
        "cx1": 0.25, "cy1": 0.35, "c1": (35, 20, 70),
        "cx2": 0.75, "cy2": 0.65, "c2": (18, 15, 55),
        "base": (6, 5, 18),
        "vignette": 0.45,
    },
    # 4 - Dark red radial
    {
        "name": "bg_04.png",
        "type": "radial",
        "cx": 0.55, "cy": 0.5,
        "c_inner": (65, 15, 15),
        "c_outer": (18, 5, 5),
        "vignette": 0.55,
    },
    # 5 - Forest green diagonal
    {
        "name": "bg_05.png",
        "type": "diagonal",
        "angle": 140,
        "c_tl": (6, 18, 10),
        "c_br": (14, 48, 22),
        "vignette": 0.50,
    },
    # 6 - Charcoal radial (near-monochrome)
    {
        "name": "bg_06.png",
        "type": "radial",
        "cx": 0.48, "cy": 0.48,
        "c_inner": (42, 42, 44),
        "c_outer": (10, 10, 12),
        "vignette": 0.60,
    },
    # 7 - Navy two-blob
    {
        "name": "bg_07.png",
        "type": "two_blob",
        "cx1": 0.3, "cy1": 0.6, "c1": (12, 22, 60),
        "cx2": 0.7, "cy2": 0.3, "c2": (10, 30, 50),
        "base": (4, 6, 16),
        "vignette": 0.50,
    },
    # 8 - Slate diagonal
    {
        "name": "bg_08.png",
        "type": "diagonal",
        "angle": 65,
        "c_tl": (30, 35, 42),
        "c_br": (8, 10, 14),
        "vignette": 0.55,
    },
    # 9 - Deep purple radial
    {
        "name": "bg_09.png",
        "type": "radial",
        "cx": 0.45, "cy": 0.55,
        "c_inner": (50, 18, 60),
        "c_outer": (12, 5, 16),
        "vignette": 0.50,
    },
    # 10 - Dark amber two-blob
    {
        "name": "bg_10.png",
        "type": "two_blob",
        "cx1": 0.4, "cy1": 0.4, "c1": (65, 40, 10),
        "cx2": 0.7, "cy2": 0.7, "c2": (50, 25, 8),
        "base": (14, 8, 4),
        "vignette": 0.50,
    },
]


def generate(spec):
    img = Image.new("RGB", (WIDTH, HEIGHT))

    if spec["type"] == "radial":
        radial_gradient(img, spec["cx"], spec["cy"],
                        spec["c_inner"], spec["c_outer"], radius_frac=0.7)
    elif spec["type"] == "diagonal":
        diagonal_gradient(img, spec["c_tl"], spec["c_br"], spec["angle"])
    elif spec["type"] == "two_blob":
        two_point_radial(img,
                         spec["cx1"], spec["cy1"], spec["c1"],
                         spec["cx2"], spec["cy2"], spec["c2"],
                         spec["base"])

    # Light Gaussian blur to ensure perfectly smooth gradients
    img = img.filter(ImageFilter.GaussianBlur(radius=4))

    # Vignette
    apply_vignette(img, strength=spec.get("vignette", 0.5))

    path = os.path.join(OUT_DIR, spec["name"])
    img.save(path, "PNG", optimize=True)
    return path


if __name__ == "__main__":
    for i, spec in enumerate(backgrounds, 1):
        path = generate(spec)
        print(f"[{i:2d}/10] {path}")
    print("Done.")
