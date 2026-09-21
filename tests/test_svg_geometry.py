"""
Tests: SVG geometry — verifica viewBox, IDs, y estructura de assets SVG.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "v8"))

import hand_geometry as hg


def test_viewbox_2048():
    svg = hg.hand_svg("L")
    assert 'viewBox="0 0 2048 2048"' in svg


def test_no_text_in_hand():
    svg = hg.hand_svg("L")
    assert "<text" not in svg


def test_no_external_urls():
    svg = hg.hand_svg("L")
    # Exclude XML namespace
    svg_no_ns = svg.replace("http://www.w3.org/2000/svg", "")
    assert "http://" not in svg_no_ns
    assert "https://" not in svg_no_ns


def test_layer_structure():
    svg = hg.hand_svg("L")
    assert 'id="hand-base"' in svg
    assert 'id="natural-creases"' in svg
    assert 'id="shading"' in svg


def test_svg_library_viewbox():
    svg_path = Path(__file__).resolve().parent.parent / "assets" / "v8" / "svg"
    if not svg_path.exists():
        return
    for svg_file in list(svg_path.glob("*.svg"))[:5]:
        content = svg_file.read_text(encoding="utf-8")
        assert "viewBox" in content, f"No viewBox in {svg_file.name}"


if __name__ == "__main__":
    tests = [test_viewbox_2048, test_no_text_in_hand, test_no_external_urls,
             test_layer_structure, test_svg_library_viewbox]
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
