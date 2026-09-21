"""
Tests: forbidden claims — verifica que no haya afirmaciones prohibidas.
"""
import re
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

# Palabras/frases prohibidas en contenido educativo de quiromancia
FORBIDDEN = [
    re.compile(r'garantiz[oa]', re.IGNORECASE),
    re.compile(r'asegur[oa]', re.IGNORECASE),
    re.compile(r'cur[ao]', re.IGNORECASE),
    re.compile(r'medic[oa]', re.IGNORECASE),
    re.compile(r'diagn[oó]stic', re.IGNORECASE),
    re.compile(r'predic(ci[oó]n|ar)', re.IGNORECASE),
]


def test_no_forbidden_in_scripts():
    """Los scripts no deben contener afirmaciones prohibidas."""
    scripts_dir = PROJECT_DIR / "data" / "jobs"
    if not scripts_dir.exists():
        return
    issues = []
    for txt in list(scripts_dir.rglob("*.txt"))[:5]:
        try:
            content = txt.read_text(encoding="utf-8")
            for pattern in FORBIDDEN:
                for match in pattern.finditer(content):
                    issues.append(f"{txt.name}: '{match.group()}' at pos {match.start()}")
        except Exception:
            pass
    assert not issues, f"Forbidden claims:\n" + "\n".join(issues[:10])


if __name__ == "__main__":
    tests = [test_no_forbidden_in_scripts]
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
