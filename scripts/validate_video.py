"""
Valida el video final contra el perfil especificado.
- Verifica resolución, fps, codec, duración
- Verifica existencia de audio
- Verifica que cumple rangos de duración del perfil
- Genera reporte de QA
"""
import sys
import os
import json
import argparse
import subprocess
import wave
from pathlib import Path
from datetime import datetime
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent.parent
PROFILES_PATH = SCRIPT_DIR / "config" / "video_profiles.yaml"
RULES_PATH = SCRIPT_DIR / "config" / "quality_rules.yaml"


def load_profiles() -> dict:
    with open(PROFILES_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["profiles"]


def load_rules() -> dict:
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_video_info(path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error",
        "-print_format", "json",
        "-show_streams", "-show_format",
        str(path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        return {"error": str(e)}
    return {}


def get_audio_peak_dbfs(path: Path) -> float:
    cmd = [
        "ffmpeg", "-i", str(path),
        "-af", "volumedetect",
        "-vn", "-f", "null", "-"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        stderr = result.stderr
        for line in stderr.split("\n"):
            if "max_volume" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "max_volume:":
                        return float(parts[i + 1].rstrip(" dB"))
    except Exception:
        pass
    return -99.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", default=str(SCRIPT_DIR / "data" / "renders" / "final.mp4"))
    parser.add_argument("--profile", default="test_30s")
    parser.add_argument("--job-dir", default=str(SCRIPT_DIR / "data" / "jobs" / "default"))
    args = parser.parse_args()

    video_path = Path(args.video)
    job_dir = Path(args.job_dir)

    profiles = load_profiles()
    rules = load_rules()
    profile = profiles.get(args.profile, {})
    thresholds = rules.get("qa_thresholds", {})

    report = {
        "video": str(video_path),
        "profile": args.profile,
        "checks": {},
        "warnings": [],
        "errors": [],
        "passed": True,
        "evaluated_at": datetime.now().isoformat(),
    }

    if not video_path.exists():
        report["errors"].append(f"Video no existe: {video_path}")
        report["passed"] = False
        write_report(report, job_dir)
        sys.exit(1)

    size = video_path.stat().st_size
    report["checks"]["file_exists"] = True
    report["checks"]["file_size_bytes"] = size
    if size < thresholds.get("min_file_size_bytes", 100000):
        report["warnings"].append(f"Archivo pequeño: {size} bytes")

    info = get_video_info(video_path)
    if "error" in info:
        report["errors"].append(f"ffprobe error: {info['error']}")
        report["passed"] = False
        write_report(report, job_dir)
        sys.exit(1)

    duration = float(info.get("format", {}).get("duration", 0))
    report["checks"]["duration_sec"] = duration

    if "streams" in info:
        video_streams = [s for s in info["streams"] if s.get("codec_type") == "video"]
        audio_streams = [s for s in info["streams"] if s.get("codec_type") == "audio"]

        if video_streams:
            vs = video_streams[0]
            report["checks"]["video"] = {
                "codec": vs.get("codec_name"),
                "width": vs.get("width"),
                "height": vs.get("height"),
                "fps": vs.get("r_frame_rate"),
            }
            if vs.get("width") != profile.get("width") or vs.get("height") != profile.get("height"):
                report["warnings"].append(
                    f"Resolución {vs.get('width')}x{vs.get('height')} no coincide con perfil {profile.get('width')}x{profile.get('height')}"
                )
        else:
            report["errors"].append("No se encontró stream de video")
            report["passed"] = False

        if audio_streams:
            aus = audio_streams[0]
            report["checks"]["audio"] = {
                "codec": aus.get("codec_name"),
                "sample_rate": aus.get("sample_rate"),
                "channels": aus.get("channels"),
            }
        else:
            report["errors"].append("No se encontró stream de audio")
            report["passed"] = False

    target_range = profile.get("target_duration_range")
    if target_range:
        lo, hi = target_range
        if duration < lo or duration > hi:
            if args.profile == "test_30s":
                report["warnings"].append(f"Duración {duration:.1f}s fuera del rango de prueba {lo}-{hi}s")
            else:
                if duration < lo - 10 or duration > hi + 10:
                    report["errors"].append(f"Duración {duration:.1f}s fuera del rango {lo}-{hi}s")
                    report["passed"] = False
                else:
                    report["warnings"].append(f"Duración {duration:.1f}s cerca del límite {lo}-{hi}s")

    audio_files = list((SCRIPT_DIR / "data" / "audio").glob("scene_*.wav"))
    if audio_files:
        first_audio = audio_files[0]
        peak = get_audio_peak_dbfs(first_audio)
        report["checks"]["audio_peak_dbfs"] = peak
        max_peak = thresholds.get("max_audio_peak_dbfs", -0.5)
        if peak > max_peak:
            report["warnings"].append(f"Audio pico {peak} dBFS excede el máximo {max_peak} dBFS")

    expected_assets = ["images", "audio", "subtitles", "scenes"]
    for folder in expected_assets:
        folder_path = SCRIPT_DIR / "data" / folder
        if folder_path.exists():
            count = len(list(folder_path.iterdir()))
            report["checks"][f"{folder}_count"] = count

    print(json.dumps(report, indent=2, ensure_ascii=False))
    write_report(report, job_dir)
    sys.exit(0 if report["passed"] else 1)


def write_report(report, job_dir):
    qa_path = Path(job_dir) / "qa.json"
    qa_path.parent.mkdir(parents=True, exist_ok=True)
    qa_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    status = "PASS" if report["passed"] else "FAIL"
    print(f"\n[{status}] Reporte guardado en {qa_path}")


if __name__ == "__main__":
    main()
