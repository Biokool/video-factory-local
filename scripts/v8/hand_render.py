"""
Render hand geometry as solid PNG using Cairo directly.

The SVG renderer only draws strokes (no fill). This module renders
the hand outline as a FILLED shape with smooth skin gradient, border,
and optional palm lines — producing a proper cartoon hand image.

Output: assets/v8/hands/mano_<side>_solid.png (1024×1024, RGBA)
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import cairo
import hand_geometry as hg

OUT_DIR = HERE.parent.parent / "assets" / "v8" / "hands"


def render_hand_png(side="L", size=1024, output_path=None):
    """Render a single hand as a solid filled PNG."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surf)

    # Transparent background
    ctx.set_operator(cairo.OPERATOR_CLEAR)
    ctx.paint()
    ctx.set_operator(cairo.OPERATOR_OVER)

    # Get outline points and build smooth path
    outline = hg.build_hand_outline()
    d = hg.smooth_path(outline, closed=True)

    # Parse the SVG path d-attribute and draw it with Cairo
    _draw_svg_path(ctx, d)

    # Fill with skin gradient
    palm_cx = hg.PALM_CX
    palm_cy = hg.PALM_CY
    grad = cairo.RadialGradient(palm_cx, palm_cy - 50, 50, palm_cx, palm_cy, hg.PALM_W)
    grad.add_color_stop_rgba(0, 0.98, 0.87, 0.79, 1.0)   # #FADEC9
    grad.add_color_stop_rgba(1, 0.91, 0.72, 0.54, 1.0)   # #E8B88A
    ctx.set_source(grad)
    ctx.fill_preserve()

    # Border
    ctx.set_source_rgba(0.83, 0.65, 0.46, 1.0)  # #D4A574
    ctx.set_line_width(3.5)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()

    # Palm lines (thick, colored, dashed)
    lines_data = hg.anchors()[0]
    _draw_line(ctx, lines_data.get("vida", []), (0.00, 0.83, 0.92), 9, [16, 8])     # cyan
    _draw_line(ctx, lines_data.get("corazon", []), (1.00, 0.42, 0.61), 9, [16, 8])  # pink
    _draw_line(ctx, lines_data.get("cabeza", []), (1.00, 0.65, 0.00), 9, [16, 8])   # orange
    _draw_line(ctx, lines_data.get("destino", []), (1.00, 0.85, 0.24), 8, [14, 8])  # yellow

    # Mount circles
    _, mounts = hg.anchors()
    for name, (mx, my, mr) in mounts.items():
        colors = {
            "jupiter":  (1.0, 0.42, 0.42),   # red
            "saturno":  (1.0, 0.85, 0.24),   # yellow
            "sol":      (0.42, 0.79, 0.47),  # green
            "mercurio": (0.30, 0.59, 1.0),   # blue
            "venus":    (1.0, 1.0, 1.0),     # white
        }
        c = colors.get(name, (1, 1, 1))
        # Halo
        ctx.set_source_rgba(c[0], c[1], c[2], 0.3)
        ctx.arc(mx, my, mr * 1.6, 0, 6.283)
        ctx.fill()
        # Solid circle
        ctx.set_source_rgba(c[0], c[1], c[2], 0.9)
        ctx.arc(mx, my, mr, 0, 6.283)
        ctx.fill()
        # White border
        ctx.set_source_rgba(1, 1, 1, 0.8)
        ctx.set_line_width(2.5)
        ctx.arc(mx, my, mr, 0, 6.283)
        ctx.stroke()

    # Save
    if output_path is None:
        suffix = "izquierda" if side.upper() == "L" else "derecha"
        output_path = OUT_DIR / f"mano_{suffix}_solid.png"
    else:
        output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    surf.write_to_png(str(output_path))
    return output_path


def _draw_svg_path(ctx, d):
    """Parse minimal SVG path d-attribute and draw with Cairo."""
    import re
    # Tokenize: split into commands and numbers
    parts = re.findall(r'[MLCSZmlcsz]|[-+]?(?:\d+\.?\d*|\.\d+)', d)
    i = 0
    cx, cy = 0, 0
    while i < len(parts):
        tok = parts[i]
        if tok in ('M', 'm'):
            i += 1
            x = float(parts[i]); i += 1
            y = float(parts[i]); i += 1
            if tok == 'm':
                x += cx; y += cy
            ctx.move_to(x, y)
            cx, cy = x, y
        elif tok in ('L', 'l'):
            i += 1
            x = float(parts[i]); i += 1
            y = float(parts[i]); i += 1
            if tok == 'l':
                x += cx; y += cy
            ctx.line_to(x, y)
            cx, cy = x, y
        elif tok in ('C', 'c'):
            i += 1
            x1 = float(parts[i]); i += 1
            y1 = float(parts[i]); i += 1
            x2 = float(parts[i]); i += 1
            y2 = float(parts[i]); i += 1
            x = float(parts[i]); i += 1
            y = float(parts[i]); i += 1
            if tok == 'c':
                x1 += cx; y1 += cy
                x2 += cx; y2 += cy
                x += cx; y += cy
            ctx.curve_to(x1, y1, x2, y2, x, y)
            cx, cy = x, y
        elif tok in ('Z', 'z'):
            ctx.close_path()
            i += 1
        else:
            i += 1


def _draw_line(ctx, points, color, width=8, dash=None):
    """Draw a smooth line through points."""
    if len(points) < 2:
        return
    ctx.set_source_rgba(color[0], color[1], color[2], 0.9)
    ctx.set_line_width(width)
    if dash:
        ctx.set_dash(dash)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.move_to(points[0][0], points[0][1])
    for i in range(1, len(points)):
        ctx.line_to(points[i][0], points[i][1])
    ctx.stroke()
    ctx.set_dash([])


def emit_both():
    """Render L and R hands."""
    lpath = render_hand_png("L")
    rpath = render_hand_png("R")
    print(f"L: {lpath}")
    print(f"R: {rpath}")
    return lpath, rpath


if __name__ == "__main__":
    emit_both()
