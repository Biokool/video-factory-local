"""
SVG Asset Library — genera SVGs independientes para líneas, montes y signos.

Cada asset es un archivo SVG separado con la estructura requerida por §9
de la especificación maestra. Los archivos se guardan en assets/v8/svg/.
"""
import json
import hashlib
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "v8" / "svg"

# ── Colores de líneas (consistente con compositor) ──────────────────
LINE_COLORS = {
    "vida":     {"hex": "#00D4FF", "rgb": (0.00, 0.83, 0.92), "name": "Línea de la Vida"},
    "cabeza":   {"hex": "#FFA500", "rgb": (1.00, 0.65, 0.00), "name": "Línea de la Cabeza"},
    "corazon":  {"hex": "#FF6B9D", "rgb": (1.00, 0.42, 0.61), "name": "Línea del Corazón"},
    "destino":  {"hex": "#FFD93D", "rgb": (1.00, 0.85, 0.24), "name": "Línea del Destino"},
    "sol":      {"hex": "#FF6B6B", "rgb": (1.00, 0.42, 0.42), "name": "Línea del Sol"},
    "mercurio": {"hex": "#4D96FF", "rgb": (0.30, 0.59, 1.00), "name": "Línea de Mercurio"},
    "marte":    {"hex": "#FF4444", "rgb": (1.00, 0.27, 0.27), "name": "Línea de Marte"},
    "intuicion":{"hex": "#9B59B6", "rgb": (0.61, 0.35, 0.71), "name": "Línea de la Intuición"},
}

# ── Colores de montes ───────────────────────────────────────────────
MOUNT_COLORS = {
    "venus":    {"hex": "#FFFFFF", "rgb": (1.0, 1.0, 1.0),   "name": "Monte de Venus"},
    "jupiter":  {"hex": "#FF6B6B", "rgb": (1.0, 0.42, 0.42), "name": "Monte de Júpiter"},
    "saturno":  {"hex": "#FFD93D", "rgb": (1.0, 0.85, 0.24), "name": "Monte de Saturno"},
    "sol":      {"hex": "#6BCB77", "rgb": (0.42, 0.79, 0.47), "name": "Monte del Sol"},
    "mercurio": {"hex": "#4D96FF", "rgb": (0.30, 0.59, 1.0),  "name": "Monte de Mercurio"},
    "luna":     {"hex": "#C0C0C0", "rgb": (0.75, 0.75, 0.75), "name": "Monte de la Luna"},
    "marte_pos":{"hex": "#FF4444", "rgb": (1.0, 0.27, 0.27),  "name": "Monte de Marte Positivo"},
    "marte_neg":{"hex": "#884444", "rgb": (0.53, 0.27, 0.27), "name": "Monte de Marte Negativo"},
    "urano":    {"hex": "#44FFFF", "rgb": (0.27, 1.0, 1.0),   "name": "Monte de Urano"},
    "neptuno":  {"hex": "#4488FF", "rgb": (0.27, 0.53, 1.0),  "name": "Monte de Neptuno"},
    "pluton":   {"hex": "#8844AA", "rgb": (0.53, 0.27, 0.67), "name": "Monte de Plutón"},
}

# ── Signos universales ──────────────────────────────────────────────
UNIVERSAL_SIGNS = [
    "cruz", "doble_cruz", "estrella", "triangulo", "cuadrado",
    "rejilla", "punto", "isla", "cadena", "ruptura", "rama",
    "lineas_paralelas", "final_pincel", "circulo_resaltado",
    "flecha", "conector", "lupa",
]


def _svg_wrap(inner: str, viewbox="0 0 2048 2048", extras: str = "") -> str:
    """Envuelve contenido SVG con la estructura estándar."""
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}" width="512" height="512">
  <defs>{extras}</defs>
  {inner}
</svg>'''


def generate_line_svg(line_id: str, points: list[tuple], color: str,
                      width: int = 12, dash: str = "16,8") -> str:
    """Genera SVG de una línea como path suave."""
    if len(points) < 2:
        return ""
    d = f"M{points[0][0]},{points[0][1]}"
    for i in range(1, len(points)):
        prev = points[i - 1]
        curr = points[i]
        mx = (prev[0] + curr[0]) / 2
        my = (prev[1] + curr[1]) / 2
        d += f" Q{prev[0]},{prev[1]} {mx},{my}"
    d += f" L{points[-1][0]},{points[-1][1]}"

    inner = f'''<g id="line-{line_id}">
    <path id="path-{line_id}" d="{d}"
          stroke="{color}" stroke-width="{width}" fill="none"
          stroke-dasharray="{dash}" stroke-linecap="round"
          stroke-linejoin="round"/>
  </g>'''
    return _svg_wrap(inner)


def generate_mount_svg(mount_id: str, cx: int, cy: int, r: int,
                       color: str, halo: bool = True) -> str:
    """Genera SVG de un Monte como círculo con halo opcional."""
    halo_elem = ""
    if halo:
        halo_elem = f'<circle class="halo" cx="{cx}" cy="{cy}" r="{r * 2}" fill="{color}" opacity="0.2"/>'

    inner = f'''<g id="mount-{mount_id}">
    {halo_elem}
    <circle id="circle-{mount_id}" cx="{cx}" cy="{cy}" r="{r}" fill="{color}" opacity="0.9"/>
    <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="white" stroke-width="3" opacity="0.8"/>
  </g>'''
    return _svg_wrap(inner)


def generate_sign_svg(sign_id: str, cx: int, cy: int, size: int = 40) -> str:
    """Genera SVG de un signo universal."""
    templates = {
        "cruz": f'<line x1="{cx}" y1="{cy-size}" x2="{cx}" y2="{cy+size}" stroke="white" stroke-width="4"/><line x1="{cx-size}" y1="{cy}" x2="{cx+size}" y2="{cy}" stroke="white" stroke-width="4"/>',
        "estrella": f'<polygon points="{cx},{cy-size} {cx+size//3},{cy+size//3} {cx+size},{cy+size//3} {cx+size//2},{cy+size//2} {cx+size//4},{cy+size} {cx},{cy+size//2-size//4} {cx-size//4},{cy+size} {cx-size//2},{cy+size//2} {cx-size},{cy+size//3} {cx-size//3},{cy+size//3}" fill="white" opacity="0.8"/>',
        "triangulo": f'<polygon points="{cx},{cy-size} {cx+size},{cy+size} {cx-size},{cy+size}" fill="none" stroke="white" stroke-width="4"/>',
        "cuadrado": f'<rect x="{cx-size}" y="{cy-size}" width="{size*2}" height="{size*2}" fill="none" stroke="white" stroke-width="4"/>',
        "punto": f'<circle cx="{cx}" cy="{cy}" r="{size//4}" fill="white"/>',
        "isla": f'<ellipse cx="{cx}" cy="{cy}" rx="{size}" ry="{size//2}" fill="none" stroke="white" stroke-width="3"/>',
        "ruptura": f'<line x1="{cx-size}" y1="{cy}" x2="{cx-5}" y2="{cy}" stroke="white" stroke-width="4"/><line x1="{cx+5}" y1="{cy}" x2="{cx+size}" y2="{cy}" stroke="white" stroke-width="4"/>',
    }
    svg_content = templates.get(sign_id, f'<circle cx="{cx}" cy="{cy}" r="{size//3}" fill="white" opacity="0.5"/>')
    inner = f'<g id="sign-{sign_id}">{svg_content}</g>'
    return _svg_wrap(inner)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def generate_all():
    """Genera toda la librería SVG."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    registry = []

    # ── Líneas ──────────────────────────────────────────────────────
    line_paths = {
        "vida":    [(640, 520), (580, 680), (560, 840), (620, 960), (700, 1020)],
        "cabeza":  [(520, 760), (640, 740), (780, 720), (920, 700), (1040, 680)],
        "corazon": [(480, 620), (600, 580), (740, 560), (880, 580), (1000, 620)],
        "destino": [(740, 520), (740, 680), (740, 840), (740, 960)],
        "sol":     [(800, 560), (860, 640), (920, 720), (960, 800)],
        "mercurio":[(600, 900), (660, 920), (720, 940), (780, 920)],
        "marte":   [(520, 800), (580, 840), (640, 880)],
        "intuicion":[(680, 600), (720, 720), (740, 840)],
    }

    for lid, points in line_paths.items():
        info = LINE_COLORS.get(lid, {"hex": "#FFFFFF", "name": lid})
        fname = f"LINE_{lid.upper()}_L_BASE_V001.svg"
        fpath = OUT_DIR / fname
        fpath.write_text(generate_line_svg(lid, points, info["hex"]), encoding="utf-8")
        registry.append({
            "asset_id": f"LINE_{lid.upper()}_L_BASE_V001",
            "file": f"assets/v8/svg/{fname}",
            "type": "LINE",
            "status": "FROZEN",
            "license": {"name": "project_owned", "commercial_use": "YES", "status": "VERIFIED"},
            "sha256": _sha256_file(fpath),
        })

    # ── Montes ──────────────────────────────────────────────────────
    mount_positions = {
        "venus":    (580, 920, 40),
        "jupiter":  (640, 560, 28),
        "saturno":  (740, 520, 28),
        "sol":      (840, 560, 25),
        "mercurio": (960, 680, 22),
        "luna":     (480, 960, 22),
        "marte_pos":(520, 760, 20),
        "marte_neg":(480, 840, 20),
        "urano":    (700, 480, 18),
        "neptuno":  (600, 1000, 18),
        "pluton":   (500, 1040, 18),
    }

    for mid, (cx, cy, r) in mount_positions.items():
        info = MOUNT_COLORS.get(mid, {"hex": "#FFFFFF", "name": mid})
        fname = f"MOUNT_{mid.upper()}_L_V001.svg"
        fpath = OUT_DIR / fname
        fpath.write_text(generate_mount_svg(mid, cx, cy, r, info["hex"]), encoding="utf-8")
        registry.append({
            "asset_id": f"MOUNT_{mid.upper()}_L_V001",
            "file": f"assets/v8/svg/{fname}",
            "type": "MOUNT",
            "status": "FROZEN",
            "license": {"name": "project_owned", "commercial_use": "YES", "status": "VERIFIED"},
            "sha256": _sha256_file(fpath),
        })

    # ── Signos ──────────────────────────────────────────────────────
    for sign in UNIVERSAL_SIGNS:
        fname = f"SIGN_{sign.upper()}_V001.svg"
        fpath = OUT_DIR / fname
        fpath.write_text(generate_sign_svg(sign, 1024, 1024, 40), encoding="utf-8")
        registry.append({
            "asset_id": f"SIGN_{sign.upper()}_V001",
            "file": f"assets/v8/svg/{fname}",
            "type": "SIGN",
            "status": "FROZEN",
            "license": {"name": "project_owned", "commercial_use": "YES", "status": "VERIFIED"},
            "sha256": _sha256_file(fpath),
        })

    # ── Guardar registry ────────────────────────────────────────────
    reg_path = OUT_DIR / "svg_library.json"
    reg_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Generados: {len(registry)} assets SVG")
    print(f"  Líneas: {len(line_paths)}")
    print(f"  Montes: {len(mount_positions)}")
    print(f"  Signos: {len(UNIVERSAL_SIGNS)}")
    print(f"Registry: {reg_path}")
    return registry


if __name__ == "__main__":
    generate_all()
