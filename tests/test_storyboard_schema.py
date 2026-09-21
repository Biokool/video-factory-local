"""
Tests: storyboard schema — verifica que el storyboard tenga la estructura correcta.
"""
import json
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent


def test_storyboard_structure():
    """Verificar que el storyboard tenga campos requeridos."""
    jobs_dir = PROJECT_DIR / "data" / "jobs"
    if not jobs_dir.exists():
        return
    sb_files = list(jobs_dir.rglob("storyboard.json"))
    if not sb_files:
        return
    for sb in sb_files[:2]:
        data = json.loads(sb.read_text(encoding="utf-8"))
        assert "scenes" in data or "blocks" in data, \
            f"{sb.name}: missing 'scenes' or 'blocks'"


def test_scene_fields():
    """Cada escena debe tener campos mínimos."""
    jobs_dir = PROJECT_DIR / "data" / "jobs"
    if not jobs_dir.exists():
        return
    for sb in list(jobs_dir.rglob("storyboard.json"))[:1]:
        data = json.loads(sb.read_text(encoding="utf-8"))
        scenes = data.get("scenes", data.get("blocks", []))
        for scene in scenes[:3]:
            if isinstance(scene, dict):
                assert "narration" in scene or "text" in scene or "id" in scene, \
                    f"Scene missing fields: {list(scene.keys())}"


if __name__ == "__main__":
    tests = [test_storyboard_structure, test_scene_fields]
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
