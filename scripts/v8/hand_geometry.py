"""hand_geometry.py - Mano vectorial determinista de alta calidad (V8.1).

Construye la silueta de la mano a partir de primitivas anatomicas bien
proporcionadas (palma trapezoidal, 4 dedos afinados con punta redonda,
pulgar y muñeca) y extrae el contorno exterior como UN unico path de
Bezier cubicos, de modo que la linea exterior es continua por construccion.

Pipeline interno:
  1. rasteriza la union de primitivas (supersampleado)
  2. traza el contorno exterior (marching squares via matplotlib)
  3. simplifica (Douglas-Peucker cerrado) y suaviza (Catmull-Rom -> Bezier)
  4. emite el SVG maestro (path unico, relleno + trazo)

Mano izquierda palmar (dedos arriba, pulgar a la DERECHA). La derecha es
un espejo declarado (x' = W - x).

Reglas (docs/v7/03-IMAGENES-Y-ORTOGRAFIA.md): exactamente cinco dedos
claramente diferenciables, puntas completas, muñeca completa, sin texto ni
lineas de quiromancia dentro del raster, lateralidad declarada.

Uso:
  python hand_geometry.py --emit
  python hand_geometry.py --selftest
  python hand_geometry.py --landmarks
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import svg_render  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parents[2]
HANDS_DIR = SCRIPT_DIR / "assets" / "v7" / "hands"

VIEWBOX = 1024
SKIN = "#F0C3AC"
SKIN_LINE = "#B9795F"
STROKE_W = 8.0
SUPERSAMPLE = 3

# ── Primitivas anatomicas (espacio 1024x1024) ───────────────────────────
PALM = [(340, 505), (660, 505), (688, 590), (700, 700), (674, 795), (634, 838),
        (366, 838), (326, 795), (300, 700), (312, 590)]
WRIST = {"x0": 405, "y0": 810, "x1": 600, "y1": 1000, "r": 45}
FINGERS = {
    "index":  {"base": (398, 520), "tip": (372, 165), "wb": 78, "wt": 60},
    "middle": {"base": (492, 508), "tip": (494, 78),  "wb": 82, "wt": 62},
    "ring":   {"base": (584, 520), "tip": (612, 138), "wb": 76, "wt": 58},
    "pinky":  {"base": (670, 565), "tip": (712, 292), "wb": 62, "wt": 46},
}
THUMB = {"base": (700, 745), "tip": (915, 500), "wb": 96, "wt": 66}
PALM_CENTER = (500.0, 665.0)
PALM_RADII = (200.0, 180.0)

_PATH_CACHE = {}


def _tapered_poly(base, tip, wb, wt, n=26):
    bx, by = base
    tx, ty = tip
    dx, dy = tx - bx, ty - by
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    px, py = -uy, ux
    pts = []
    for i in range(n + 1):
        t = i / n
        w = wb + (wt - wb) * t
        pts.append((bx + dx * t + px * w / 2, by + dy * t + py * w / 2))
    for i in range(1, n):
        a = math.pi * i / n
        r = wt / 2
        pts.append((tx + px * math.cos(a) * r + ux * math.sin(a) * r,
                    ty + py * math.cos(a) * r + uy * math.sin(a) * r))
    for i in range(n + 1):
        t = 1 - i / n
        w = wb + (wt - wb) * t
        pts.append((bx + dx * t - px * w / 2, by + dy * t - py * w / 2))
    return pts


def _rounded_rect(x0, y0, x1, y1, r, n=10):
    pts = [(x0 + r, y0), (x1 - r, y0)]
    for cx, cy, a0, a1 in [(x1 - r, y0 + r, -math.pi / 2, 0),
                           (x1 - r, y1 - r, 0, math.pi / 2),
                           (x0 + r, y1 - r, math.pi / 2, math.pi),
                           (x0 + r, y0 + r, math.pi, 3 * math.pi / 2)]:
        for i in range(n + 1):
            a = a0 + (a1 - a0) * i / n
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def build_mask(size=VIEWBOX, ss=SUPERSAMPLE):
    """Rasteriza la union de primitivas y devuelve una mascara booleana."""
    from PIL import Image, ImageDraw
    import numpy as np
    W = size * ss
    img = Image.new("L", (W, W), 0)
    d = ImageDraw.Draw(img)
    sc = lambda pts: [(x * ss, y * ss) for x, y in pts]
    d.polygon(sc(PALM), fill=255)
    d.polygon(sc(_rounded_rect(WRIST["x0"], WRIST["y0"], WRIST["x1"],
                               WRIST["y1"], WRIST["r"])), fill=255)
    for f in FINGERS.values():
        d.polygon(sc(_tapered_poly(f["base"], f["tip"], f["wb"], f["wt"])), fill=255)
    d.polygon(sc(_tapered_poly(THUMB["base"], THUMB["tip"], THUMB["wb"],
                               THUMB["wt"])), fill=255)
    img = img.resize((size, size), Image.LANCZOS)
    return np.array(img) > 127


# ── Trazado del contorno a un unico path Bezier ─────────────────────────
def _trace_contour(mask):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure()
    ax = fig.add_subplot(111)
    cs = ax.contour(mask.astype(float), levels=[0.5])
    segs = cs.allsegs[0]
    plt.close(fig)
    seg = max(segs, key=len)
    return [(float(x), float(y)) for x, y in seg]


def _rdp(points, eps):
    pts = points
    n = len(pts)
    if n < 3:
        return pts
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        x1, y1 = pts[i]
        x2, y2 = pts[j]
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1e-9
        dmax, idx = 0.0, -1
        for k in range(i + 1, j):
            x0, y0 = pts[k]
            d = abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / L
            if d > dmax:
                dmax, idx = d, k
        if dmax > eps:
            keep[idx] = True
            stack.append((i, idx))
            stack.append((idx, j))
    return [pts[i] for i in range(n) if keep[i]]


def _rdp_closed(points, eps):
    pts = points
    n = len(pts)
    if n < 4:
        return pts
    x0, y0 = pts[0]
    far = max(range(n), key=lambda i: (pts[i][0] - x0) ** 2 + (pts[i][1] - y0) ** 2)
    a = _rdp(pts[0:far + 1], eps)
    b = _rdp(pts[far:] + [pts[0]], eps)
    return a[:-1] + b[:-1]


def _catmull_closed(pts):
    n = len(pts)
    out = []
    for i in range(n):
        p0 = pts[(i - 1) % n]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6.0, p1[1] + (p2[1] - p0[1]) / 6.0)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6.0, p2[1] - (p3[1] - p1[1]) / 6.0)
        out.append((p1, c1, c2, p2))
    return out


def _segments_to_d(segs):
    p0 = segs[0][0]
    s = f"M{p0[0]:.1f} {p0[1]:.1f}"
    for _, c1, c2, p in segs:
        s += (f"C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} "
              f"{p[0]:.1f} {p[1]:.1f}")
    return s + "Z"


def hand_path_d(eps=2.2):
    """Path `d` del contorno de la mano izquierda (cacheado)."""
    if "d" in _PATH_CACHE:
        return _PATH_CACHE["d"]
    mask = build_mask()
    contour = _trace_contour(mask)
    simp = _rdp_closed(contour, eps)
    d = _segments_to_d(_catmull_closed(simp))
    _PATH_CACHE["d"] = d
    _PATH_CACHE["points"] = len(simp)
    return d


def hand_svg(side="L"):
    d = hand_path_d()
    transform = ""
    if side.upper() == "R":
        transform = f' transform="translate({VIEWBOX},0) scale(-1,1)"'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {VIEWBOX} {VIEWBOX}">'
            f'<path d="{d}" fill="{SKIN}" stroke="{SKIN_LINE}" '
            f'stroke-width="{STROKE_W:.0f}" stroke-linejoin="round"'
            f'{transform}/></svg>')


def content_bbox():
    """BBox real (x0,y0,x1,y1) del contenido de la mano en el viewBox."""
    if "bbox" in _PATH_CACHE:
        return _PATH_CACHE["bbox"]
    import numpy as np
    mask = build_mask()
    ys, xs = np.where(mask)
    bbox = (float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max()))
    _PATH_CACHE["bbox"] = bbox
    return bbox


# ── Landmarks y anclas de overlays ──────────────────────────────────────
def derived_landmarks():
    lm = {}
    for name, p in FINGERS.items():
        bx, by = p["base"]
        tx, ty = p["tip"]
        lm[name] = {"base": [bx, by], "tip": [tx, ty],
                    "mid": [(bx + tx) / 2.0, (by + ty) / 2.0],
                    "width": p["wb"]}
    lm["thumb"] = {"base": list(THUMB["base"]), "tip": list(THUMB["tip"]),
                   "mid": [(THUMB["base"][0] + THUMB["tip"][0]) / 2.0,
                           (THUMB["base"][1] + THUMB["tip"][1]) / 2.0],
                   "width": THUMB["wb"]}
    lm["palm"] = {"center": list(PALM_CENTER), "radii": list(PALM_RADII)}
    lm["wrist"] = {"center": [(WRIST["x0"] + WRIST["x1"]) / 2.0,
                              (WRIST["y0"] + WRIST["y1"]) / 2.0],
                   "width": WRIST["x1"] - WRIST["x0"]}
    return lm


def landmarks_json(side="L"):
    lm = derived_landmarks()
    if side.upper() == "R":
        for item in lm.values():
            for key in ("base", "tip", "mid", "center"):
                if key in item:
                    item[key][0] = VIEWBOX - item[key][0]
    return {"viewBox": [VIEWBOX, VIEWBOX], "side": side.upper(), "landmarks": lm}


def palm_line_anchors():
    """Puntos de control (p0,c1,c2,p3) de las 4 lineas, dentro de la palma."""
    return {
        "vida": [(462, 560), (430, 640), (440, 760), (492, 845)],
        "cabeza": [(660, 600), (585, 618), (470, 610), (352, 560)],
        "corazon": [(662, 648), (585, 560), (470, 542), (352, 602)],
        "destino": [(500, 520), (500, 640), (492, 760), (492, 848)],
    }


def palm_mounts():
    return {
        "venus": (645, 780, 92),
        "jupiter": (430, 512, 54),
        "saturno": (500, 500, 50),
        "sol": (590, 512, 50),
        "mercurio": (676, 566, 46),
    }


# ── QA: exactamente cinco dedos ─────────────────────────────────────────
def count_digits(mask):
    """Cuenta dedos como componentes con punta por encima de la palma."""
    import numpy as np
    from scipy import ndimage
    yy, xx = np.ogrid[:VIEWBOX, :VIEWBOX]
    disk = ((xx - PALM_CENTER[0]) ** 2 + (yy - PALM_CENTER[1]) ** 2) < 205 ** 2
    m = mask & ~disk
    m[int(PALM_CENTER[1] + 200):, :] = False
    lab, n = ndimage.label(m)
    digits = 0
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if len(ys) < 800:
            continue
        if ys.min() < PALM_CENTER[1] - 90:  # la punta está por encima de la palma
            digits += 1
    return digits


def selftest(side="L"):
    import numpy as np
    svg = hand_svg(side)
    mask, _ = svg_render.render_svg_to_mask(svg, VIEWBOX, VIEWBOX)
    mask = mask > 0
    digits = count_digits(mask)
    return {"side": side.upper(), "digits": digits, "ok": digits == 5,
            "path_points": _PATH_CACHE.get("points")}


def emit_all():
    HANDS_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for side in ("L", "R"):
        fp = HANDS_DIR / f"HAND_{side}_PALM_FRONT_EDITORIAL_V001.svg"
        fp.write_text(hand_svg(side), encoding="utf-8")
        written.append(str(fp))
        meta = fp.with_suffix(".landmarks.json")
        meta.write_text(json.dumps(landmarks_json(side), indent=2,
                                   ensure_ascii=False), encoding="utf-8")
        written.append(str(meta))
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--landmarks", action="store_true")
    a = ap.parse_args()
    if a.landmarks:
        print(json.dumps(landmarks_json("L"), indent=2, ensure_ascii=False))
    if a.emit:
        for fp in emit_all():
            print("escrito:", fp)
    if a.selftest or not (a.emit or a.landmarks):
        print(json.dumps(selftest("L"), ensure_ascii=False))


if __name__ == "__main__":
    main()
