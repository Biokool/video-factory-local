"""
Tests: offline render — verifica que el renderizado sin GPU funcione.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "v8"))

import hand_geometry as hg


def test_hand_renders_without_gpu():
    """La mano debe poder renderizarse sin GPU."""
    svg = hg.hand_svg("L")
    assert len(svg) > 1000, "SVG too short"
    assert svg.startswith("<?xml"), "Not valid XML"


def test_both_sides_render():
    """Ambas manos deben renderizarse."""
    for side in ["L", "R"]:
        svg = hg.hand_svg(side)
        assert len(svg) > 1000, f"Hand {side} too short"


if __name__ == "__main__":
    tests = [test_hand_renders_without_gpu, test_both_sides_render]
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
