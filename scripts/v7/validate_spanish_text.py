"""validate_spanish_text.py - Valida la ortografía de los textos visuales.

V8: revisa las fuentes del motor visual vigente (scripts/v8, config/v8,
config/prompts y docs/v7) en lugar de los generadores raster legacy, que
fueron retirados. Comprueba las denominaciones obligatorias del sistema
(docs/v7/03-IMAGENES-Y-ORTOGRAFIA.md).
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]

CHECKS = {
    "Linea de la": "Línea de la",
    "Linea del": "Línea del",
    "Jupiter": "Júpiter",
    "Mitologia": "Mitología",
    "Quiromancia Terapeutica": "Quiromancia terapéutica",
    "TERAPEUTICA": "TERAPÉUTICA",
}

TARGETS = [
    "scripts/v8/compositor.py",
    "scripts/v8/hand_geometry.py",
    "config/v8/render_profiles.yaml",
    "config/prompts/hands.yaml",
    "docs/v7/03-IMAGENES-Y-ORTOGRAFIA.md",
]


def main():
    errors = []
    for rel in TARGETS:
        p = ROOT / rel
        if not p.exists():
            continue
        s = p.read_text(encoding="utf-8")
        for bad, good in CHECKS.items():
            if bad in s:
                errors.append({"file": rel, "bad": bad, "expected": good})
    print(json.dumps({"passed": not errors, "errors": errors},
                     ensure_ascii=False, indent=2))
    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
