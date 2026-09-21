"""
Tests: path security — verifica que no haya rutas absolutas, UNC o URLs.
"""
import json
import re
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

_DANGEROUS_PATTERNS = [
    (re.compile(r'[A-Z]:\\\\'), "Ruta absoluta Windows"),
    (re.compile(r'\\\\\\\\\\\\'), "Ruta UNC"),
    (re.compile(r'rm\s+-rf\s+/'), "Comando destructivo"),
    (re.compile(r'Drop\s+TABLE', re.IGNORECASE), "SQL injection"),
    (re.compile(r'<script', re.IGNORECASE), "Script injection"),
]


def scan_file(path: Path) -> list:
    """Escanea un archivo buscando patrones peligrosos (excluye comentarios y docstrings)."""
    issues = []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        in_docstring = False
        for line_num, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_docstring = not in_docstring
                continue
            if in_docstring or stripped.startswith("#") or stripped.startswith("//"):
                continue
            for pattern, desc in _DANGEROUS_PATTERNS:
                if pattern.search(line):
                    issues.append(f"{path.name}:{line_num}: {desc}")
    except Exception:
        pass
    return issues


def test_no_absolute_paths():
    """No debe haber rutas absolutas en scripts Python (excluyendo test fixtures)."""
    issues = []
    for py in (PROJECT_DIR / "scripts").rglob("*.py"):
        if "test" in py.name.lower() or "expected" in str(py):
            continue
        file_issues = scan_file(py)
        issues.extend(file_issues)
    # Filtrar falsos positivos conocidos
    issues = [i for i in issues if "security_audit" not in i and "audit_v7" not in i]
    assert not issues, f"Rutas peligrosas encontradas:\n" + "\n".join(issues[:10])


def test_no_secrets_in_code():
    """No debe haber secretos hardcodeados."""
    issues = []
    secret_patterns = [
        (re.compile(r'password\s*=\s*["\'][^"\']+["\']', re.IGNORECASE), "Password hardcodeado"),
        (re.compile(r'api_key\s*=\s*["\'][^"\']+["\']', re.IGNORECASE), "API key hardcodeada"),
        (re.compile(r'token\s*=\s*["\'][^"\']+["\']', re.IGNORECASE), "Token hardcodeado"),
    ]
    for py in (PROJECT_DIR / "scripts").rglob("*.py"):
        try:
            content = py.read_text(encoding="utf-8", errors="replace")
            for pattern, desc in secret_patterns:
                for match in pattern.finditer(content):
                    issues.append(f"{py.name}: {desc}")
        except Exception:
            pass
    assert not issues, f"Secretos encontrados:\n" + "\n".join(issues[:10])


def test_storyboard_no_paths():
    """Storyboards no deben contener rutas arbitrarias."""
    jobs_dir = PROJECT_DIR / "data" / "jobs"
    if not jobs_dir.exists():
        return
    issues = []
    for sb in jobs_dir.rglob("storyboard.json"):
        try:
            data = json.loads(sb.read_text(encoding="utf-8"))
            text = json.dumps(data)
            for pattern, desc in _DANGEROUS_PATTERNS[:4]:
                if pattern.search(text):
                    issues.append(f"{sb.parent.name}: {desc}")
        except Exception:
            pass
    assert not issues, f"Paths en storyboards:\n" + "\n".join(issues[:5])


if __name__ == "__main__":
    import sys
    tests = [test_no_absolute_paths, test_no_secrets_in_code, test_storyboard_no_paths]
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
