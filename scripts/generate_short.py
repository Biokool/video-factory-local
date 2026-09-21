"""
Genera una versión short (9:16) a partir del video 16:9.

Carga el perfil de audio/video desde config/video_profiles.yaml para no
cambiar silenciosamente la cadena que ya consiguió audio audible
(aac 44100 Hz estéreo 192k), corrigiendo el bug de 48000 Hz mono.
"""
import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent.parent
PROFILES_PATH = SCRIPT_DIR / "config" / "video_profiles.yaml"


def load_profile(name="short"):
    import yaml
    data = yaml.safe_load(PROFILES_PATH.read_text(encoding="utf-8"))
    profiles = data.get("profiles", {})
    if name not in profiles:
        return {}
    return profiles[name]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--start", type=float, default=0.0)
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--profile", default="short")
    args = parser.parse_args()

    profile = load_profile(args.profile)
    width = profile.get("width", 1080)
    height = profile.get("height", 1920)
    fps = profile.get("fps", 30)
    acodec = profile.get("audio_codec", "aac")
    ar = profile.get("audio_samplerate", 44100)
    ab = profile.get("audio_bitrate", "192k")
    channels = 2

    video_path = Path(args.video)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not video_path.exists():
        print(f"ERROR: video no existe: {video_path}")
        sys.exit(1)

    # Encuadre 9:16 sin cortar el sujeto: fondo desenfocado + video centrado.
    W, H = width, height
    fc = (
        f"[0:v]split=2[bg][fg];"
        f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},boxblur=30:2,eq=brightness=-0.08[bgb];"
        f"[fg]scale={W}:{H}:force_original_aspect_ratio=decrease[fgs];"
        f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2:shortest=1[v]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(args.start),
        "-i", str(video_path),
        "-t", str(args.duration),
        "-filter_complex", fc,
        "-map", "[v]", "-map", "0:a:0?",
        "-r", str(fps),
        "-c:v", profile.get("video_codec", "libx264"),
        "-preset", profile.get("preset", "fast"),
        "-crf", str(profile.get("crf", 22)),
        "-c:a", acodec,
        "-ar", str(ar),
        "-ac", str(channels),
        "-b:a", ab,
        "-pix_fmt", profile.get("pix_fmt", "yuv420p"),
        "-movflags", "+faststart",
        str(output_path)
    ]

    print(f"Generando short desde {video_path}...")
    print(f"  Inicio: {args.start}s, Duración: {args.duration}s")
    print(f"  Audio: {acodec} {ar}Hz {channels}ch {ab}")
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
        "profile": args.profile,
        "audio": {"codec": acodec, "samplerate": ar, "channels": channels,
                  "bitrate": ab},
        "size_bytes": size,
        "created_at": datetime.now().isoformat()
    }
    meta_path = output_path.parent / (output_path.stem + ".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
