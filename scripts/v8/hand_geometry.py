"""hand_geometry.py - Geometria vectorial determinista de la mano (V8).

Fuente unica de verdad de la silueta, landmarks y anclas de lineas/montes.
La silueta es una union de primitivas (palma, muñeca y 5 dedos capsula) con
contorno exterior continuo por construccion: se dibuja una capa de contorno
(primitivas expandidas en color de trazo) y encima la capa de piel, que
cubre los trazos internos. Sin numeros magicos y sin raster.

Mano izquierda palmar (dedos arriba, pulgar a la DERECHA). La mano derecha
es un espejo declarado (x' = W - x), no un recorte.

Uso:
  python hand_geometry.py --emit
  python hand_geometry.py --selftest
  python hand_geometry.py --landmarks
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE))
import svg_render  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parents[2]
HANDS_DIR = SCRIPT_DIR / "assets" / "v7" / "hands"

VIEWBOX = 1024
SKIN = "#F3C9B4"
SKIN_LINE = "#C98775"
STROKE_W = 10.0

FINGERS = {
    "index":  {"base": (410, 548), "tip": (388, 138), "width": 78, "order": 0},
    "middle": {"base": (508, 540), "tip": (512, 100), "width": 82, "order": 1},
    "ring":   {"base": (606, 548), "tip": (632, 150), "width": 76, "order": 2},
    "pinky":  {"base": (694, 588), "tip": (752, 282), "width": 62, "order": 3},
    "thumb":  {"base": (690, 700), "tip": (930, 300), "width": 100, "order": 4},
}
PALM = {"center": (516, 700), "rx": 208, "ry": 250}
WRIST = {"center": (516, 900), "rx": 138, "ry": 112}


def primitives():
    """Lista ordenada (tipo, params) de las primitivas de la silueta."""
    prims = [("ellipse", PALM), ("ellipse", WRIST)]
    for name in sorted(FINGERS, key=lambda k: FINGERS[k]["order"]):
        prims.append(("capsule", FINGERS[name]))
    return prims


def _ellipse_d(cx, cy, rx, ry):
    return svg_render._ellipse_path(cx, cy, rx, ry)


def _capsule_path(x0, y0, x1, y1):
    return f"M{x0} {y0} L{x1} {y1}"


def hand_svg(side="L"):
    """SVG maestro: capa contorno + capa piel (union con borde continuo)."""
    outline, skin = [], []
    for kind, p in primitives():
        if kind == "ellipse":
            d = _ellipse_d(p["center"][0], p["center"][1], p["rx"], p["ry"])
            outline.append(
                f'<path d="{d}" fill="{SKIN_LINE}" stroke="{SKIN_LINE}" '
                f'stroke-width="{2 * STROKE_W:.0f}"/>')
            skin.append(f'<path d="{d}" fill="{SKIN}" stroke="none"/>')
        else:
            d = _capsule_path(p["base"][0], p["base"][1], p["tip"][0], p["tip"][1])
            outline.append(
                f'<path d="{d}" fill="none" stroke="{SKIN_LINE}" '
                f'stroke-width="{p["width"] + 2 * STROKE_W:.1f}" '
                f'stroke-linecap="round"/>')
            skin.append(
                f'<path d="{d}" fill="none" stroke="{SKIN}" '
                f'stroke-width="{p["width"]:.1f}" stroke-linecap="round"/>')
    body = "".join(outline + skin)
    transform = ""
    if side.upper() == "R":
        transform = f' transform="translate({VIEWBOX},0) scale(-1,1)"'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {VIEWBOX} {VIEWBOX}"><g{transform}>{body}</g></svg>')


def derived_landmarks():
    lm = {}
    for name, p in FINGERS.items():
        bx, by = p["base"]
        tx, ty = p["tip"]
        lm[name] = {
            "base": [bx, by],
            "tip": [tx, ty],
            "mid": [(bx + tx) / 2.0, (by + ty) / 2.0],
            "width": p["width"],
        }
    lm["palm"] = {"center": list(PALM["center"]),
                  "radii": [PALM["rx"], PALM["ry"]]}
    lm["wrist"] = {"center": list(WRIST["center"]),
                   "radii": [WRIST["rx"], WRIST["ry"]]}
    return lm


def landmarks_json(side="L"):
    lm = derived_landmarks()
    if side.upper() == "R":
        for name, item in lm.items():
            if "base" in item:
                item["base"][0] = VIEWBOX - item["base"][0]
                item["tip"][0] = VIEWBOX - item["tip"][0]
                item["mid"][0] = VIEWBOX - item["mid"][0]
            if "center" in item:
                item["center"][0] = VIEWBOX - item["center"][0]
    return {"viewBox": [VIEWBOX, VIEWBOX], "side": side.upper(), "landmarks": lm}


def palm_line_anchors():
    """Puntos de control (p0,c1,c2,p3) para las 4 lineas, en la mano."""
    return {
        "vida": [(470, 565), (428, 645), (452, 765), (505, 882)],
        "cabeza": [(688, 600), (600, 612), (470, 600), (372, 560)],
        "corazon": [(690, 648), (600, 560), (470, 540), (372, 600)],
        "destino": [(518, 498), (516, 620), (508, 760), (505, 886)],
    }


def palm_mounts():
    """Montes (x, y, radio) derivados de la estructura de la mano."""
    return {
        "venus": (655, 785, 95),
        "jupiter": (430, 500, 55),
        "saturno": (516, 490, 52),
        "sol": (612, 500, 52),
        "mercurio": (702, 560, 48),
    }


def count_finger_runs(mask, row):
    """Cuenta tramos rellenos distintos en una fila de la mascara."""
    runs, inside = 0, False
    for v in mask[row]:
        if v and not inside:
            runs += 1
            inside = True
        elif not v:
            inside = False
    return runs


def _finger_scan(side="L"):
    mask, (rw, rh) = svg_render.render_svg_to_mask(hand_svg(side), VIEWBOX, VIEWBOX)
    best = 0
    for y in range(int(rh * 0.15), int(rh * 0.55)):
        best = max(best, count_finger_runs(mask, y))
    return best


def selftest(side="L"):
    runs = _finger_scan(side)
    return {"side": side.upper(), "finger_runs": runs, "ok": runs == 5}


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
