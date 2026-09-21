"""
Hand geometry V10 — segmented SVG per spec §8.1.

Each hand produces a 2048×2048 SVG with:
  <g id="hand-base">
    <path id="palm-silhouette"/>
    <path id="thumb"/>
    <path id="index-finger"/>
    <path id="middle-finger"/>
    <path id="ring-finger"/>
    <path id="little-finger"/>
    <path id="wrist"/>
  </g>
  <g id="natural-creases"/>
  <g id="shading"/>

No mounts, no palm lines, no text inside hand SVG.
Lines and mounts are separate SVG assets from svg_library.
"""
import argparse, json, math, sys
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "v8" / "hands"

# ── ViewBox 2048×2048 per §8.1 ────────────────────────────────────
VB = 2048

# Scale factor from old 1024 geometry to 2048
_S = 2.0

# Palm geometry (scaled to 2048 space)
PALM_CX, PALM_CY = int(512 * _S), int(590 * _S)   # 1024, 1180
PALM_W, PALM_H = int(380 * _S), int(300 * _S)     # 760, 600

FINGER_BASE_Y = PALM_CY - PALM_H // 2  # 880

# Finger dimensions (scaled)
FINGERS = {
    "index-finger":   {"x_off": int(-105 * _S), "len": int(250 * _S), "base_w": int(54 * _S), "tip_w": int(36 * _S)},
    "middle-finger":  {"x_off": int(-30 * _S),  "len": int(280 * _S), "base_w": int(54 * _S), "tip_w": int(36 * _S)},
    "ring-finger":    {"x_off": int(45 * _S),   "len": int(245 * _S), "base_w": int(50 * _S), "tip_w": int(34 * _S)},
    "little-finger":  {"x_off": int(115 * _S),  "len": int(195 * _S), "base_w": int(44 * _S), "tip_w": int(30 * _S)},
}
THUMB = {"x_off": int(-220 * _S), "y_off": int(110 * _S), "len": int(210 * _S),
         "base_w": int(56 * _S), "tip_w": int(38 * _S), "angle_deg": -35}

WRIST_W = int(160 * _S)
WRIST_BOTTOM = PALM_CY + PALM_H // 2 + int(80 * _S)  # 1560

# Safe margin 8% per §8.2
SAFE_MARGIN = int(VB * 0.08)  # 163

# ── Coordinate helpers ──────────────────────────────────────────────

def _finger_tip_cx(fi):
    return PALM_CX + fi["x_off"]

def _finger_tip_cy(fi):
    return FINGER_BASE_Y - fi["len"]

def _finger_left(fi, y=None):
    if y is None:
        y = FINGER_BASE_Y
    t = (FINGER_BASE_Y - y) / fi["len"] if fi["len"] else 0
    half_w = (fi["base_w"] / 2) * (1 - t) + (fi["tip_w"] / 2) * t
    return PALM_CX + fi["x_off"] - half_w

def _finger_right(fi, y=None):
    if y is None:
        y = FINGER_BASE_Y
    t = (FINGER_BASE_Y - y) / fi["len"] if fi["len"] else 0
    half_w = (fi["base_w"] / 2) * (1 - t) + (fi["tip_w"] / 2) * t
    return PALM_CX + fi["x_off"] + half_w


# ── Bezier smoothing ────────────────────────────────────────────────

def catmull_rom_to_bezier(p0, p1, p2, p3, tension=0.4):
    d1 = (p2[0] - p0[0], p2[1] - p0[1])
    d2 = (p3[0] - p1[0], p3[1] - p1[1])
    cp1 = (p1[0] + d1[0] * tension, p1[1] + d1[1] * tension)
    cp2 = (p2[0] - d2[0] * tension, p2[1] - d2[1] * tension)
    return cp1, cp2


def smooth_path(keypoints, closed=True):
    n = len(keypoints)
    pts = list(keypoints)
    if closed:
        pts = [pts[-1]] + pts + [pts[0], pts[1]]
    else:
        pts = [pts[0]] + pts + [pts[-1]]

    segments = []
    for i in range(1, len(pts) - 2):
        cp1, cp2 = catmull_rom_to_bezier(pts[i - 1], pts[i], pts[i + 1], pts[i + 2])
        if i == 1:
            segments.append(f"M{pts[i][0]:.1f},{pts[i][1]:.1f}")
        segments.append(f"C{cp1[0]:.1f},{cp1[1]:.1f} {cp2[0]:.1f},{cp2[1]:.1f} {pts[i+1][0]:.1f},{pts[i+1][1]:.1f}")

    if closed:
        segments.append("Z")
    return "".join(segments)


# ── Segmented finger paths ─────────────────────────────────────────

def _build_finger_path(fi):
    """Build a single closed finger path: left side up → tip → right side down → base close."""
    tip_cy = _finger_tip_cy(fi)
    tip_cx = _finger_tip_cx(fi)
    tl = _finger_left(fi, tip_cy)
    tr = _finger_right(fi, tip_cy)
    bl = _finger_left(fi, FINGER_BASE_Y)
    br = _finger_right(fi, FINGER_BASE_Y)

    pts = [
        (bl, FINGER_BASE_Y + 5),
        (bl + 3 * _S, FINGER_BASE_Y - 10 * _S),
        (tl + 2 * _S, tip_cy + 60 * _S),
        (tl + 1 * _S, tip_cy + 30 * _S),
        (tl + 3 * _S, tip_cy + 8 * _S),
        (tip_cx, tip_cy - 4 * _S),
        (tr - 3 * _S, tip_cy + 8 * _S),
        (tr - 1 * _S, tip_cy + 30 * _S),
        (tr - 3 * _S, tip_cy + 60 * _S),
        (br - 3 * _S, FINGER_BASE_Y - 10 * _S),
        (br, FINGER_BASE_Y + 5),
    ]
    return smooth_path(pts, closed=True)


def _build_thumb_path():
    """Build thumb as separate closed path."""
    th_cx = PALM_CX + THUMB["x_off"]
    th_cy = PALM_CY + THUMB["y_off"]
    th_len = THUMB["len"]
    th_angle = math.radians(THUMB["angle_deg"])
    th_basew = THUMB["base_w"] / 2
    th_tipw = THUMB["tip_w"] / 2

    th_tip_x = th_cx + th_len * math.sin(th_angle)
    th_tip_y = th_cy - th_len * math.cos(th_angle)

    pts = [
        (th_cx + th_basew + 5 * _S, th_cy - 30 * _S),
        (th_cx + th_basew, th_cy),
        (th_cx + th_tipw + 10 * _S, th_tip_y + 40 * _S),
        (th_cx + th_tipw + 3 * _S, th_tip_y + 10 * _S),
        (th_tip_x, th_tip_y - 5 * _S),
        (th_cx - th_tipw - 3 * _S, th_tip_y + 10 * _S),
        (th_cx - th_tipw - 10 * _S, th_tip_y + 40 * _S),
        (th_cx - th_basew, th_cy),
        (th_cx - th_basew - 5 * _S, th_cy - 40 * _S),
    ]
    return smooth_path(pts, closed=True)


def _build_palm_silhouette():
    """Build palm outline without fingers (just the palm body + connections to finger bases)."""
    palm_lx = PALM_CX - PALM_W // 2
    palm_rx = PALM_CX + PALM_W // 2
    palm_top = FINGER_BASE_Y
    palm_bot = PALM_CY + PALM_H // 2

    # Palm contour: wrist left → palm left → between finger bases → palm right → wrist right
    pts = [
        (PALM_CX - WRIST_W // 2, WRIST_BOTTOM),
        (PALM_CX - WRIST_W // 2, palm_bot - 20 * _S),
        (palm_lx + 10 * _S, palm_bot),
        (palm_lx, palm_bot - 60 * _S),
        (palm_lx - 5 * _S, PALM_CY),
        (palm_lx + 5 * _S, palm_top + 40 * _S),
        (palm_lx + 20 * _S, palm_top + 10 * _S),
        # across finger bases (simplified — fingers are separate paths)
        (palm_rx - 20 * _S, palm_top + 10 * _S),
        (palm_rx - 5 * _S, palm_top + 40 * _S),
        (palm_rx, PALM_CY + 20 * _S),
        (palm_rx - 5 * _S, palm_bot - 30 * _S),
        (palm_rx - 15 * _S, palm_bot + 10 * _S),
        (PALM_CX + WRIST_W // 2, palm_bot - 20 * _S),
        (PALM_CX + WRIST_W // 2, WRIST_BOTTOM),
    ]
    return smooth_path(pts, closed=True)


def _build_wrist_path():
    """Build wrist as separate path connecting palm bottom to arm."""
    wrist_lx = PALM_CX - WRIST_W // 2
    wrist_rx = PALM_CX + WRIST_W // 2
    palm_bot = PALM_CY + PALM_H // 2

    pts = [
        (wrist_lx, WRIST_BOTTOM),
        (wrist_lx, WRIST_BOTTOM + 40 * _S),
        (wrist_lx + 20 * _S, WRIST_BOTTOM + 80 * _S),
        (wrist_rx - 20 * _S, WRIST_BOTTOM + 80 * _S),
        (wrist_rx, WRIST_BOTTOM + 40 * _S),
        (wrist_rx, WRIST_BOTTOM),
    ]
    return smooth_path(pts, closed=True)


# ── SVG generation ──────────────────────────────────────────────────

def hand_svg(side="L"):
    """Return segmented SVG string per spec §8.1."""
    asset_id = f"HAND_{side}_PALM_FRONT_V001"
    palm_d = _build_palm_silhouette()
    thumb_d = _build_thumb_path()
    finger_paths = {}
    for fname, fi in FINGERS.items():
        finger_paths[fname] = _build_finger_path(fi)
    wrist_d = _build_wrist_path()

    finger_elements = ""
    for fname in ["index-finger", "middle-finger", "ring-finger", "little-finger"]:
        finger_elements += f'    <path id="{fname}" d="{finger_paths[fname]}" fill="#F5CBA7" stroke="#D4A574" stroke-width="3" stroke-linejoin="round"/>\n'

    mirror = ""
    if side.upper() == "R":
        mirror = ' transform="translate(2048,0) scale(-1,1)"'

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg id="{asset_id}" xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 {VB} {VB}" width="{VB}" height="{VB}">

  <g id="hand-base"{mirror}>
    <path id="palm-silhouette" d="{palm_d}"
          fill="#F5CBA7" stroke="#D4A574" stroke-width="3" stroke-linejoin="round"/>
    <path id="thumb" d="{thumb_d}"
          fill="#F5CBA7" stroke="#D4A574" stroke-width="3" stroke-linejoin="round"/>
{finger_elements}    <path id="wrist" d="{wrist_d}"
          fill="#E8B88A" stroke="#D4A574" stroke-width="3" stroke-linejoin="round"/>
  </g>

  <g id="natural-creases">
    <!-- Creases will be added from reference images -->
  </g>

  <g id="shading">
    <!-- Subtle shading for depth — added by compositor -->
  </g>

</svg>'''
    return svg


def content_bbox():
    """Return (x0, y0, x1, y1) bounding box of hand content."""
    ys = [_finger_tip_cy(fi) for fi in FINGERS.values()]
    xs = [_finger_tip_cx(fi) for fi in FINGERS.values()]
    th_cx = PALM_CX + THUMB["x_off"]
    th_cy = PALM_CY + THUMB["y_off"]
    th_angle = math.radians(THUMB["angle_deg"])
    th_tip_y = th_cy - THUMB["len"] * math.cos(th_angle)
    th_tip_x = th_cx + THUMB["len"] * math.sin(th_angle)
    xs.append(th_tip_x)
    ys.append(th_tip_y)
    palm_lx = PALM_CX - PALM_W // 2
    palm_rx = PALM_CX + PALM_W // 2
    xs.extend([palm_lx, palm_rx])
    ys.extend([FINGER_BASE_Y, WRIST_BOTTOM])
    pad = SAFE_MARGIN
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


def anchors(side="L"):
    """Return line paths and mount positions (used by compositor, NOT in hand SVG)."""
    lines = {
        "vida": [
            (PALM_CX - 240, PALM_CY - 240),
            (PALM_CX - 280, PALM_CY - 80),
            (PALM_CX - 260, PALM_CY + 80),
            (PALM_CX - 180, PALM_CY + 220),
            (PALM_CX - 80, PALM_CY + 280),
        ],
        "corazon": [
            (PALM_CX - 320, PALM_CY - 160),
            (PALM_CX - 160, PALM_CY - 190),
            (PALM_CX, PALM_CY - 200),
            (PALM_CX + 160, PALM_CY - 180),
            (PALM_CX + 280, PALM_CY - 140),
        ],
        "cabeza": [
            (PALM_CX - 300, PALM_CY - 60),
            (PALM_CX - 120, PALM_CY - 40),
            (PALM_CX + 60, PALM_CY - 20),
            (PALM_CX + 220, PALM_CY + 20),
            (PALM_CX + 340, PALM_CY + 60),
        ],
        "destino": [
            (PALM_CX + 10, PALM_CY - 240),
            (PALM_CX, PALM_CY - 100),
            (PALM_CX - 10, PALM_CY + 40),
            (PALM_CX, PALM_CY + 160),
        ],
    }
    mounts = {
        "jupiter":  (PALM_CX - 130, PALM_CY - 200, 44),
        "saturno":  (PALM_CX + 10,  PALM_CY - 230, 44),
        "sol":      (PALM_CX + 150, PALM_CY - 200, 40),
        "mercurio": (PALM_CX + 270, PALM_CY - 110, 36),
        "venus":    (PALM_CX - 200, PALM_CY + 160, 70),
    }
    return lines, mounts


def anchors_normalized():
    """Return anchors in 0-1 normalized coordinates per §10."""
    lines, mounts = anchors()
    norm_lines = {}
    for k, pts in lines.items():
        norm_lines[k] = [(x / VB, y / VB) for x, y in pts]
    norm_mounts = {}
    for k, (x, y, r) in mounts.items():
        norm_mounts[k] = (x / VB, y / VB, r / VB)
    return norm_lines, norm_mounts


def palm_line_anchors():
    lines, _ = anchors()
    return lines


def emit_svg(side="L"):
    svg = hand_svg(side)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    svg_path = OUT_DIR / f"mano_{('izquierda' if side == 'L' else 'derecha')}_v10.svg"
    svg_path.write_text(svg, encoding="utf-8")

    if side == "L":
        svg_r = hand_svg("R")
        r_path = OUT_DIR / "mano_derecha_v10.svg"
        r_path.write_text(svg_r, encoding="utf-8")
    else:
        svg_l = hand_svg("L")
        l_path = OUT_DIR / "mano_izquierda_v10.svg"
        l_path.write_text(svg_l, encoding="utf-8")

    # Landmarks JSON (scaled to 2048)
    lm = {"side": side, "viewbox": VB, "coordinate_system": "pixel_2048",
          "fingers": {}, "wrist": [], "palm_center": [PALM_CX, PALM_CY]}
    for fname, fi in FINGERS.items():
        lm["fingers"][fname] = {
            "tip": [_finger_tip_cx(fi), _finger_tip_cy(fi)],
            "base_left": [_finger_left(fi), FINGER_BASE_Y],
            "base_right": [_finger_right(fi), FINGER_BASE_Y],
        }
    lm["wrist"] = [
        [PALM_CX - WRIST_W // 2, WRIST_BOTTOM],
        [PALM_CX + WRIST_W // 2, WRIST_BOTTOM],
    ]
    # Thumb
    th_cx = PALM_CX + THUMB["x_off"]
    th_cy = PALM_CY + THUMB["y_off"]
    th_angle = math.radians(THUMB["angle_deg"])
    lm["thumb"] = {
        "tip": [int(th_cx + THUMB["len"] * math.sin(th_angle)),
                int(th_cy - THUMB["len"] * math.cos(th_angle))],
        "base": [th_cx, th_cy],
    }
    # Normalized coordinates
    norm_lines, norm_mounts = anchors_normalized()
    lm["anchors_normalized"] = {"lines": norm_lines, "mounts": norm_mounts}

    json_path = OUT_DIR / "hand_landmarks_v10.json"
    json_path.write_text(json.dumps(lm, indent=2, ensure_ascii=False), encoding="utf-8")

    return svg_path, json_path, lm


def selftest():
    """Verify segmented hand structure."""
    # Count fingers in SVG
    svg = hand_svg("L")
    finger_ids = ["palm-silhouette", "thumb", "index-finger", "middle-finger",
                  "ring-finger", "little-finger", "wrist"]
    present = [fid for fid in finger_ids if f'id="{fid}"' in svg]

    # Verify no mounts/lines in SVG
    has_mount = any(w in svg.lower() for w in ["jupiter", "saturn", "venus", "mercury"])
    has_line = any(w in svg.lower() for w in ["vida", "corazon", "cabeza", "destino"])

    # Verify viewBox 2048
    has_2048 = 'viewBox="0 0 2048 2048"' in svg

    # Verify no text labels
    has_text = "<text" in svg

    # Verify asset ID
    has_id = 'id="HAND_L_PALM_FRONT_V001"' in svg

    # Verify layers
    has_creases = 'id="natural-creases"' in svg
    has_shading = 'id="shading"' in svg

    # Finger tips above palm
    tips_y = [_finger_tip_cy(fi) for fi in FINGERS.values()]
    tips_above = sum(1 for y in tips_y if y < FINGER_BASE_Y)
    tips_x = sorted([_finger_tip_cx(fi) for fi in FINGERS.values()])
    spread = tips_x[-1] - tips_x[0]

    ok = (len(present) == 7 and not has_mount and not has_line
          and has_2048 and not has_text and has_id
          and has_creases and has_shading
          and tips_above == 4 and spread > 400)

    print(json.dumps({
        "side": "L",
        "ok": ok,
        "viewbox": VB,
        "segmented_ids": present,
        "all_ids_present": len(present) == 7,
        "no_mounts_in_svg": not has_mount,
        "no_lines_in_svg": not has_line,
        "no_text_in_svg": not has_text,
        "viewbox_2048": has_2048,
        "asset_id_correct": has_id,
        "layers_present": has_creases and has_shading,
        "finger_tips_above_palm": tips_above,
        "finger_spread_px": spread,
    }, indent=2))
    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hand geometry V10 — segmented 2048×2048")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--emit", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        sys.exit(0 if selftest() else 1)
    elif args.emit:
        svg_path, json_path, lm = emit_svg()
        print(f"SVG L: {svg_path}")
        print(f"SVG R: {OUT_DIR / 'mano_derecha_v10.svg'}")
        print(f"JSON: {json_path}")
    else:
        svg_path, json_path, lm = emit_svg()
        ok = selftest()
        print(f"Emitted: {svg_path}")
        print(f"Selftest: {'PASS' if ok else 'FAIL'}")
