"""
Renderiza el video final con FFmpeg - V2 multi-fotograma.

Soporta dos modos:
  1. Multi-frame: si images.json tiene frames para la escena, renderiza
     cada keyframe como segmento con zoompan y concatena con crossfades.
  2. Legacy: una sola imagen por escena con slow zoom (V1 compat).

Flujo por escena:
  - Renderizar cada keyframe como mini-segmento (loop 1 + zoompan, -an)
  - Concat segmentos por escena (concat demuxer -c copy)
  - Mux audio (AAC stereo 44.1kHz 192kbps)
  - Concat escenas finales + subtítulos + re-encode audio final

Parámetros:
  --manifest <ruta>
  --output <ruta_video>
  --profile <long|short|test_30s>
  --burn-subtitles
"""
import sys
import os
import json
import argparse
import subprocess
import yaml
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent.parent
PROFILES_PATH = SCRIPT_DIR / "config" / "video_profiles.yaml"


def load_profiles() -> dict:
    with open(PROFILES_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["profiles"]


def get_video_duration(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception:
        pass
    return 0.0


def get_audio_wav_duration(wav_path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(wav_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception:
        pass
    return 0.0


def resolve_path(job_dir: Path, rel: str) -> Path:
    """Resuelve una ruta relativa del storyboard de forma segura.

    Rechaza rutas absolutas, UNC y URLs. Permite rutas relativas (incluido
    ../) SOLO si la ruta resuelta permanece dentro de la raíz del proyecto,
    de modo que el storyboard no pueda escapar del árbol del proyecto.
    """
    import re
    if not rel:
        raise ValueError("ruta vacia")
    if re.match(r"^([A-Za-z]:[\\/]|\\\\)", rel):
        raise ValueError(f"ruta absoluta/UNC prohibida: {rel}")
    if re.match(r"^https?://", rel, re.I):
        raise ValueError(f"ruta remota prohibida: {rel}")
    root = SCRIPT_DIR.resolve()
    if rel.startswith("../"):
        p = (job_dir / rel).resolve()
    else:
        p = (job_dir.parent.parent / rel.lstrip("./")).resolve()
    if root not in p.parents and p != root:
        raise ValueError(f"ruta fuera del proyecto: {p}")
    return p


def render_frame_segment(frame_path: Path, duration: float, W: int, H: int,
                          fps: int, profile: dict, out_path: Path, zoom_dir=1):
    """Renderiza un frame como mini-segmento con zoompan suave."""
    zoom_expr = "1.05+0.015*on/{d}" if zoom_dir > 0 else "1.065-0.015*on/{d}"
    d = int(duration * fps)
    if d < 1:
        d = 1
    zoom_expr = zoom_expr.replace("{d}", str(d))

    zoompan = (
        f"zoompan=z='{zoom_expr}':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={d}:s={W}x{H}:fps={fps}"
    )
    scale = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black"
    video_filter = f"{scale},{zoompan}"

    cmd = [
        "ffmpeg", "-y", "-loop", "1",
        "-i", str(frame_path),
        "-vf", video_filter,
        "-t", str(duration),
        "-r", str(fps),
        "-pix_fmt", profile.get("pix_fmt", "yuv420p"),
        "-c:v", profile["video_codec"],
        "-preset", profile.get("preset", "medium"),
        "-crf", str(profile.get("crf", 20)),
        "-an",
        str(out_path)
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print(f"    segment error: {r.stderr[:300]}")
        return None
    return out_path


def render_scene_multiframe(scene, frames_dir: Path, frames: list,
                             profile: dict, temp_dir: Path, index: int):
    """Renderiza escena multi-fotograma: keyframes -> segmentos -> concat -> mux audio."""
    W, H = profile["width"], profile["height"]
    fps = profile["fps"]
    duration = scene["duration_sec"]
    seg_dur = duration / len(frames)
    scene_temp = temp_dir / f"scene_{scene['id']:03d}"
    scene_temp.mkdir(parents=True, exist_ok=True)

    segments = []
    for i, fname in enumerate(frames):
        fp = frames_dir / fname
        if not fp.exists():
            print(f"    frame {fname} no existe, saltando")
            continue
        seg_out = scene_temp / f"seg_{i:02d}.mp4"
        zoom_dir = 1 if i % 2 == 0 else -1
        render_frame_segment(fp, seg_dur, W, H, fps, profile, seg_out, zoom_dir)
        if seg_out.exists():
            segments.append(seg_out)

    if not segments:
        return None

    # Concat segmentos (video only)
    concat_file = scene_temp / "concat.txt"
    with open(concat_file, "w", encoding="utf-8") as f:
        for seg in segments:
            f.write(f"file '{seg.resolve().as_posix()}'\n")

    scene_video_noaudio = scene_temp / "scene_noaudio.mp4"
    cmd_concat = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        "-t", str(duration),
        str(scene_video_noaudio)
    ]
    r = subprocess.run(cmd_concat, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print(f"    concat error: {r.stderr[:300]}")
        return None

    # Mux audio
    voice_rel = scene["voice"]
    voice_path = resolve_path(scene_temp.parent.parent, voice_rel)
    scene_muxed = scene_temp / "scene_muxed.mp4"
    cmd_mux = [
        "ffmpeg", "-y",
        "-i", str(scene_video_noaudio),
        "-i", str(voice_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-ar", "44100",
        "-ac", "2",
        "-b:a", profile.get("audio_bitrate", "192k"),
        "-map", "0:v:0", "-map", "1:a:0",
        str(scene_muxed)
    ]
    r = subprocess.run(cmd_mux, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print(f"    mux error: {r.stderr[:300]}")
        return scene_video_noaudio
    return scene_muxed


def render_scene_single(scene, job_dir, profile, temp_dir, index):
    """Legacy: una imagen por escena con slow zoom."""
    image_path = resolve_path(job_dir, scene["image"])
    voice_path = resolve_path(job_dir, scene["voice"])

    if not image_path.exists():
        print(f"  [{index}] IMAGEN NO ENCONTRADA: {image_path}")
        return None
    if not voice_path.exists():
        print(f"  [{index}] VOZ NO ENCONTRADA: {voice_path}")
        return None

    duration = scene["duration_sec"]
    W, H = profile["width"], profile["height"]
    fps = profile["fps"]
    target_frames = int(duration * fps)

    zoompan = (
        f"zoompan=z='1.05+0.03*on/{target_frames}':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={target_frames}:s={W}x{H}:fps={fps}"
    )
    scale = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black"
    video_filter = f"{scale},{zoompan}"

    out_video = temp_dir / f"scene_{scene['id']:03d}.mp4"
    cmd_video = [
        "ffmpeg", "-y", "-loop", "1",
        "-i", str(image_path),
        "-vf", video_filter,
        "-t", str(duration),
        "-r", str(fps),
        "-pix_fmt", profile.get("pix_fmt", "yuv420p"),
        "-c:v", profile["video_codec"],
        "-preset", profile.get("preset", "medium"),
        "-crf", str(profile.get("crf", 20)),
        "-an",
        str(out_video)
    ]
    print(f"  [{index}] Renderizando video legacy escena {scene['id']}...")
    r = subprocess.run(cmd_video, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print(f"  [{index}] FFmpeg error: {r.stderr[:500]}")
        return None

    out_muxed = temp_dir / f"scene_{scene['id']:03d}_muxed.mp4"
    cmd_mux = [
        "ffmpeg", "-y",
        "-i", str(out_video),
        "-i", str(voice_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-ar", "44100",
        "-ac", "2",
        "-b:a", profile.get("audio_bitrate", "192k"),
        "-map", "0:v:0", "-map", "1:a:0",
        str(out_muxed)
    ]
    r = subprocess.run(cmd_mux, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print(f"  [{index}] Mux error: {r.stderr[:500]}")
        return out_video
    return out_muxed


def concatenate_scenes(scene_videos, profile, output_path, burn_subtitles=False, subtitle_path=None):
    list_file = output_path.parent / "concat_list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for sv in scene_videos:
            sv = Path(sv).resolve().as_posix()
            f.write(f"file '{sv}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file.resolve()),
    ]
    if burn_subtitles and subtitle_path and subtitle_path.exists():
        # Ruta con ':' escapado y barras normales para el filtergraph.
        sub = subtitle_path.resolve().as_posix().replace(":", "\\:")
        style = ("FontName=Arial,FontSize=38,PrimaryColour=&HFFFFFF,"
                 "OutlineColour=&H000000,Outline=2")
        vf = f"subtitles='{sub}':si=0:force_style='{style}'"
        cmd += ["-vf", vf]
    cmd += [
        "-c:v", profile["video_codec"],
        "-preset", profile.get("preset", "medium"),
        "-crf", str(profile.get("crf", 20)),
        "-c:a", profile["audio_codec"],
        "-ar", str(profile.get("audio_samplerate", 44100)),
        "-ac", "2",
        "-b:a", profile.get("audio_bitrate", "192k"),
        "-pix_fmt", profile["pix_fmt"],
        str(output_path.resolve()),
    ]

    print(f"  Concatenando {len(scene_videos)} escenas...")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        print(f"  Concat error: {r.stderr[-1000:]}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--manifest", default=str(SCRIPT_DIR / "data" / "jobs" / "default" / "manifest.json"))
    parser.add_argument("--output", default=str(SCRIPT_DIR / "data" / "renders" / "final.mp4"))
    parser.add_argument("--profile", default="test_30s")
    parser.add_argument("--burn-subtitles", action="store_true")
    args = parser.parse_args()

    profiles = load_profiles()
    if args.profile not in profiles:
        print(f"Perfil '{args.profile}' no encontrado. Disponibles: {list(profiles.keys())}")
        sys.exit(1)
    profile = profiles[args.profile]

    manifest_path = Path(args.manifest)
    job_dir = manifest_path.parent
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scenes = manifest["scenes"]

    # Load images.json for multi-frame data
    images_json_path = job_dir / "images.json"
    images_json = None
    if images_json_path.exists():
        images_json = json.loads(images_json_path.read_text(encoding="utf-8"))

    temp_dir = job_dir / "render_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== RENDERIZADO DE VIDEO V2 ===")
    print(f"  Proyecto: {manifest.get('project_id', 'unknown')}")
    print(f"  Escenas: {len(scenes)}")
    print(f"  Perfil: {args.profile} ({profile['width']}x{profile['height']}@{profile['fps']})")
    print(f"  Multi-frame: {'si' if images_json else 'no'}")
    print(f"  Salida: {output_path}")

    scene_videos = []
    for i, scene in enumerate(scenes, 1):
        # Check for multi-frame data
        frames = []
        frames_dir = None
        if images_json:
            sid = str(scene["id"])
            for s in images_json.get("scenes", []):
                if str(s["scene_id"]) == sid:
                    frames_dir = Path(s["dir"])
                    frames = s["frames"]
                    break

        if frames and frames_dir:
            print(f"  [{i}] Multi-frame escena {scene['id']}: {len(frames)} keyframes")
            out = render_scene_multiframe(scene, frames_dir, frames, profile, temp_dir, i)
        else:
            print(f"  [{i}] Legacy escena {scene['id']}")
            out = render_scene_single(scene, job_dir, profile, temp_dir, i)

        if out and out.exists():
            scene_videos.append(str(out))

    if not scene_videos:
        print("ERROR: No se renderizó ninguna escena")
        sys.exit(1)

    subtitle_path = SCRIPT_DIR / "data" / "subtitles" / "all_subtitles.srt"
    ok = concatenate_scenes(scene_videos, profile, output_path, args.burn_subtitles, subtitle_path)
    if not ok:
        print("ERROR en concatenación")
        sys.exit(1)

    duration = get_video_duration(output_path)
    size = output_path.stat().st_size
    print(f"=== VIDEO GENERADO ===")
    print(f"  Path: {output_path}")
    print(f"  Duración: {duration:.1f}s")
    print(f"  Tamaño: {size:,} bytes")

    render_meta = {
        "path": str(output_path),
        "duration_sec": duration,
        "size_bytes": size,
        "profile": args.profile,
        "scenes_rendered": len(scene_videos),
        "created_at": datetime.now().isoformat()
    }
    render_path = job_dir / "render.json"
    render_path.write_text(json.dumps(render_meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Metadata guardada en {render_path}")


if __name__ == "__main__":
    main()
