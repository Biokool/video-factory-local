"""
Security Audit — auditoría completa de seguridad del proyecto.
Cumple §20 del spec maestro.
"""
import json
import os
import re
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).resolve().parent.parent


def audit_gitignore() -> dict:
    """Verifica que .env y otros archivos sensibles estén en .gitignore."""
    gi_path = PROJECT_DIR / ".gitignore"
    required = [".env", "*.env.local", "__pycache__", "*.pyc"]
    missing = []
    if gi_path.exists():
        content = gi_path.read_text(encoding="utf-8")
        for r in required:
            if r not in content:
                missing.append(r)
    else:
        missing = required
    return {"status": "PASS" if not missing else "FAIL", "missing": missing}


def audit_secrets_exposed() -> dict:
    """Busca secretos en el código fuente."""
    patterns = [
        (re.compile(r'password\s*=\s*["\'][^"\']{8,}["\']'), "Password"),
        (re.compile(r'api_key\s*=\s*["\'][^"\']{8,}["\']'), "API Key"),
        (re.compile(r'secret\s*=\s*["\'][^"\']{8,}["\']'), "Secret"),
        (re.compile(r'token\s*=\s*["\'][^"\']{8,}["\']'), "Token"),
    ]
    found = []
    for py in (PROJECT_DIR / "scripts").rglob("*.py"):
        try:
            content = py.read_text(encoding="utf-8", errors="replace")
            for pattern, desc in patterns:
                for match in pattern.finditer(content):
                    found.append(f"{py.name}: {desc}")
        except Exception:
            pass
    return {"status": "PASS" if not found else "FAIL", "found": found[:10]}


def audit_env_file() -> dict:
    """Verifica que .env exista y no esté versionado."""
    env_path = PROJECT_DIR / ".env"
    gi_path = PROJECT_DIR / ".gitignore"
    issues = []
    if env_path.exists():
        gi_content = gi_path.read_text(encoding="utf-8") if gi_path.exists() else ""
        if ".env" not in gi_content:
            issues.append(".env no está en .gitignore")
    return {"status": "PASS" if not issues else "WARN", "issues": issues}


def audit_localhost_only() -> dict:
    """Verifica que los servidores solo escuchen en localhost."""
    issues = []
    for py in (PROJECT_DIR / "scripts").rglob("*.py"):
        try:
            content = py.read_text(encoding="utf-8", errors="replace")
            if "0.0.0.0" in content:
                issues.append(f"{py.name}: bind a 0.0.0.0 (público)")
            if "127.0.0.1" not in content and "localhost" not in content:
                if "HTTPServer" in content or "serve" in content:
                    issues.append(f"{py.name}: posiblemente no localhost")
        except Exception:
            pass
    return {"status": "PASS" if not issues else "WARN", "issues": issues}


def audit_svg_safety() -> dict:
    """Verifica que los SVGs no tengan scripts."""
    issues = []
    for svg in (PROJECT_DIR / "assets").rglob("*.svg"):
        try:
            content = svg.read_text(encoding="utf-8", errors="replace")
            if "<script" in content.lower():
                issues.append(f"{svg.name}: contiene <script>")
            if "onclick" in content.lower():
                issues.append(f"{svg.name}: contiene onclick")
            if "foreignObject" in content:
                issues.append(f"{svg.name}: contiene foreignObject")
        except Exception:
            pass
    return {"status": "PASS" if not issues else "FAIL", "issues": issues}


def run_full_audit() -> dict:
    results = {
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "gitignore": audit_gitignore(),
            "secrets": audit_secrets_exposed(),
            "env_file": audit_env_file(),
            "localhost": audit_localhost_only(),
            "svg_safety": audit_svg_safety(),
        },
    }
    all_pass = all(c["status"] in ("PASS", "WARN") for c in results["checks"].values())
    results["overall"] = "PASS" if all_pass else "FAIL"
    results["gates"] = {"gate_0_security": results["overall"] == "PASS"}
    return results


if __name__ == "__main__":
    result = run_full_audit()
    out_path = PROJECT_DIR / "data" / "qa" / "security_audit.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
