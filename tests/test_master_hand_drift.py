"""
Tests: master hand drift — verifica que la mano no haya cambiado entre versiones.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "v8"))

import hand_geometry as hg

EXPECTED_VIEWBOX = 2048
EXPECTED_FINGERS = ["index-finger", "middle-finger", "ring-finger", "little-finger"]
EXPECTED_LAYERS = ["hand-base", "natural-creases", "shading"]


def test_viewbox_stable():
    assert hg.VB == EXPECTED_VIEWBOX


def test_finger_names_stable():
    assert list(hg.FINGERS.keys()) == EXPECTED_FINGERS


def test_palm_center_stable():
    assert hg.PALM_CX == 1024
    assert hg.PALM_CY == 1180


def test_svg_has_required_layers():
    svg = hg.hand_svg("L")
    for layer in EXPECTED_LAYERS:
        assert f'id="{layer}"' in svg, f"Missing layer: {layer}"


if __name__ == "__main__":
    tests = [test_viewbox_stable, test_finger_names_stable,
             test_palm_center_stable, test_svg_has_required_layers]
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
