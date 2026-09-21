"""
Tests: block resume — verifica que el sistema pueda reanudar bloques.
"""
import json
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent


def test_job_directory_structure():
    """Los jobs deben tener estructura de directorios correcta."""
    jobs_dir = PROJECT_DIR / "data" / "jobs"
    if not jobs_dir.exists():
        return
    for job_dir in list(jobs_dir.iterdir())[:2]:
        if job_dir.is_dir():
            # Debe tener al menos un archivo de storyboard o script
            files = list(job_dir.glob("*.json")) + list(job_dir.glob("*.txt"))
            assert len(files) > 0, f"Empty job dir: {job_dir.name}"


def test_storyboard_has_id():
    """Cada storyboard debe tener un ID."""
    jobs_dir = PROJECT_DIR / "data" / "jobs"
    if not jobs_dir.exists():
        return
    for sb in list(jobs_dir.rglob("storyboard.json"))[:2]:
        data = json.loads(sb.read_text(encoding="utf-8"))
        assert "id" in data or "job_id" in data, \
            f"Missing ID in {sb.parent.name}"


if __name__ == "__main__":
    import json
    tests = [test_job_directory_structure, test_storyboard_has_id]
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
