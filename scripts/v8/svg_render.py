"""svg_render.py - Renderizador SVG minimo a Cairo (V8).

Sin cairosvg. Tokeniza un subconjunto controlado de SVG (M/L/H/V/C/S/Z,
absolutos y relativos) y dibuja con pycairo. Tambien rasteriza a mascara
binaria con numpy para QA.

Expone:
  parse_path(d)                    -> comandos normalizados
  parse_svg(text)                  -> elementos {d, fill, stroke, ...}
  draw_svg(ctx, text, scale)       -> dibuja sobre cairo.Context
  render_svg_to_mask(text, w, h)   -> numpy uint8 (255 = dentro)
  render_svg_to_rgba(text, w, h)   -> (numpy HxWx4, (w,h))
"""
from __future__ import annotations

import re

_NUM = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
_CMD = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]")


def _floats(s):
    return [float(x) for x in _NUM.findall(s)]


def _hex_color(value, default=(0.0, 0.0, 0.0, 1.0)):
    if not value:
        return default
    v = value.strip()
    if v == "none":
        return (0.0, 0.0, 0.0, 0.0)
    if v.startswith("#"):
        h = v[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) >= 6:
            r = int(h[0:2], 16) / 255.0
            g = int(h[2:4], 16) / 255.0
            b = int(h[4:6], 16) / 255.0
            a = int(h[6:8], 16) / 255.0 if len(h) >= 8 else 1.0
            return (r, g, b, a)
    return default


def _tokenize(d):
    tokens = []
    i, n = 0, len(d)
    while i < n:
        ch = d[i]
        if ch in " ,\t\n\r":
            i += 1
            continue
        m = _CMD.match(ch)
        if not m:
            break
        cmd = ch
        i += 1
        j = i
        while j < n and not _CMD.match(d[j]):
            j += 1
        tokens.append((cmd, _floats(d[i:j])))
        i = j
    return tokens


def parse_path(d):
    """Normaliza `d` a comandos absolutos (M/L/C/Z)."""
    out = []
    cx = cy = sx = sy = 0.0
    prev_c = None
    for cmd, nums in _tokenize(d):
        rel = cmd.islower()
        C = cmd.upper()
        if C == "M":
            for k in range(0, len(nums) - 1, 2):
                x, y = nums[k], nums[k + 1]
                if rel:
                    x += cx
                    y += cy
                cx, cy = x, y
                if k == 0:
                    out.append(("M", x, y))
                    sx, sy = x, y
                else:
                    out.append(("L", x, y))
            prev_c = None
        elif C == "L":
            for k in range(0, len(nums) - 1, 2):
                x, y = nums[k], nums[k + 1]
                if rel:
                    x += cx
                    y += cy
                out.append(("L", x, y))
                cx, cy = x, y
            prev_c = None
        elif C == "H":
            for v in nums:
                x = v + cx if rel else v
                out.append(("L", x, cy))
                cx = x
            prev_c = None
        elif C == "V":
            for v in nums:
                y = v + cy if rel else v
                out.append(("L", cx, y))
                cy = y
            prev_c = None
        elif C in ("C", "S"):
            step = 6 if C == "C" else 4
            for k in range(0, len(nums) - step + 1, step):
                if C == "C":
                    x1, y1, x2, y2, x, y = nums[k:k + 6]
                else:
                    x2, y2, x, y = nums[k:k + 4]
                    if prev_c is not None:
                        x1 = 2 * cx - prev_c[0]
                        y1 = 2 * cy - prev_c[1]
                    else:
                        x1, y1 = cx, cy
                if rel:
                    x1 += cx
                    y1 += cy
                    x2 += cx
                    y2 += cy
                    x += cx
                    y += cy
                out.append(("C", x1, y1, x2, y2, x, y))
                cx, cy = x, y
                prev_c = (x2, y2)
        elif C == "Z":
            out.append(("Z",))
            cx, cy = sx, sy
            prev_c = None
    return out


_TAG = re.compile(r"<(path|circle|ellipse|rect|polygon|polyline)\b([^>]*?)/?>", re.I)
_ATTR = re.compile(r'([\w:-]+)\s*=\s*"([^"]*)"')
_K = 0.5522847498


def _ellipse_path(cx, cy, rx, ry):
    return (
        f"M{cx - rx} {cy} "
        f"C{cx - rx} {cy - ry * _K} {cx - rx * _K} {cy - ry} {cx} {cy - ry} "
        f"C{cx + rx * _K} {cy - ry} {cx + rx} {cy - ry * _K} {cx + rx} {cy} "
        f"C{cx + rx} {cy + ry * _K} {cx + rx * _K} {cy + ry} {cx} {cy + ry} "
        f"C{cx - rx * _K} {cy + ry} {cx - rx} {cy + ry * _K} {cx - rx} {cy} Z"
    )


def parse_svg(text):
    """Extrae elementos dibujables. Agrupa por <g> heredando estilos."""
    elements = []
    stack = [{}]
    pos = 0
    tag_re = re.compile(r"<(/?)(path|circle|ellipse|rect|polygon|polyline|g)\b([^>]*?)(/?)>", re.I)
    for m in tag_re.finditer(text):
        closing, tag, attrs_s, selfclose = m.group(1), m.group(2).lower(), m.group(3), m.group(4)
        a = {k: v for k, v in _ATTR.findall(attrs_s)}
        if tag == "g":
            if closing:
                if len(stack) > 1:
                    stack.pop()
            else:
                inherited = dict(stack[-1])
                for key in ("fill", "stroke", "stroke-width", "opacity"):
                    if key in a:
                        inherited[key] = a[key]
                stack.append(inherited)
            continue
        style = dict(stack[-1])
        style.update(a)
        el = {
            "fill": _hex_color(style.get("fill", "none"), (0.0, 0.0, 0.0, 0.0)),
            "stroke": _hex_color(style.get("stroke", "none"), (0.0, 0.0, 0.0, 0.0)),
            "stroke_width": float(style.get("stroke-width", 1.0) or 1.0),
            "opacity": float(style.get("opacity", 1.0) or 1.0),
        }
        if tag == "path":
            el["d"] = style.get("d", "")
        elif tag == "circle":
            r = float(style.get("r", 0) or 0)
            el["d"] = _ellipse_path(float(style.get("cx", 0) or 0),
                                    float(style.get("cy", 0) or 0), r, r)
        elif tag == "ellipse":
            el["d"] = _ellipse_path(float(style.get("cx", 0) or 0),
                                    float(style.get("cy", 0) or 0),
                                    float(style.get("rx", 0) or 0),
                                    float(style.get("ry", 0) or 0))
        elif tag == "rect":
            x = float(style.get("x", 0) or 0)
            y = float(style.get("y", 0) or 0)
            w = float(style.get("width", 0) or 0)
            h = float(style.get("height", 0) or 0)
            el["d"] = f"M{x} {y} L{x + w} {y} L{x + w} {y + h} L{x} {y + h} Z"
        else:
            pts = _floats(style.get("points", ""))
            if len(pts) < 4:
                continue
            d = f"M{pts[0]} {pts[1]}"
            for k in range(2, len(pts) - 1, 2):
                d += f" L{pts[k]} {pts[k + 1]}"
            if tag == "polygon":
                d += " Z"
            el["d"] = d
        if el["d"]:
            elements.append(el)
    return elements


def viewbox_of(text):
    m = re.search(r'viewBox\s*=\s*"([^"]+)"', text)
    if not m:
        return None
    return _floats(m.group(1))


def _trace(ctx, cmds):
    started = False
    for c in cmds:
        if c[0] == "M":
            if started:
                ctx.new_sub_path()
            ctx.move_to(c[1], c[2])
            started = True
        elif c[0] == "L":
            ctx.line_to(c[1], c[2])
        elif c[0] == "C":
            ctx.curve_to(c[1], c[2], c[3], c[4], c[5], c[6])
        elif c[0] == "Z":
            ctx.close_path()


def draw_svg(ctx, text, scale=1.0):
    """Dibuja el SVG sobre un contexto Cairo. Devuelve n elementos."""
    ctx.save()
    ctx.scale(scale, scale)
    n = 0
    for el in parse_svg(text):
        cmds = parse_path(el["d"])
        if not cmds:
            continue
        ctx.new_path()
        _trace(ctx, cmds)
        ctx.set_line_width(el["stroke_width"])
        ctx.set_line_join(1)
        ctx.set_line_cap(1)
        if el["fill"][3] > 0:
            r, g, b, a = el["fill"]
            ctx.set_source_rgba(r, g, b, a * el["opacity"])
            ctx.fill_preserve()
        if el["stroke"][3] > 0:
            r, g, b, a = el["stroke"]
            ctx.set_source_rgba(r, g, b, a * el["opacity"])
            ctx.stroke()
        else:
            ctx.new_path()
        n += 1
    ctx.restore()
    return n


def render_svg_to_rgba(text, out_w, out_h, fill_bg=None):
    """Rasteriza a numpy RGBA (HxWx4) y devuelve tambien el tamano escalado."""
    import numpy as np
    import cairo

    vb = viewbox_of(text)
    if vb and len(vb) == 4:
        sx = out_w / vb[2]
        sy = out_h / vb[3]
        scale = min(sx, sy)
        vw, vh = vb[2], vb[3]
    else:
        vw = out_w
        vh = out_h
        scale = 1.0
    rw, rh = int(vw * scale), int(vh * scale)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, rw, rh)
    ctx = cairo.Context(surf)
    if fill_bg is not None:
        ctx.set_source_rgba(*fill_bg)
        ctx.paint()
    draw_svg(ctx, text, scale)
    surf.flush()
    buf = surf.get_data()
    arr = np.frombuffer(buf, dtype=np.uint8).reshape(rh, surf.get_stride() // 4, 4)
    arr = arr[:, :rw, :].copy()
    # Cairo ARGB32 little-endian = BGRA en memoria
    arr = arr[:, :, [2, 1, 0, 3]]
    return arr, (rw, rh)


def render_svg_to_mask(text, out_w, out_h, threshold=16):
    """Mascara binaria uint8 (255 = dentro) a partir del alfa."""
    arr, (rw, rh) = render_svg_to_rgba(text, out_w, out_h)
    alpha = arr[:, :, 3]
    return (alpha > threshold).astype("uint8") * 255, (rw, rh)


def main():
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("svg")
    ap.add_argument("--out", default=None)
    ap.add_argument("--w", type=int, default=1024)
    ap.add_argument("--h", type=int, default=1024)
    a = ap.parse_args()
    text = open(a.svg, encoding="utf-8").read()
    mask, (rw, rh) = render_svg_to_mask(text, a.w, a.h)
    info = {"size": [rw, rh], "filled_px": int((mask > 0).sum())}
    if a.out:
        import numpy as np
        rgba, _ = render_svg_to_rgba(text, a.w, a.h, fill_bg=(0, 0, 0, 0))
        from PIL import Image
        Image.fromarray(rgba, "RGBA").save(a.out)
        info["out"] = a.out
    print(json.dumps(info))


if __name__ == "__main__":
    main()
