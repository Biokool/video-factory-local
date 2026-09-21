"""
Validate SVG Library — verifica que todos los assets SVG cumplan §9.
"""
import json
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
SVG_DIR = PROJECT_DIR / "assets" / "v8" / "svg"
REGISTRY = SVG_DIR / "svg_library.json"

REQUIRED_LINES = [
    "vida", "cabeza", "corazon", "destino", "sol", "mercurio", "marte", "intuicion",
    "isis", "neptuno", "viajes", "hijos", "pareja", "rascetas",
    "anillo_familiar", "anillo_salomon", "cinturon_venus", "cruz_san_andres", "vidas_pasadas",
]
REQUIRED_MOUNTS = [
    "venus", "jupiter", "saturno", "sol", "mercurio", "luna",
    "marte_pos", "marte_neg", "urano", "neptuno", "pluton",
]
REQUIRED_SIGNS = [
    "cruz", "doble_cruz", "estrella", "triangulo", "cuadrado",
    "rejilla", "punto", "isla", "cadena", "ruptura", "rama",
    "lineas_paralelas", "final_pincel", "circulo_resaltado",
    "flecha", "conector", "lupa",
]


def validate():
    issues = []

    if not REGISTRY.exists():
        issues.append(f"Registry not found: {REGISTRY}")
        return issues

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    asset_ids = {r["asset_id"] for r in registry}

    for lid in REQUIRED_LINES:
        aid = f"LINE_{lid.upper()}_L_BASE_V001"
        if aid not in asset_ids:
            issues.append(f"Missing line: {aid}")

    for mid in REQUIRED_MOUNTS:
        aid = f"MOUNT_{mid.upper()}_L_V001"
        if aid not in asset_ids:
            issues.append(f"Missing mount: {aid}")

    for sid in REQUIRED_SIGNS:
        aid = f"SIGN_{sid.upper()}_V001"
        if aid not in asset_ids:
            issues.append(f"Missing sign: {aid}")

    for entry in registry:
        fpath = PROJECT_DIR / entry["file"]
        if not fpath.exists():
            issues.append(f"File missing: {entry['file']}")
        if entry.get("license", {}).get("commercial_use") != "YES":
            issues.append(f"Non-commercial: {entry['asset_id']}")

    return issues


if __name__ == "__main__":
    issues = validate()
    if issues:
        print(f"FAIL: {len(issues)} issues")
        for i in issues[:20]:
            print(f"  - {i}")
        sys.exit(1)
    else:
        print("PASS: All SVG library assets valid")
        sys.exit(0)
