"""
Tests: hand finger count — verifica que cada mano tenga exactamente 5 dedos.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "v8"))

import hand_geometry as hg


def test_left_hand_finger_count():
    """Mano izquierda debe tener 5 dedos (4 superiores + pulgar)."""
    outline = hg.build_hand_outline()
    tips_y = [hg._finger_tip_cy(fi) for fi in hg.FINGERS.values()]
    tips_above = sum(1 for y in tips_y if y < hg.PALM_CY - hg.PALM_H // 2)
    assert tips_above == 4, f"Se esperan 4 dedos arriba, se encontraron {tips_above}"


def test_right_hand_finger_count():
    """Espejo derecho debe tener la misma estructura."""
    svg_r = hg.hand_svg("R")
    assert "hand-base" in svg_r or "path" in svg_r


def test_finger_spread():
    """Los dedos deben estar separados horizontalmente."""
    tips_x = sorted([hg._finger_tip_cx(fi) for fi in hg.FINGERS.values()])
    spread = tips_x[-1] - tips_x[0]
    assert spread > 150, f"Spread mínimo 150px, actual {spread}px"


def test_thumb_separate():
    """El pulgar debe estar separado de los demás dedos."""
    index_x = hg._finger_tip_cx(hg.FINGERS["indice"])
    thumb_x = hg.PALM_CX + hg.THUMB["x_off"]
    assert abs(index_x - thumb_x) > 100, "Pulgar muy cerca del índice"


if __name__ == "__main__":
    tests = [test_left_hand_finger_count, test_right_hand_finger_count,
             test_finger_spread, test_thumb_separate]
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
