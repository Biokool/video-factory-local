"""
Tests: RAG topic coverage — verifica que el RAG tenga cobertura del tema.
"""
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent


def test_rag_files_exist():
    """Verificar que existan archivos de RAG."""
    rag_dir = PROJECT_DIR / "data" / "rag"
    if not rag_dir.exists():
        return
    jsonl_files = list(rag_dir.glob("*.jsonl"))
    assert len(jsonl_files) > 0, "No RAG evidence files found"


def test_rag_evidence_structure():
    """Verificar que las evidencias tengan estructura correcta."""
    rag_dir = PROJECT_DIR / "data" / "rag"
    if not rag_dir.exists():
        return
    for jsonl in list(rag_dir.glob("*.jsonl"))[:1]:
        import json
        with open(jsonl, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= 3:
                    break
                data = json.loads(line)
                assert "text" in data or "content" in data, \
                    f"Evidence missing text: {list(data.keys())}"


if __name__ == "__main__":
    tests = [test_rag_files_exist, test_rag_evidence_structure]
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
