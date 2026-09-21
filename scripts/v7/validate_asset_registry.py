"""validate_asset_registry.py - Valida registro de assets V7/V8.

Ademas de validar cada fila registrada (ruta dentro del proyecto, archivo
existente, licencia comercial verificada), recorre el disco y reporta los
SVG que existen pero NO estan registrados (huerfanos). El validador
anterior iteraba solo las lineas del registro, por lo que no podia
detectar archivos sin registrar.
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
REG = ROOT / "assets/v7/registry/assets.jsonl"
ASSETS_ROOT = (ROOT / "assets").resolve()
STATES = {"PENDING", "GENERATING", "VALIDATING", "APPROVED", "FROZEN"}


def main():
    errors = []
    orphans = []
    registered = set()
    if not REG.exists():
        print(json.dumps({"passed": False,
                          "errors": [["0", "registro no encontrado"]]}, indent=2))
        sys.exit(1)
    for i, line in enumerate(REG.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            x = json.loads(line)
        except Exception as e:
            errors.append([i, f"JSON invalido: {e}"])
            continue
        rel = x.get("file", "")
        if rel.startswith("../") or rel.startswith("..\\") or ":" in rel.split("/")[0]:
            errors.append([i, "path traversal"])
            continue
        p = (ROOT / rel).resolve()
        if ASSETS_ROOT not in p.parents and p != ASSETS_ROOT:
            errors.append([i, "fuera de assets/"])
            continue
        if not p.exists():
            errors.append([i, "missing file"])
        registered.add(str(p))
        lic = x.get("license", {})
        if lic.get("commercial_use") != "YES" or lic.get("status") != "VERIFIED":
            errors.append([i, "commercial license not verified"])
        if x.get("status") not in STATES:
            errors.append([i, f"estado invalido: {x.get('status')}"])

    # Deteccion de huerfanos: SVG en disco sin registrar.
    for f in ASSETS_ROOT.rglob("*.svg"):
        if str(f.resolve()) not in registered:
            orphans.append(str(f.relative_to(ROOT)))

    result = {"passed": not errors and not orphans,
              "errors": errors, "orphans": sorted(orphans)}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
