"""
Genera una versión short (9:16) a partir del video 16:9.
Recorta el segmento más fuerte (30-60s) y lo reformatea a 1080x1920.
"""
import sys
import os
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--start", type=float, default=0.0)
    parser.add_argument("--duration", type=float, default=30.0)
    args = parser.parse_args()

    video_path = Path(args.video)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not video_path.exists():
        print(f"ERROR: video no existe: {video_path}")
        sys.exit(1)

    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:1"

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(args.start),
        "-i", str(video_path),
        "-t", str(args.duration),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-c:a", "aac",
        "-ar", "48000",
        "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path)
    ]

    print(f"Generando short desde {video_path}...")
    print(f"  Inicio: {args.start}s, Duración: {args.duration}s")
    print(f"  Salida: {output_path}")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"ERROR: {r.stderr[:1000]}")
        sys.exit(1)

    size = output_path.stat().st_size
    print(f"Short generado: {output_path} ({size:,} bytes)")

    meta = {
        "source": str(video_path),
        "output": str(output_path),
        "start_sec": args.start,
        "duration_sec": args.duration,
        "size_bytes": size,
        "created_at": datetime.now().isoformat()
    }
    meta_path = output_path.parent / (output_path.stem + ".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
