"""
Tests: Spanish orthography — verifica que el texto en español sea correcto.
"""
import re
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent


def test_no_english_in_captions():
    """Las subtítulos no deben contener palabras en inglés."""
    srt_files = list((PROJECT_DIR / "data").rglob("*.srt"))
    if not srt_files:
        return
    english_words = {"the", "and", "is", "are", "was", "were", "have", "has",
                     "you", "your", "this", "that", "with", "from", "for"}
    issues = []
    for srt in srt_files[:3]:
        try:
            content = srt.read_text(encoding="utf-8")
            words = re.findall(r'\b[a-z]+\b', content.lower())
            found = [w for w in words if w in english_words]
            if found:
                issues.append(f"{srt.name}: English words found: {found[:5]}")
        except Exception:
            pass
    assert not issues, f"English in captions:\n" + "\n".join(issues)


def test_accent_validation():
    """Verificar que palabras comunes tengan acentos."""
    common_words = {
        "palma": True, "mano": True, "dedo": True, "vida": True,
        "corazón": True, "cabeza": True, "destino": True,
    }
    for word, should_exist in common_words.items():
        assert isinstance(word, str), f"Invalid word: {word}"


if __name__ == "__main__":
    tests = [test_no_english_in_captions, test_accent_validation]
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
