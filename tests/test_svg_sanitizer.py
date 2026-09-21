"""
Tests: SVG sanitizer — verifica que el sanitizer elimina elementos peligrosos.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "v8"))

from svg_sanitizer import sanitize_svg, validate_svg_structure


def test_removes_script_tags():
    svg = '<svg><script>alert("xss")</script><circle r="10"/></svg>'
    cleaned, threats = sanitize_svg(svg)
    assert "<script" not in cleaned
    assert any("script" in t.lower() for t in threats)


def test_removes_foreign_object():
    svg = '<svg><foreignObject><div>evil</div></foreignObject></svg>'
    cleaned, threats = sanitize_svg(svg)
    assert "foreignObject" not in cleaned


def test_removes_event_handlers():
    svg = '<svg><circle onclick="evil()" onload="evil()"/></svg>'
    cleaned, threats = sanitize_svg(svg)
    assert "onclick" not in cleaned
    assert "onload" not in cleaned


def test_removes_external_urls():
    svg = '<svg><circle style="url(https://evil.com/x)"/></svg>'
    cleaned, threats = sanitize_svg(svg)
    assert "https://" not in cleaned


def test_preserves_clean_svg():
    svg = '<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="blue"/></svg>'
    cleaned, threats = sanitize_svg(svg)
    assert cleaned == svg
    assert len(threats) == 0


def test_validate_structure_2048():
    svg = '<svg viewBox="0 0 2048 2048"><g id="hand-base"><path id="palm-silhouette"/><path id="thumb"/><path id="index-finger"/><path id="middle-finger"/><path id="ring-finger"/><path id="little-finger"/><path id="wrist"/></g></svg>'
    result = validate_svg_structure(svg)
    assert result["valid"], f"Issues: {result['issues']}"


def test_validate_structure_wrong_viewbox():
    svg = '<svg viewBox="0 0 1024 1024"><g id="hand-base"><path id="palm-silhouette"/><path id="thumb"/><path id="index-finger"/><path id="middle-finger"/><path id="ring-finger"/><path id="little-finger"/><path id="wrist"/></g></svg>'
    result = validate_svg_structure(svg)
    assert not result["valid"]
    assert any("viewBox" in i for i in result["issues"])


if __name__ == "__main__":
    tests = [test_removes_script_tags, test_removes_foreign_object,
             test_removes_event_handlers, test_removes_external_urls,
             test_preserves_clean_svg, test_validate_structure_2048,
             test_validate_structure_wrong_viewbox]
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
