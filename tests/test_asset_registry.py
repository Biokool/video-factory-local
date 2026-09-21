"""
Tests: asset registry — verifica integridad del registro V8.
"""
import json
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent


def test_svg_registry_exists():
    reg_path = PROJECT_DIR / "assets" / "v8" / "svg" / "svg_library.json"
    assert reg_path.exists(), "SVG registry not found"


def test_svg_registry_count():
    reg_path = PROJECT_DIR / "assets" / "v8" / "svg" / "svg_library.json"
    if not reg_path.exists():
        return
    registry = json.loads(reg_path.read_text(encoding="utf-8"))
    assert len(registry) >= 40, f"Expected >= 40 assets, got {len(registry)}"


def test_all_files_exist():
    reg_path = PROJECT_DIR / "assets" / "v8" / "svg" / "svg_library.json"
    if not reg_path.exists():
        return
    registry = json.loads(reg_path.read_text(encoding="utf-8"))
    missing = []
    for entry in registry:
        fpath = PROJECT_DIR / entry["file"]
        if not fpath.exists():
            missing.append(entry["file"])
    assert not missing, f"Missing files: {missing[:5]}"


if __name__ == "__main__":
    tests = [test_svg_registry_exists, test_svg_registry_count, test_all_files_exist]
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
