"""
Validate Asset Registry — verifica integridad del registro de assets §9.
"""
import json
import hashlib
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
REGISTRY_V8 = PROJECT_DIR / "assets" / "v8" / "svg" / "svg_library.json"
HANDS_DIR = PROJECT_DIR / "assets" / "v8" / "hands"


def validate():
    issues = []

    # Check V8 SVG registry
    if not REGISTRY_V8.exists():
        issues.append(f"V8 registry not found: {REGISTRY_V8}")
    else:
        registry = json.loads(REGISTRY_V8.read_text(encoding="utf-8"))
        for entry in registry:
            fpath = PROJECT_DIR / entry["file"]
            if not fpath.exists():
                issues.append(f"Missing file: {entry['file']}")
            elif entry.get("sha256"):
                actual = hashlib.sha256(fpath.read_bytes()).hexdigest()
                if actual != entry["sha256"]:
                    issues.append(f"SHA256 mismatch: {entry['asset_id']}")

    # Check hand assets
    for hand_file in ["mano_izquierda_solid.png", "mano_derecha_solid.png"]:
        fpath = HANDS_DIR / hand_file
        if not fpath.exists():
            issues.append(f"Missing hand: {hand_file}")

    return issues


if __name__ == "__main__":
    issues = validate()
    if issues:
        print(f"FAIL: {len(issues)} issues")
        for i in issues[:20]:
            print(f"  - {i}")
        sys.exit(1)
    else:
        print("PASS: Asset registry valid")
        sys.exit(0)
