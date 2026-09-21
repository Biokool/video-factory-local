"""
Tests: hand left/right — verifica que ambas manos se generen correctamente.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "v8"))

import hand_geometry as hg


def test_left_hand_svg():
    svg = hg.hand_svg("L")
    assert 'id="HAND_L_PALM_FRONT_V001"' in svg
    assert 'viewBox="0 0 2048 2048"' in svg


def test_right_hand_svg():
    svg = hg.hand_svg("R")
    assert 'id="HAND_R_PALM_FRONT_V001"' in svg
    assert "scale(-1,1)" in svg


def test_both_hands_have_7_segments():
    for side in ["L", "R"]:
        svg = hg.hand_svg(side)
        ids = ["palm-silhouette", "thumb", "index-finger", "middle-finger",
               "ring-finger", "little-finger", "wrist"]
        for fid in ids:
            assert f'id="{fid}"' in svg, f"Missing {fid} in hand {side}"


def test_no_mounts_in_hand():
    svg = hg.hand_svg("L")
    for mount in ["jupiter", "saturn", "venus", "mercury", "luna"]:
        assert mount.lower() not in svg.lower(), f"Mount {mount} in hand SVG"


if __name__ == "__main__":
    tests = [test_left_hand_svg, test_right_hand_svg,
             test_both_hands_have_7_segments, test_no_mounts_in_hand]
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
