"""asset_registry.py - Resolucion segura de asset_id y maquina de estados V8.

Reglas (docs/v7/05):
  - El storyboard solo aporta asset_id; el registro traduce a ruta.
  - La ruta resuelta debe permanecer dentro de assets/ (se rechaza ../, C:\\,
    \\\\servidor\\, http://, https://).
  - Estados: PENDING -> GENERATING -> VALIDATING -> APPROVED -> FROZEN.
  - Resolucion por ID, no por ruta.

Uso:
  python asset_registry.py --validate
  python asset_registry.py --resolve HAND_L_PALM_FRONT_EDITORIAL_V001
  python asset_registry.py --set-status ID APPROVED
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2]
ASSETS_ROOT = (SCRIPT_DIR / "assets").resolve()
REGISTRY = SCRIPT_DIR / "assets" / "v7" / "registry" / "assets.jsonl"

STATES = ["PENDING", "GENERATING", "VALIDATING", "APPROVED", "FROZEN"]
_ORDER = {s: i for i, s in enumerate(STATES)}
_BAD = re.compile(r"(\.\./|\.\.\\|^[A-Za-z]:[\\/]|^\\\\|^https?://)", re.I)


class RegistryError(Exception):
    pass


def load_registry(path: Path = REGISTRY) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            raise RegistryError(f"linea {i}: JSON invalido: {e}")
        row["_line"] = i
        rows.append(row)
    return rows


def _check_rel(rel: str):
    if _BAD.search(rel):
        raise RegistryError(f"ruta prohibida: {rel}")


def resolve_asset(asset_id: str, path: Path = REGISTRY) -> Path:
    """Traduce asset_id -> ruta absoluta validada dentro de assets/."""
    if _BAD.search(asset_id):
        raise RegistryError(f"asset_id prohibido: {asset_id}")
    for row in load_registry(path):
        if row.get("asset_id") == asset_id:
            _check_rel(row["file"])
            p = (SCRIPT_DIR / row["file"]).resolve()
            if ASSETS_ROOT not in p.parents and p != ASSETS_ROOT:
                raise RegistryError(f"fuera de assets/: {p}")
            return p
    raise RegistryError(f"asset_id no registrado: {asset_id}")


def validate(path: Path = REGISTRY) -> dict:
    """Valida registro + detecta huerfanos en disco."""
    errors = []
    registered = set()
    try:
        rows = load_registry(path)
    except RegistryError as e:
        return {"passed": False, "errors": [[0, str(e)]], "orphans": []}
    for row in rows:
        ln = row.get("_line")
        rel = row.get("file", "")
        if _BAD.search(rel):
            errors.append([ln, "path traversal"])
            continue
        p = (SCRIPT_DIR / rel)
        rp = p.resolve()
        if ASSETS_ROOT not in rp.parents and rp != ASSETS_ROOT:
            errors.append([ln, "fuera de assets/"])
            continue
        if not p.exists():
            errors.append([ln, "missing file"])
        registered.add(str(rp))
        lic = row.get("license", {})
        if lic.get("commercial_use") != "YES" or lic.get("status") != "VERIFIED":
            errors.append([ln, "commercial license not verified"])
        st = row.get("status")
        if st not in STATES:
            errors.append([ln, f"estado invalido: {st}"])

    orphans = []
    for f in ASSETS_ROOT.rglob("*.svg"):
        if str(f.resolve()) not in registered:
            orphans.append(str(f.relative_to(SCRIPT_DIR)))
    return {"passed": not errors, "errors": errors, "orphans": sorted(orphans)}


def set_status(asset_id: str, status: str, path: Path = REGISTRY):
    if status not in STATES:
        raise RegistryError(f"estado invalido: {status}")
    rows = load_registry(path)
    found = False
    out = []
    for row in rows:
        row.pop("_line", None)
        if row.get("asset_id") == asset_id:
            row["status"] = status
            found = True
        out.append(row)
    if not found:
        raise RegistryError(f"asset_id no registrado: {asset_id}")
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n",
                    encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--resolve")
    ap.add_argument("--set-status", nargs=2, metavar=("ID", "STATUS"))
    a = ap.parse_args()
    if a.resolve:
        try:
            print(resolve_asset(a.resolve))
        except RegistryError as e:
            print(json.dumps({"error": str(e)}))
            raise SystemExit(1)
    if a.set_status:
        set_status(a.set_status[0], a.set_status[1])
        print(json.dumps({"ok": True, "asset": a.set_status[0],
                          "status": a.set_status[1]}))
    if a.validate or not (a.resolve or a.set_status):
        result = validate()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
