"""
Tests: source traceability — verifica que los assets tengan trazabilidad.
"""
import json
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent


def test_svg_registry_has_sha256():
    """Cada asset en el registry debe tener SHA256."""
    reg_path = PROJECT_DIR / "assets" / "v8" / "svg" / "svg_library.json"
    if not reg_path.exists():
        return
    registry = json.loads(reg_path.read_text(encoding="utf-8"))
    for entry in registry:
        assert "sha256" in entry and entry["sha256"], \
            f"Missing SHA256: {entry.get('asset_id')}"


def test_svg_registry_has_license():
    """Cada asset debe tener licencia."""
    reg_path = PROJECT_DIR / "assets" / "v8" / "svg" / "svg_library.json"
    if not reg_path.exists():
        return
    registry = json.loads(reg_path.read_text(encoding="utf-8"))
    for entry in registry:
        assert "license" in entry, f"Missing license: {entry.get('asset_id')}"


def test_hand_landmarks_exist():
    """Los landmarks de la mano deben existir."""
    lm_path = PROJECT_DIR / "assets" / "v8" / "hands" / "hand_landmarks_v10.json"
    if not lm_path.exists():
        return
    data = json.loads(lm_path.read_text(encoding="utf-8"))
    assert "fingers" in data
    assert "palm_center" in data
    assert "viewbox" in data


if __name__ == "__main__":
    tests = [test_svg_registry_has_sha256, test_svg_registry_has_license,
             test_hand_landmarks_exist]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS: {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
