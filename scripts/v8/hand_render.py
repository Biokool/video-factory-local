"""
Render hand geometry as solid PNG using Cairo directly.

Renders the segmented hand SVG as a FILLED shape with smooth skin gradient,
border, and optional palm lines — producing a proper cartoon hand image.

Output: assets/v8/hands/mano_<side>_solid.png (2048×2048, RGBA)
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import cairo
import hand_geometry as hg
import svg_sanitizer

OUT_DIR = HERE.parent.parent / "assets" / "v8" / "hands"


def _draw_svg_path(ctx, d):
    """Parse minimal SVG path d-attribute and draw with Cairo."""
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


def render_hand_png(side="L", size=2048, output_path=None):
    """Render a single hand as a solid filled PNG at 2048×2048."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surf)

    # Transparent background
    ctx.set_operator(cairo.OPERATOR_CLEAR)
    ctx.paint()
    ctx.set_operator(cairo.OPERATOR_OVER)

    # Scale from 2048 viewBox to target size
    scale = size / hg.VB
    ctx.scale(scale, scale)

    # Get the hand SVG and sanitize it
    svg_str = hg.hand_svg(side)
    svg_clean, threats = svg_sanitizer.sanitize_svg(svg_str)
    if threats:
        print(f"  Sanitizer removed {len(threats)} threats from hand SVG")

    # Draw each finger path from the segmented SVG
    # Extract path d-attributes from the sanitized SVG
    path_pattern = re.compile(r'<path\s+id="([^"]+)"\s+d="([^"]+)"', re.DOTALL)
    for match in path_pattern.finditer(svg_clean):
        path_id = match.group(1)
        d = match.group(2)

        if path_id in ("palm-silhouette", "thumb", "index-finger",
                        "middle-finger", "ring-finger", "little-finger", "wrist"):
            _draw_svg_path(ctx, d)

            # Fill with skin gradient for palm and fingers
            if path_id != "wrist":
                grad = cairo.RadialGradient(
                    hg.PALM_CX, hg.PALM_CY - 50, 50,
                    hg.PALM_CX, hg.PALM_CY, hg.PALM_W)
                grad.add_color_stop_rgba(0, 0.98, 0.87, 0.79, 1.0)
                grad.add_color_stop_rgba(1, 0.91, 0.72, 0.54, 1.0)
                ctx.set_source(grad)
                ctx.fill_preserve()

                # Border
                ctx.set_source_rgba(0.83, 0.65, 0.46, 1.0)
                ctx.set_line_width(3.5)
                ctx.set_line_join(cairo.LINE_JOIN_ROUND)
                ctx.set_line_cap(cairo.LINE_CAP_ROUND)
                ctx.stroke()
            else:
                # Wrist: simpler fill
                ctx.set_source_rgba(0.91, 0.72, 0.54, 1.0)
                ctx.fill_preserve()
                ctx.set_source_rgba(0.83, 0.65, 0.46, 1.0)
                ctx.set_line_width(3.5)
                ctx.stroke()

    # Palm lines (thick, colored, dashed)
    lines_data = hg.anchors()[0]
    _draw_line(ctx, lines_data.get("vida", []), (0.00, 0.83, 0.92), 9, [16, 8])
    _draw_line(ctx, lines_data.get("corazon", []), (1.00, 0.42, 0.61), 9, [16, 8])
    _draw_line(ctx, lines_data.get("cabeza", []), (1.00, 0.65, 0.00), 9, [16, 8])
    _draw_line(ctx, lines_data.get("destino", []), (1.00, 0.85, 0.24), 8, [14, 8])

    # Mount circles
    _, mounts = hg.anchors()
    mount_colors = {
        "jupiter":  (1.0, 0.42, 0.42),
        "saturno":  (1.0, 0.85, 0.24),
        "sol":      (0.42, 0.79, 0.47),
        "mercurio": (0.30, 0.59, 1.0),
        "venus":    (1.0, 1.0, 1.0),
    }
    for name, (mx, my, mr) in mounts.items():
        c = mount_colors.get(name, (1, 1, 1))
        ctx.set_source_rgba(c[0], c[1], c[2], 0.3)
        ctx.arc(mx, my, mr * 1.6, 0, 6.283)
        ctx.fill()
        ctx.set_source_rgba(c[0], c[1], c[2], 0.9)
        ctx.arc(mx, my, mr, 0, 6.283)
        ctx.fill()
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


def emit_both():
    """Render L and R hands."""
    lpath = render_hand_png("L")
    rpath = render_hand_png("R")
    print(f"L: {lpath}")
    print(f"R: {rpath}")
    return lpath, rpath


if __name__ == "__main__":
    emit_both()
