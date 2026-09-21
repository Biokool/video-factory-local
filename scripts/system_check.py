"""
System Check — verifica entorno de ejecución (§2 del spec maestro).
Genera environment.json con hardware, software y dependencias.
"""
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent


def check_gpu() -> dict:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=8,
        )
        if out.returncode == 0 and out.stdout.strip():
            parts = [p.strip() for p in out.stdout.strip().split(",")]
            return {
                "status": "OK",
                "name": parts[0],
                "vram_mb": int(parts[1]) if len(parts) > 1 else 0,
                "driver": parts[2] if len(parts) > 2 else "unknown",
            }
    except Exception:
        pass
    return {"status": "NOT_FOUND"}


def check_ffmpeg() -> dict:
    try:
        out = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=8)
        if out.returncode == 0:
            version_line = out.stdout.split("\n")[0]
            return {"status": "OK", "version": version_line[:80]}
    except Exception:
        pass
    return {"status": "NOT_FOUND"}


def check_ollama() -> dict:
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:11434/api/version", timeout=4) as r:
            data = json.loads(r.read())
            return {"status": "OK", "version": data.get("version", "?"), "backend": "cpu"}
    except Exception:
        pass
    return {"status": "NOT_FOUND"}


def check_voicestudio() -> dict:
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:3900/.well-known/voicestudio-speech", timeout=4) as r:
            data = json.loads(r.read())
            return {"status": "OK", "version": data.get("service_version", "?")}
    except Exception:
        pass
    return {"status": "NOT_FOUND"}


def check_python() -> dict:
    return {
        "status": "OK",
        "version": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
    }


def check_disk() -> dict:
    try:
        import shutil
        usage = shutil.disk_usage(str(PROJECT_DIR))
        free_gb = usage.free / (1024 ** 3)
        return {"status": "OK", "free_gb": round(free_gb, 1)}
    except Exception:
        return {"status": "UNKNOWN"}


def run_check() -> dict:
    gpu = check_gpu()
    return {
        "timestamp": datetime.now().isoformat(),
        "python": check_python(),
        "ffmpeg": check_ffmpeg(),
        "ollama": check_ollama(),
        "voicestudio": check_voicestudio(),
        "gpu": gpu,
        "disk": check_disk(),
        "profile": {
            "id": "LEGACY_PASCAL_4GB" if gpu.get("vram_mb", 0) <= 4096 else "UNKNOWN",
            "gpu_vram_gb": round(gpu.get("vram_mb", 0) / 1024, 1),
            "ollama_backend": "cpu",
            "max_gpu_heavy_processes": 1,
            "image_generation_required": False,
        },
        "gates": {
            "gate_1_environment": all(
                s.get("status") == "OK"
                for s in [check_python(), check_ffmpeg(), gpu]
            ),
        },
    }


if __name__ == "__main__":
    result = run_check()
    out_path = PROJECT_DIR / "data" / "environment.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
