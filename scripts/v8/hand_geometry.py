"""
Hand geometry v9 – anatomical outline as a single smooth Bézier path.

The hand is drawn in a LEFT palmar view inside a 1024×1024 viewBox.
The outline traces continuously: wrist → palm → index → middle → ring →
pinky → palm → thumb → wrist. Fingers are clearly separated with
rounded tips.  No raster tracing – the path is defined mathematically
for crisp, smooth curves at any resolution.

Output: SVG master + JSON landmarks + selftest.
"""
import argparse, json, math, sys
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "v8" / "hands"
SVG_OUT = OUT_DIR / "mano_izquierda_v9.svg"
JSON_OUT = OUT_DIR / "hand_landmarks_v9.json"

# ── ViewBox & palm geometry ─────────────────────────────────────────
VIEWBOX = 1024  # alias for compositor compatibility
VB = VIEWBOX
# Palm: wide, centred
PALM_CX, PALM_CY = 512, 590
PALM_W, PALM_H = 380, 300  # wide and not too tall

# Finger base positions (x offsets from palm centre, y = top of palm)
# These are the gaps between fingers at the palm top edge
FINGER_BASE_Y = PALM_CY - PALM_H // 2  # 440

# Finger dimensions: (length, base_width, tip_width, x_offset_from_centre)
# Index is leftmost, pinky rightmost (palmar view, left hand)
FINGERS = {
    "indice":    {"x_off": -105, "len": 250, "base_w": 54, "tip_w": 36},
    "medio":     {"x_off":  -30, "len": 280, "base_w": 54, "tip_w": 36},
    "anular":    {"x_off":   45, "len": 245, "base_w": 50, "tip_w": 34},
    "menique":   {"x_off":  115, "len": 195, "base_w": 44, "tip_w": 30},
}
# Thumb: originates from lower-left of palm, angles outward
THUMB = {"x_off": -220, "y_off": 110, "len": 210, "base_w": 56, "tip_w": 38,
         "angle_deg": -35}  # angle from vertical (negative = leftward)

# Wrist
WRIST_W = 160
WRIST_BOTTOM = PALM_CY + PALM_H // 2 + 80  # 800


# ── Bezier helpers ──────────────────────────────────────────────────

def catmull_rom_to_bezier(p0, p1, p2, p3, tension=0.4):
    """Convert 4 Catmull-Rom points to a cubic Bézier segment."""
    d1 = (p2[0] - p0[0], p2[1] - p0[1])
    d2 = (p3[0] - p1[0], p3[1] - p1[1])
    cp1 = (p1[0] + d1[0] * tension, p1[1] + d1[1] * tension)
    cp2 = (p2[0] - d2[0] * tension, p2[1] - d2[1] * tension)
    return cp1, cp2


def smooth_path(keypoints, closed=True):
    """Return SVG path d-attribute using Catmull-Rom → cubic Bézier."""
    n = len(keypoints)
    pts = list(keypoints)
    if closed:
        pts = [pts[-1]] + pts + [pts[0], pts[1]]
    else:
        pts = [pts[0]] + pts + [pts[-1]]

    segments = []
    for i in range(1, len(pts) - 2):
        cp1, cp2 = catmull_rom_to_bezier(pts[i - 1], pts[i], pts[i + 1], pts[i + 2])
        if i == 1 and not closed:
            segments.append(f"M{pts[i][0]:.1f},{pts[i][1]:.1f}")
            segments.append(f"C{cp1[0]:.1f},{cp1[1]:.1f} {cp2[0]:.1f},{cp2[1]:.1f} {pts[i+1][0]:.1f},{pts[i+1][1]:.1f}")
        elif i == 1:
            segments.append(f"M{pts[i][0]:.1f},{pts[i][1]:.1f}")
            segments.append(f"C{cp1[0]:.1f},{cp1[1]:.1f} {cp2[0]:.1f},{cp2[1]:.1f} {pts[i+1][0]:.1f},{pts[i+1][1]:.1f}")
        else:
            segments.append(f"C{cp1[0]:.1f},{cp1[1]:.1f} {cp2[0]:.1f},{cp2[1]:.1f} {pts[i+1][0]:.1f},{pts[i+1][1]:.1f}")

    if closed:
        segments.append("Z")
    return "".join(segments)


# ── Hand outline keypoints ──────────────────────────────────────────

def _finger_tip_cx(finfo):
    """x of finger tip centre."""
    return PALM_CX + finfo["x_off"]

def _finger_tip_cy(finfo):
    """y of finger tip."""
    return FINGER_BASE_Y - finfo["len"]

def _finger_left(finfo, y=None):
    """x of left edge of finger at given y (default: base)."""
    if y is None:
        y = FINGER_BASE_Y
    # Linear taper from base_w/2 at base to tip_w/2 at tip
    t = (FINGER_BASE_Y - y) / finfo["len"] if finfo["len"] else 0
    half_w = (finfo["base_w"] / 2) * (1 - t) + (finfo["tip_w"] / 2) * t
    return PALM_CX + finfo["x_off"] - half_w

def _finger_right(finfo, y=None):
    if y is None:
        y = FINGER_BASE_Y
    t = (FINGER_BASE_Y - y) / finfo["len"] if finfo["len"] else 0
    half_w = (finfo["base_w"] / 2) * (1 - t) + (finfo["tip_w"] / 2) * t
    return PALM_CX + finfo["x_off"] + half_w

def _finger_tip_left(finfo):
    return _finger_left(finfo, _finger_tip_cy(finfo))

def _finger_tip_right(finfo):
    return _finger_right(finfo, _finger_tip_cy(finfo))


def build_hand_outline():
    """
    Build the complete hand outline as a list of keypoints.
    Traces: wrist_L → palm_L → between fingers → finger tips → wrist_R → thumb → wrist_L
    """
    pts = []

    # ── Left wrist / lower palm ────────────────────────────────────
    wrist_lx = PALM_CX - WRIST_W // 2   # 432
    wrist_rx = PALM_CX + WRIST_W // 2   # 592
    palm_lx = PALM_CX - PALM_W // 2     # 322
    palm_rx = PALM_CX + PALM_W // 2     # 702
    palm_top = FINGER_BASE_Y             # 440
    palm_bot = PALM_CY + PALM_H // 2    # 740

    # Start at left wrist, going up
    pts.append((wrist_lx, WRIST_BOTTOM))      # 0: wrist left bottom
    pts.append((wrist_lx, palm_bot - 20))      # 1: wrist left mid
    pts.append((palm_lx + 10, palm_bot))       # 2: palm left lower
    pts.append((palm_lx, palm_bot - 60))       # 3: palm left mid
    pts.append((palm_lx - 5, PALM_CY))         # 4: palm left widest
    pts.append((palm_lx + 5, palm_top + 40))   # 5: palm left upper
    pts.append((palm_lx + 20, palm_top + 10))  # 6: palm left near top

    # ── Fingers: index → middle → ring → pinky ─────────────────────
    finger_order = ["indice", "medio", "anular", "menique"]
    for i, fname in enumerate(finger_order):
        fi = FINGERS[fname]
        tip_cy = _finger_tip_cy(fi)
        tip_cx = _finger_tip_cx(fi)
        tl = _finger_tip_left(fi)
        tr = _finger_tip_right(fi)
        bl = _finger_left(fi, palm_top)
        br = _finger_right(fi, palm_top)

        # Gap between previous finger's right edge and this finger's left edge
        # At the palm top, fingers are separated by small gaps
        gap = 6  # pixels between fingers at base

        if i == 0:
            # Index: left side connects from palm top
            pts.append((bl - gap, palm_top))      # 7: between palm and index left

        # Left side of finger (going up)
        pts.append((bl, palm_top + 5))             # finger base left
        pts.append((bl + 3, palm_top - 10))        # slight inward curve
        pts.append((tl + 2, tip_cy + 60))          # mid finger left
        pts.append((tl + 1, tip_cy + 30))          # upper finger left

        # Tip (rounded) - 3 points for smooth curve
        pts.append((tl + 3, tip_cy + 8))           # tip left approach
        pts.append((tip_cx, tip_cy - 4))           # tip centre (highest point)
        pts.append((tr - 3, tip_cy + 8))           # tip right approach

        # Right side of finger (going down)
        pts.append((tr - 1, tip_cy + 30))          # upper finger right
        pts.append((tr - 3, tip_cy + 60))          # mid finger right
        pts.append((br - 3, palm_top - 10))        # slight inward
        pts.append((br, palm_top + 5))             # finger base right

        # Gap to next finger (or to palm edge for pinky)
        if i < len(finger_order) - 1:
            nxt = FINGERS[finger_order[i + 1]]
            nxt_bl = _finger_left(nxt, palm_top)
            pts.append((br + gap, palm_top))        # gap right side
            pts.append((nxt_bl - gap, palm_top))    # next finger gap left
        else:
            # After pinky: connect to right palm edge
            pts.append((br + gap, palm_top))
            pts.append((palm_rx - 20, palm_top + 10))

    # ── Right palm edge (going down) ───────────────────────────────
    pts.append((palm_rx - 5, palm_top + 40))
    pts.append((palm_rx, PALM_CY + 20))
    pts.append((palm_rx - 5, palm_bot - 30))
    pts.append((palm_rx - 15, palm_bot + 10))

    # ── Thumb (from lower-right of palm, angling down-right) ───────
    # Thumb is separate from the four fingers, originating lower
    th_cx = PALM_CX + THUMB["x_off"]   # 337
    th_cy = PALM_CY + THUMB["y_off"]   # 700
    th_len = THUMB["len"]
    th_angle = math.radians(THUMB["angle_deg"])
    th_basew = THUMB["base_w"] / 2
    th_tipw = THUMB["tip_w"] / 2

    # Thumb tip position
    th_tip_x = th_cx + th_len * math.sin(th_angle)
    th_tip_y = th_cy - th_len * math.cos(th_angle)

    # Thumb base is at the lower-left of the palm
    # Left side of thumb (going from palm toward tip)
    pts.append((palm_lx + 30, palm_bot - 10))   # connect from palm
    pts.append((th_cx + th_basew + 5, th_cy - 30))  # thumb base right
    pts.append((th_cx + th_basew, th_cy))       # thumb mid right
    pts.append((th_cx + th_tipw + 10, th_tip_y + 40)) # thumb upper right

    # Thumb tip (rounded)
    pts.append((th_cx + th_tipw + 3, th_tip_y + 10))
    pts.append((th_tip_x, th_tip_y - 5))        # tip
    pts.append((th_cx - th_tipw - 3, th_tip_y + 10))

    # Left side of thumb (going back toward wrist)
    pts.append((th_cx - th_tipw - 10, th_tip_y + 40))
    pts.append((th_cx - th_basew, th_cy))
    pts.append((th_cx - th_basew - 5, th_cy - 40))
    pts.append((palm_lx + 20, palm_bot + 5))    # connect back to palm/wrist

    # ── Close to wrist left ────────────────────────────────────────
    pts.append((wrist_lx + 10, palm_bot))

    return pts


def build_hand_svg(side="L", outline_d="", landmarks=None):
    """Build the SVG string."""
    skin = "#F5CBA7"
    skin_stroke = "#D4A574"
    wrist_fill = "#E8B88A"

    # Mounts: colored circles on the palm (positioned relative to palm)
    mounts = [
        ("Jupiter",  PALM_CX - 65,  PALM_CY - 100, "#FF6B6B", 22),
        ("Saturn",   PALM_CX + 5,   PALM_CY - 115, "#FFD93D", 22),
        ("Sun",      PALM_CX + 75,  PALM_CY - 100, "#6BCB77", 20),
        ("Mercury",  PALM_CX + 135, PALM_CY - 55,  "#4D96FF", 18),
        ("Venus",    PALM_CX - 100, PALM_CY + 80,  "#FFFFFF", 35),
    ]

    # Lines: thick colored dashed paths
    lines_svg = ""
    # Life line: curves from between thumb-index down around Venus mount
    life_pts = [
        (PALM_CX - 120, PALM_CY - 120),
        (PALM_CX - 140, PALM_CY - 40),
        (PALM_CX - 130, PALM_CY + 40),
        (PALM_CX - 90, PALM_CY + 110),
        (PALM_CX - 40, PALM_CY + 140),
    ]
    lines_svg += f'<path d="{_line_d(life_pts)}" stroke="#00D4FF" stroke-width="8" fill="none" stroke-dasharray="16,8" opacity="0.9"/>\n'

    # Heart line: across upper palm
    heart_pts = [
        (PALM_CX - 160, PALM_CY - 80),
        (PALM_CX - 80, PALM_CY - 95),
        (PALM_CX + 0, PALM_CY - 100),
        (PALM_CX + 80, PALM_CY - 90),
        (PALM_CX + 140, PALM_CY - 70),
    ]
    lines_svg += f'<path d="{_line_d(heart_pts)}" stroke="#FF6B9D" stroke-width="8" fill="none" stroke-dasharray="16,8" opacity="0.9"/>\n'

    # Head line: across mid palm
    head_pts = [
        (PALM_CX - 150, PALM_CY - 30),
        (PALM_CX - 60, PALM_CY - 20),
        (PALM_CX + 30, PALM_CY - 10),
        (PALM_CX + 110, PALM_CY + 10),
        (PALM_CX + 170, PALM_CY + 30),
    ]
    lines_svg += f'<path d="{_line_d(head_pts)}" stroke="#FFA500" stroke-width="8" fill="none" stroke-dasharray="16,8" opacity="0.9"/>\n'

    # Destiny line: vertical through centre
    destiny_pts = [
        (PALM_CX + 5, PALM_CY - 120),
        (PALM_CX + 0, PALM_CY - 50),
        (PALM_CX - 5, PALM_CY + 20),
        (PALM_CX + 0, PALM_CY + 80),
    ]
    lines_svg += f'<path d="{_line_d(destiny_pts)}" stroke="#FFD93D" stroke-width="7" fill="none" stroke-dasharray="14,8" opacity="0.85"/>\n'

    mounts_svg = ""
    for name, mx, my, color, r in mounts:
        mounts_svg += f'<circle cx="{mx}" cy="{my}" r="{r}" fill="{color}" opacity="0.9"/>\n'

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VB} {VB}" width="{VB}" height="{VB}">
  <defs>
    <radialGradient id="palmGrad" cx="50%" cy="45%" r="55%">
      <stop offset="0%" stop-color="#FADEC9"/>
      <stop offset="100%" stop-color="#E8B88A"/>
    </radialGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>

  <!-- Hand outline -->
  <path d="{outline_d}" fill="url(#palmGrad)" stroke="{skin_stroke}" stroke-width="4"
        stroke-linejoin="round" stroke-linecap="round" filter="url(#glow)"/>

  <!-- Lines on palm -->
  {lines_svg}

  <!-- Mounts -->
  {mounts_svg}

  <!-- Landmarks (small dots for QA) -->
  {"".join(f'<circle cx="{l[0]}" cy="{l[1]}" r="4" fill="#fff" opacity="0.6"/>' for l in (landmarks or []))}
</svg>'''
    return svg


def _line_d(pts):
    """Build a smooth SVG path for a line through points."""
    if len(pts) < 2:
        return ""
    d = f"M{pts[0][0]},{pts[0][1]}"
    for i in range(1, len(pts)):
        prev = pts[i - 1]
        curr = pts[i]
        cpx = (prev[0] + curr[0]) / 2
        cpy = (prev[1] + curr[1]) / 2
        d += f" Q{prev[0]},{prev[1]} {cpx},{cpy}"
    d += f" L{pts[-1][0]},{pts[-1][1]}"
    return d


def hand_svg(side="L"):
    """Return the SVG string for the given side (used by compositor)."""
    outline_pts = build_hand_outline()
    outline_d = smooth_path(outline_pts, closed=True)
    landmarks = []
    for fname, fi in FINGERS.items():
        landmarks.append((_finger_tip_cx(fi), _finger_tip_cy(fi)))
    landmarks.append((PALM_CX - WRIST_W // 2, WRIST_BOTTOM))
    landmarks.append((PALM_CX + WRIST_W // 2, WRIST_BOTTOM))
    svg = build_hand_svg(side, outline_d, landmarks)
    if side.upper() == "R":
        svg = svg.replace('<g ', '<g transform="translate(1024,0) scale(-1,1)" ', 1)
    return svg


def content_bbox():
    """Return (x0, y0, x1, y1) bounding box of the hand content (fingers + palm + thumb)."""
    # Include all finger tips and thumb tip
    ys = [_finger_tip_cy(fi) for fi in FINGERS.values()]
    xs = [_finger_tip_cx(fi) for fi in FINGERS.values()]
    # Thumb tip
    th_cx = PALM_CX + THUMB["x_off"]
    th_cy = PALM_CY + THUMB["y_off"]
    th_len = THUMB["len"]
    th_angle = math.radians(THUMB["angle_deg"])
    th_tip_y = th_cy - th_len * math.cos(th_angle)
    th_tip_x = th_cx + th_len * math.sin(th_angle)
    xs.append(th_tip_x)
    ys.append(th_tip_y)
    # Palm edges
    palm_lx = PALM_CX - PALM_W // 2
    palm_rx = PALM_CX + PALM_W // 2
    xs.extend([palm_lx, palm_rx])
    ys.extend([PALM_CY - PALM_H // 2, WRIST_BOTTOM])
    pad = 30
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


def anchors(side="L"):
    """Return line paths and mount positions in viewBox coordinates.
    Format: {"corazon": [(x,y),...], "cabeza": [...], ...}, {"venus": (x,y,r), ...}"""
    # Line paths: each is a list of (x,y) points
    lines = {
        "vida": [
            (PALM_CX - 120, PALM_CY - 120),
            (PALM_CX - 140, PALM_CY - 40),
            (PALM_CX - 130, PALM_CY + 40),
            (PALM_CX - 90, PALM_CY + 110),
            (PALM_CX - 40, PALM_CY + 140),
        ],
        "corazon": [
            (PALM_CX - 160, PALM_CY - 80),
            (PALM_CX - 80, PALM_CY - 95),
            (PALM_CX + 0, PALM_CY - 100),
            (PALM_CX + 80, PALM_CY - 90),
            (PALM_CX + 140, PALM_CY - 70),
        ],
        "cabeza": [
            (PALM_CX - 150, PALM_CY - 30),
            (PALM_CX - 60, PALM_CY - 20),
            (PALM_CX + 30, PALM_CY - 10),
            (PALM_CX + 110, PALM_CY + 10),
            (PALM_CX + 170, PALM_CY + 30),
        ],
        "destino": [
            (PALM_CX + 5, PALM_CY - 120),
            (PALM_CX + 0, PALM_CY - 50),
            (PALM_CX - 5, PALM_CY + 20),
            (PALM_CX + 0, PALM_CY + 80),
        ],
    }
    # Mount positions: (x, y, radius)
    mounts = {
        "jupiter":  (PALM_CX - 65,  PALM_CY - 100, 22),
        "saturno":  (PALM_CX + 5,   PALM_CY - 115, 22),
        "sol":      (PALM_CX + 75,  PALM_CY - 100, 20),
        "mercurio": (PALM_CX + 135, PALM_CY - 55,  18),
        "venus":    (PALM_CX - 100, PALM_CY + 80,  35),
    }
    return lines, mounts


def palm_line_anchors():
    """Return only line anchors (used by compositor scene 3)."""
    lines, _ = anchors()
    return lines


def emit_svg(side="L"):
    outline_pts = build_hand_outline()
    outline_d = smooth_path(outline_pts, closed=True)
    landmarks = []
    for fname, fi in FINGERS.items():
        landmarks.append((_finger_tip_cx(fi), _finger_tip_cy(fi)))
    landmarks.append((PALM_CX - WRIST_W // 2, WRIST_BOTTOM))
    landmarks.append((PALM_CX + WRIST_W // 2, WRIST_BOTTOM))

    svg = build_hand_svg(side, outline_d, landmarks)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SVG_OUT.write_text(svg, encoding="utf-8")

    rsvg = svg.replace('<g ', '<g transform="translate(1024,0) scale(-1,1)" ', 1)
    rpath = OUT_DIR / "mano_derecha_v9.svg"
    rpath.write_text(rsvg, encoding="utf-8")

    lm = {"side": side, "fingers": {}, "wrist": landmarks[-2:],
          "palm_center": [PALM_CX, PALM_CY], "viewbox": VB}
    for fname, fi in FINGERS.items():
        lm["fingers"][fname] = {
            "tip": [_finger_tip_cx(fi), _finger_tip_cy(fi)],
            "base_left": [_finger_left(fi), FINGER_BASE_Y],
            "base_right": [_finger_right(fi), FINGER_BASE_Y],
        }
    JSON_OUT.write_text(json.dumps(lm, indent=2, ensure_ascii=False), encoding="utf-8")

    return SVG_OUT, rsvg, lm


def selftest():
    """Verify the hand has proper finger tips and shape."""
    outline_pts = build_hand_outline()

    # Check we have enough points for a smooth hand
    n_pts = len(outline_pts)

    # Check finger tips are in the right region (upper portion of viewBox)
    tips_y = [_finger_tip_cy(fi) for fi in FINGERS.values()]
    tips_above_palm = sum(1 for y in tips_y if y < PALM_CY - PALM_H // 2)

    # Check no finger tip is below the palm
    tips_below_palm = sum(1 for y in tips_y if y > PALM_CY)

    # Check finger separation: tips should be spread horizontally
    tips_x = sorted([_finger_tip_cx(fi) for fi in FINGERS.values()])
    spread = tips_x[-1] - tips_x[0]

    ok = (tips_above_palm == 4 and tips_below_palm == 0
          and spread > 200 and n_pts > 40)

    print(json.dumps({
        "side": "L",
        "ok": ok,
        "outline_points": n_pts,
        "finger_tips_above_palm": tips_above_palm,
        "finger_spread_px": spread,
        "finger_tips_y": tips_y,
        "finger_tips_x": tips_x,
    }, indent=2))
    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hand geometry v9")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--emit", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        ok = selftest()
        sys.exit(0 if ok else 1)
    elif args.emit:
        svg_l, svg_r, lm = emit_svg()
        print(f"L: {svg_l}")
        print(f"R: {OUT_DIR / 'mano_derecha_v9.svg'}")
        print(f"JSON: {JSON_OUT}")
    else:
        svg_l, svg_r, lm = emit_svg()
        ok = selftest()
        print(f"Emitted: {svg_l}")
        print(f"Selftest: {'PASS' if ok else 'FAIL'}")
