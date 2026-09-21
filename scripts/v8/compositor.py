"""compositor.py - Compositor por capas V8 (reemplaza generate_images.py).

Orden de capas (docs/v7/03): background -> hand -> natural_creases ->
palm_lines -> zones -> markers -> guides -> labels -> captions -> effects.

La mano es SVG vectorial (hand_geometry) renderizada con svg_render; las
lineas/montes se derivan de los landmarks, por lo que alinean por
construccion. El texto se dibuja con Cairo y fuente del sistema (Segoe UI),
nunca dentro de una imagen generada.

Salida:
  data/images/scene_XXX/f_YYY.png
  data/jobs/<jid>/images.json

Uso:
  python compositor.py --storyboard <ruta> --frames 7 --profile test_30s
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import cairo  # noqa: E402
import yaml  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import hand_geometry as hg  # noqa: E402
import svg_render  # noqa: E402
import svg_sanitizer  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parents[2]
IMAGES_DIR = SCRIPT_DIR / "data" / "images"
VISUAL_PROFILES = SCRIPT_DIR / "config" / "v7" / "visual_profiles.yaml"

LCOL = {
    "corazon": (0.00, 0.78, 0.86),
    "cabeza": (0.00, 0.71, 0.39),
    "destino": (0.90, 0.47, 0.12),
    "vida": (0.83, 0.20, 0.31),
}
MCOL = {
    "venus": (0.98, 0.47, 0.59),
    "jupiter": (0.94, 0.82, 0.20),
    "saturno": (0.94, 0.59, 0.16),
    "sol": (0.90, 0.24, 0.24),
    "mercurio": (0.90, 0.24, 0.63),
}
DASH = {"corazon": [8, 4], "cabeza": [4, 4], "destino": [12, 4, 4, 4], "vida": [10, 5]}

SCFG = {
    1: {"title": "LECTURA DE MANO", "subtitle": "La Línea de la Vida", "hl": "vida"},
    2: {"title": "PUNTOS DE PARTIDA", "subtitle": "Tres orígenes posibles", "hl": "vida"},
    3: {"title": "FORMA DEL NACIMIENTO", "subtitle": "Curva amplia vs estrecha", "hl": "vida"},
    4: {"title": "PROFUNDIDAD Y VITALIDAD", "subtitle": "Lo que la línea revela", "hl": "vida"},
}

HAND_SVG_L = hg.hand_svg("L")
HAND_SVG_R = hg.hand_svg("R")

# Pre-rendered solid hand PNGs (filled, with lines and mounts)
HAND_PNG_L = SCRIPT_DIR / "assets" / "v8" / "hands" / "mano_izquierda_solid.png"
HAND_PNG_R = SCRIPT_DIR / "assets" / "v8" / "hands" / "mano_derecha_solid.png"

def _load_png(path):
    """Load a PNG file into a Cairo ImageSurface."""
    if path.exists():
        return cairo.ImageSurface.create_from_png(str(path))
    return None

_HAND_PNG_CACHE = {}

def _get_hand_png(side):
    key = side.upper()
    if key not in _HAND_PNG_CACHE:
        p = HAND_PNG_L if key == "L" else HAND_PNG_R
        _HAND_PNG_CACHE[key] = _load_png(p)
    return _HAND_PNG_CACHE[key]


def load_visual_profile(name="cosmic_educational_v1"):
    try:
        data = yaml.safe_load(VISUAL_PROFILES.read_text(encoding="utf-8"))
        return data["profiles"].get(name, {})
    except Exception:
        return {}


def bez3(p0, p1, p2, p3, n=48):
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
        y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
        out.append((x, y))
    return out


def anchors(side="L"):
    """lineas y montes en coordenadas 1024 de la mano, con espejo."""
    raw_lines, raw_mounts = hg.anchors()
    lines = {}
    for name, pts in raw_lines.items():
        # Convert list of points to smooth path using simple interpolation
        if len(pts) >= 2:
            smooth = []
            for i in range(len(pts) - 1):
                p0 = pts[i]
                p1 = pts[i + 1]
                for t_i in range(12):
                    t = t_i / 12
                    x = p0[0] + (p1[0] - p0[0]) * t
                    y = p0[1] + (p1[1] - p0[1]) * t
                    smooth.append((x, y))
            smooth.append(pts[-1])
            if side.upper() == "R":
                smooth = [(hg.VB - x, y) for x, y in smooth]
            lines[name] = smooth
    mounts = {}
    for name, (mx, my, mr) in raw_mounts.items():
        if side.upper() == "R":
            mx = hg.VB - mx
        mounts[name] = (mx, my, mr)
    return lines, mounts


# ── Fondo cosmico cacheado ──────────────────────────────────────────────
def build_space_bg(w, h):
    cache = IMAGES_DIR / f"_bg_space_{w}x{h}.png"
    if cache.exists():
        return cairo.ImageSurface.create_from_png(str(cache))
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(surf)
    for y in range(h):
        r = y / h
        ctx.set_source_rgb(0.03 + 0.07 * r, 0.02 + 0.03 * r, 0.11 + 0.17 * r)
        ctx.move_to(0, y)
        ctx.line_to(w, y)
        ctx.stroke()
    random.seed(42)
    for _ in range(340):
        x, y = random.randint(0, w), random.randint(0, h)
        b = random.random() * 0.6 + 0.4
        ctx.set_source_rgb(b, b, b)
        ctx.arc(x, y, random.choice([1, 1, 1, 1.5, 2]), 0, 6.283)
        ctx.fill()
    for _ in range(4):
        x, y = random.randint(0, w), random.randint(0, h)
        g = cairo.RadialGradient(x, y, 0, x, y, 180)
        g.add_color_stop_rgba(0.6, 0.12, 0.10, 0.25, 0.5)
        g.add_color_stop_rgba(1, 0.12, 0.10, 0.25, 0)
        ctx.set_source(g)
        ctx.arc(x, y, 180, 0, 6.283)
        ctx.fill()
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    surf.write_to_png(str(cache))
    return cairo.ImageSurface.create_from_png(str(cache))


def _set_font(ctx, size, bold=False):
    ctx.select_font_face("Segoe UI", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)


def _rrect(ctx, x, y, w, h, r):
    ctx.new_path()
    ctx.move_to(x + r, y)
    ctx.line_to(x + w - r, y)
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.line_to(x + w, y + h - r)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.line_to(x + r, y + h)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.line_to(x, y + r)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def draw_partial(ctx, pts, frac, color, lw=6, dash=None, glow=False):
    if frac <= 0 or len(pts) < 2:
        return
    n = max(2, int(len(pts) * min(1.0, frac)) + 1)
    sub = pts[:n]
    if glow:
        for gw, a in [(lw * 5, 0.12), (lw * 3.5, 0.20),
                      (lw * 2.2, 0.30), (lw * 1.4, 0.45)]:
            ctx.set_source_rgba(min(1, color[0] + 0.3), min(1, color[1] + 0.3),
                                min(1, color[2] + 0.3), a)
            ctx.set_line_width(gw)
            ctx.set_dash([])
            ctx.move_to(*sub[0])
            for p in sub[1:]:
                ctx.line_to(*p)
            ctx.stroke()
    ctx.set_source_rgb(*color)
    ctx.set_line_width(lw)
    ctx.set_dash(dash or [])
    ctx.move_to(*sub[0])
    for p in sub[1:]:
        ctx.line_to(*p)
    ctx.stroke()
    ctx.set_dash([])


def draw_pulsing_point(ctx, x, y, color, phase, base_r=12):
    for gw, a in [(base_r * 2.2, 0.18), (base_r * 1.6, 0.30)]:
        ctx.set_source_rgba(color[0], color[1], color[2], a * (1 - phase * 0.5))
        ctx.arc(x, y, gw * (0.8 + phase * 0.4), 0, 6.283)
        ctx.fill()
    ctx.set_source_rgb(*color)
    ctx.arc(x, y, base_r, 0, 6.283)
    ctx.fill()
    ctx.set_source_rgb(1, 1, 1)
    ctx.set_line_width(3)
    ctx.arc(x, y, base_r, 0, 6.283)
    ctx.stroke()


def _label(ctx, lx, ly, tx, ty, text, fs=28, col=(1, 1, 1), alpha=1.0):
    if alpha <= 0.02:
        return
    _set_font(ctx, fs, True)
    ext = ctx.text_extents(text)
    tw, th = ext.width, ext.height
    pad = 8
    ctx.set_source_rgba(0, 0, 0, 0.85 * alpha)
    _rrect(ctx, lx - pad, ly - pad, tw + 2 * pad, th + 2 * pad + 4, 6)
    ctx.fill()
    ctx.set_source_rgba(1, 1, 1, 0.25 * alpha)
    ctx.set_line_width(1)
    _rrect(ctx, lx - pad, ly - pad, tw + 2 * pad, th + 2 * pad + 4, 6)
    ctx.stroke()
    ctx.set_source_rgba(col[0], col[1], col[2], alpha)
    ctx.move_to(lx, ly + th)
    ctx.show_text(text)
    ctx.set_line_width(1.5)
    ctx.set_source_rgba(0.7, 0.7, 0.85, 0.6 * alpha)
    ctx.set_dash([4, 4])
    ctx.move_to(lx + tw / 2, ly + th + pad)
    ctx.line_to(tx, ty)
    ctx.stroke()
    ctx.set_dash([])
    ctx.set_source_rgba(1, 1, 1, 0.8 * alpha)
    ctx.arc(tx, ty, 5, 0, 6.283)
    ctx.fill()
    ctx.set_source_rgba(col[0], col[1], col[2], alpha)
    ctx.arc(tx, ty, 3, 0, 6.283)
    ctx.fill()


def draw_title(ctx, w, h, cfg, alpha=1.0):
    fs = max(60, w // 18)
    _set_font(ctx, fs, True)
    ext = ctx.text_extents(cfg["title"])
    ctx.set_source_rgba(1, 1, 1, alpha)
    ctx.move_to((w - ext.width) / 2, 75)
    ctx.show_text(cfg["title"])
    _set_font(ctx, max(28, w // 38))
    ext = ctx.text_extents(cfg["subtitle"])
    ctx.set_source_rgba(0.71, 0.63, 0.86, alpha)
    ctx.move_to((w - ext.width) / 2, 115)
    ctx.show_text(cfg["subtitle"])
    ctx.set_source_rgba(1, 1, 1, 0.25 * alpha)
    ctx.set_line_width(2)
    uw = min(700, w // 3)
    ctx.move_to(w / 2 - uw / 2, 130)
    ctx.line_to(w / 2 + uw / 2, 130)
    ctx.stroke()


def draw_footer(ctx, w, h, sid, tot):
    ctx.set_source_rgba(0, 0, 0, 0.55)
    ctx.rectangle(0, h - 56, w, 56)
    ctx.fill()
    _set_font(ctx, max(22, w // 45))
    txt = "QUIROMANCIA TERAPÉUTICA · CONTENIDO EDUCATIVO"
    ext = ctx.text_extents(txt)
    ctx.set_source_rgb(0.47, 0.43, 0.59)
    ctx.move_to((w - ext.width) / 2, h - 22)
    ctx.show_text(txt)
    num = f"{sid}/{tot}"
    ext = ctx.text_extents(num)
    ctx.set_source_rgb(0.39, 0.35, 0.51)
    ctx.move_to(w - ext.width - 24, h - 22)
    ctx.show_text(num)


def _hand_to_screen(pt, box):
    x, y, w, h = box
    return (x + pt[0] / hg.VB * w, y + pt[1] / hg.VB * h)


def _box_for_content(cx, cy, target_h):
    """Caja (x,y,w,h) del viewBox que encuadra el CONTENIDO de la mano
    centrado en (cx,cy) con altura target_h. Corrige que la mano ocupe
    solo una franja del viewBox (por eso antes salía pequeña)."""
    x0, y0, x1, y1 = hg.content_bbox()
    ch = (y1 - y0) or 1.0
    s = target_h / ch
    bx = cx - (x0 + x1) / 2.0 * s
    by = cy - (y0 + y1) / 2.0 * s
    return (bx, by, hg.VB * s, hg.VB * s)


def draw_hand(ctx, box, side="L", alpha=1.0):
    """Draw pre-rendered solid hand PNG (filled, with lines and mounts)."""
    x, y, w, h = box
    png = _get_hand_png(side)
    if png is None:
        # Fallback to SVG if PNG missing
        svg = HAND_SVG_L if side.upper() == "L" else HAND_SVG_R
        ctx.save()
        ctx.translate(x, y)
        ctx.scale(w / hg.VB, h / hg.VB)
        ctx.set_source_rgba(1, 1, 1, alpha)
        ctx.push_group()
        svg_render.draw_svg(ctx, svg, 1.0)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(alpha)
        ctx.restore()
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(w / hg.VB, h / hg.VB)
    ctx.set_source_surface(png, 0, 0)
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def render_frame(scene, ki, nk, W, H, sid, tot, cfg, research, side="L"):
    prog = ki / max(1, nk - 1)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    # capa: background
    bg = build_space_bg(W, H)
    ctx.set_source_surface(bg, 0, 0)
    ctx.paint()

    # capa: hand (encuadrada por su contenido real; usa el ancho disponible)
    bx0, by0, bx1, by1 = hg.content_bbox()
    aspect = (bx1 - bx0) / max(1.0, (by1 - by0))
    if sid == 3:
        th = min(H * 0.80, (W * 0.44) / aspect)
        boxes = [_box_for_content(W * 0.29, H * 0.53, th),
                 _box_for_content(W * 0.71, H * 0.53, th)]
    else:
        th = min(H * 0.94, (W * 0.94) / aspect)
        boxes = [_box_for_content(W * 0.5, H * 0.52, th)]

    for i, box in enumerate(boxes):
        draw_hand(ctx, box, side=("R" if (sid == 3 and i == 1) else side))

    lines, mounts = anchors("L")
    title_a = min(1.0, prog * 4)

    if sid == 1:
        box = boxes[0]
        order = ["corazon", "cabeza", "destino", "vida"]
        for i, name in enumerate(order):
            start = 0.06 + i * 0.16
            frac = max(0.0, min(1.0, (prog - start) / 0.20))
            pts = [_hand_to_screen(p, box) for p in lines[name]]
            draw_partial(ctx, pts, frac, LCOL[name],
                         lw=13 if name == cfg["hl"] else 8,
                         dash=DASH[name], glow=True)
        ma = max(0.0, min(1.0, (prog - 0.50) / 0.2))
        if ma > 0:
            for name, (mx, my, mr) in mounts.items():
                sx, sy = _hand_to_screen((mx, my), box)
                sr = mr / hg.VB * box[2]
                c = MCOL[name]
                ctx.set_source_rgba(c[0], c[1], c[2], 0.30 * ma)
                ctx.arc(sx, sy, sr * 1.5, 0, 6.283)
                ctx.fill()
                ctx.set_source_rgba(c[0], c[1], c[2], 0.90 * ma)
                ctx.arc(sx, sy, sr, 0, 6.283)
                ctx.fill()
                ctx.set_source_rgba(1, 1, 1, 0.85 * ma)
                ctx.set_line_width(max(2.0, box[2] / 350.0))
                ctx.arc(sx, sy, sr, 0, 6.283)
                ctx.stroke()
        la = max(0.0, min(1.0, (prog - 0.68) / 0.2))
        if la > 0:
            lx = max(24.0, box[0] - 400.0)
            rx = min(W - 350.0, box[0] + box[2] + 24.0)
            _label(ctx, rx, box[1] + 40,
                   *_hand_to_screen(mounts["venus"][:2], box),
                   "Monte de Venus", 30, alpha=la)
            _label(ctx, lx, box[1] + 100,
                   *_hand_to_screen(lines["vida"][len(lines["vida"]) // 2], box),
                   "Línea de la Vida", 30, col=LCOL["vida"], alpha=la)
            _label(ctx, lx, box[1] + 190,
                   *_hand_to_screen(lines["corazon"][len(lines["corazon"]) // 2], box),
                   "Línea del Corazón", 30, col=LCOL["corazon"], alpha=la)
            _label(ctx, lx, box[1] + 280,
                   *_hand_to_screen(lines["cabeza"][len(lines["cabeza"]) // 2], box),
                   "Línea de la Cabeza", 30, col=LCOL["cabeza"], alpha=la)
            _label(ctx, rx, box[1] + 130,
                   *_hand_to_screen(mounts["jupiter"][:2], box),
                   "Monte de Júpiter", 30, alpha=la)
            _label(ctx, rx, box[1] + 220,
                   *_hand_to_screen(mounts["saturno"][:2], box),
                   "Monte de Saturno", 30, alpha=la)

    elif sid == 2:
        box = boxes[0]
        pts = [_hand_to_screen(p, box) for p in lines["vida"]]
        draw_partial(ctx, pts, min(1.0, prog * 2.5), LCOL["vida"],
                     lw=10, dash=DASH["vida"], glow=True)
        p_fracs = [0.02, 0.10, 0.18]
        cols = [(0, 0.86, 1), (1, 0.39, 0.39), (0.39, 1, 0.39)]
        labels = ["1. Acción directa", "2. Energía mixta", "3. Intuición"]
        for i, (pf, c, lb) in enumerate(zip(p_fracs, cols, labels)):
            a = max(0.0, min(1.0, (prog - (0.25 + i * 0.20)) / 0.15))
            if a <= 0:
                continue
            px, py = pts[int(len(pts) * pf)]
            draw_pulsing_point(ctx, px, py, c, phase=(prog * 3) % 1.0)
            _label(ctx, box[0] + box[2] + 40, box[1] + 20 + i * 55,
                   px + 18, py, lb, 26, alpha=a)

    elif sid == 3:
        for i, box in enumerate(boxes):
            frac = max(0.0, min(1.0, (prog - 0.10) / 0.45))
            base_pts = [list(p) for p in hg.anchors()[0]["vida"]]
            # Offset the line to create two different curves
            if i == 0:
                for j in range(len(base_pts)):
                    if 1 <= j <= 2:
                        base_pts[j][0] -= 45
                    elif 3 <= j <= 4:
                        base_pts[j][0] -= 40
            else:
                for j in range(len(base_pts)):
                    if 1 <= j <= 2:
                        base_pts[j][0] += 45
                    elif 3 <= j <= 4:
                        base_pts[j][0] += 30
            pts = [_hand_to_screen(p, box) for p in base_pts]
            draw_partial(ctx, pts, frac, LCOL["vida"], lw=10,
                         dash=DASH["vida"], glow=True)
            ttl = "CURVA AMPLIA" if i == 0 else "ARCO ESTRECHO"
            _set_font(ctx, 34, True)
            ext = ctx.text_extents(ttl)
            ctx.set_source_rgba(1, 1, 1, title_a)
            ctx.move_to(box[0] + box[2] / 2 - ext.width / 2, box[1] - 18)
            ctx.show_text(ttl)
        _set_font(ctx, 34, True)
        ext = ctx.text_extents("vs")
        ctx.set_source_rgb(0.47, 0.47, 0.63)
        ctx.move_to(W / 2 - ext.width / 2, int(H * 0.55))
        ctx.show_text("vs")

    elif sid == 4:
        box = boxes[0]
        pts = [_hand_to_screen(p, box) for p in lines["vida"]]
        third = len(pts) // 3
        draw_partial(ctx, pts[:third], max(0.0, min(1.0, prog / 0.35)),
                     LCOL["vida"], lw=12, glow=True)
        if prog > 0.35:
            draw_partial(ctx, pts[third:2 * third],
                         min(1.0, (prog - 0.35) / 0.25),
                         (0.78, 0.20, 0.31), lw=5, dash=[8, 4])
        la = max(0.0, min(1.0, (prog - 0.5) / 0.25))
        if la > 0:
            _label(ctx, box[0] + box[2] + 40, box[1] + 40,
                   *pts[third // 2], "PROFUNDA", 28, (1, 0.39, 0.51), alpha=la)
            _label(ctx, box[0] + box[2] + 40, box[1] + 120,
                   *pts[third + third // 2], "MEDIA", 28, (0.78, 0.71, 0.63), alpha=la)

    draw_title(ctx, W, H, cfg, alpha=title_a)
    draw_footer(ctx, W, H, sid, tot)

    # Las fotos de concepto (Openverse) quedan fuera del motor editorial V8:
    # el diseno exige imagenes solo para fondos/historia/mitologia, no
    # pegadas sobre la mano. research se conserva como metadata.
    return surf


def _surface_to_rgb(surf, W, H):
    data = bytes(surf.get_data())
    im = Image.frombuffer("RGBA", (W, H), data, "raw", "BGRA", surf.get_stride(), 1)
    return im.convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--storyboard", default=str(SCRIPT_DIR / "data" / "jobs" / "default" / "storyboard.json"))
    ap.add_argument("--research", default=None)
    ap.add_argument("--output-dir", default=str(SCRIPT_DIR / "data" / "images"))
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--frames", type=int, default=7)
    ap.add_argument("--profile", default="cosmic_educational_v1")
    ap.add_argument("--side", default="L", choices=["L", "R"])
    a = ap.parse_args()

    load_visual_profile(a.profile)
    sb = json.loads(Path(a.storyboard).read_text(encoding="utf-8"))
    jid = Path(a.storyboard).parent.name
    research = {}
    if a.research and Path(a.research).exists():
        research = json.loads(Path(a.research).read_text(encoding="utf-8"))

    out = Path(a.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    scenes = sb.get("scenes", [])
    tot = len(scenes)
    meta = {"scenes": [], "model": "vector-v8", "width": a.width, "height": a.height}

    for sc in scenes:
        sid = sc.get("id", 1)
        cfg = SCFG.get(sid, SCFG[1])
        scene_dir = out / f"scene_{sid:03d}"
        scene_dir.mkdir(parents=True, exist_ok=True)
        frames = []
        for ki in range(a.frames):
            fp = scene_dir / f"f_{ki:03d}.png"
            surf = render_frame(sc, ki, a.frames, a.width, a.height,
                                sid, tot, cfg, research, side=a.side)
            im = _surface_to_rgb(surf, a.width, a.height)
            im.save(fp, "PNG", optimize=False)
            frames.append(str(fp.name))
        meta["scenes"].append({
            "scene_id": sid, "frames": frames, "dir": str(scene_dir),
            "width": a.width, "height": a.height,
            "created_at": datetime.now().isoformat(),
        })
        print(f"Escena {sid}: {a.frames} keyframes")

    job_images = SCRIPT_DIR / "data" / "jobs" / jid / "images.json"
    job_images.parent.mkdir(parents=True, exist_ok=True)
    job_images.write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                          encoding="utf-8")
    print(json.dumps({"scenes": tot, "keyframes_per_scene": a.frames,
                      "dir": str(out)}))


if __name__ == "__main__":
    main()