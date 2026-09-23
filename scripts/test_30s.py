"""
Prueba completa 30s — Línea de la Vida.
Genera narración, frames con mano fotográfica, y video final.
"""
import json
import subprocess
import sys
import os
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
SCRIPTS = PROJECT / "scripts"
DATA = PROJECT / "data"
JOB = DATA / "jobs" / "test_30s"
JOB.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "v8"))

import hand_geometry as hg


def step1_script():
    """Crear guion de 30 segundos."""
    print("[1/6] Creating script...")
    script = {
        "title": "La Linea de la Vida",
        "duration_seconds": 30,
        "scenes": [
            {
                "id": 1, "duration": 8, "hand_side": "L", "highlight": "vida",
                "narration": "La linea de la vida es una de las lineas principales de la palma. Se origina entre el pulgar y el indice, curvandose alrededor del monte de Venus.",
                "title": "LECTURA DE MANO", "subtitle": "La Linea de la Vida"
            },
            {
                "id": 2, "duration": 8, "hand_side": "L", "highlight": "vida",
                "narration": "Su forma revela informacion sobre la vitalidad y energia de la persona. Una linea profunda indica fortaleza y resistencia.",
                "title": "PROFUNDIDAD", "subtitle": "Lo que la linea revela"
            },
            {
                "id": 3, "duration": 8, "hand_side": "R", "highlight": "vida",
                "narration": "La curva amplia sugiere una personalidad abierta y social. La curva estrecha indica introspeccion y cautela.",
                "title": "FORMA DEL NACIMIENTO", "subtitle": "Curva amplia vs estrecha"
            },
            {
                "id": 4, "duration": 6, "hand_side": "L", "highlight": "vida",
                "narration": "Recuerda, la quiromancia es una herramienta educativa. No sustituye diagnostico medico alguno.",
                "title": "AVISO IMPORTANTE", "subtitle": "Contenido educativo"
            },
        ]
    }
    (JOB / "script.json").write_text(json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8")

    narration = "\n".join([s["narration"] for s in script["scenes"]])
    (JOB / "narration.txt").write_text(narration, encoding="utf-8")
    print(f"  Script: 4 scenes, 30s total")
    return script


def step2_frames(script):
    """Generar frames con mano fotográfica."""
    print("[2/6] Rendering frames with photographic hands...")
    import cairo
    import hand_geometry as hg

    images_dir = JOB / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # Load photographic hand
    ref_l = PROJECT / "img_base" / "mano_izquierda.png"
    ref_r = PROJECT / "img_base" / "mano_derecha.png"

    from PIL import Image as PILImage
    import numpy as np

    def load_hand_png(path):
        """Load hand PNG - Cairo reads PNG correctly, no channel swap needed."""
        surf = cairo.ImageSurface.create_from_png(str(path))
        img = PILImage.open(path)
        return surf, img.width, img.height

    hand_l, hand_l_w, hand_l_h = load_hand_png(ref_l)
    hand_r, hand_r_w, hand_r_h = load_hand_png(ref_r)

    W, H = 1920, 1080
    total_frames = 0

    for scene in script["scenes"]:
        sid = scene["id"]
        scene_dir = images_dir / f"scene_{sid:03d}"
        scene_dir.mkdir(parents=True, exist_ok=True)

        hand = hand_l if scene["hand_side"] == "L" else hand_r
        hand_w = hand_l_w if scene["hand_side"] == "L" else hand_r_w
        hand_h = hand_l_h if scene["hand_side"] == "L" else hand_r_h

        frames_per_scene = 30  # 8 seconds at ~4 fps for demo
        for fi in range(frames_per_scene):
            prog = fi / max(1, frames_per_scene - 1)

            surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
            ctx = cairo.Context(surf)

            # Background: dark gradient
            grad = cairo.LinearGradient(0, 0, 0, H)
            grad.add_color_stop_rgba(0, 0.03, 0.02, 0.11, 1)
            grad.add_color_stop_rgba(1, 0.08, 0.05, 0.18, 1)
            ctx.set_source(grad)
            ctx.rectangle(0, 0, W, H)
            ctx.fill()

            # Stars
            import random
            random.seed(42)
            for _ in range(120):
                x, y = random.randint(0, W), random.randint(0, H)
                b = random.random() * 0.5 + 0.5
                ctx.set_source_rgba(b, b, b, 0.8)
                ctx.arc(x, y, random.choice([1, 1, 1.5]), 0, 6.283)
                ctx.fill()

            # Hand: centered, scaled to fit
            hand_scale = min((W * 0.5) / hand_w, (H * 0.85) / hand_h)
            hw = hand_w * hand_scale
            hh = hand_h * hand_scale
            hx = (W - hw) / 2
            hy = (H - hh) / 2

            ctx.save()
            ctx.translate(hx, hy)
            ctx.scale(hand_scale, hand_scale)
            ctx.set_source_surface(hand, 0, 0)
            ctx.paint_with_alpha(0.95)
            ctx.restore()

            # Draw life line animation
            line_prog = max(0.0, min(1.0, (prog - 0.1) / 0.6))
            if line_prog > 0:
                life_pts = [
                    (W*0.38, H*0.35), (W*0.35, H*0.45), (W*0.34, H*0.55),
                    (W*0.36, H*0.65), (W*0.40, H*0.72)
                ]
                n = max(2, int(len(life_pts) * line_prog) + 1)
                sub = life_pts[:n]

                # Glow
                ctx.set_source_rgba(0.0, 0.83, 0.92, 0.3)
                ctx.set_line_width(20)
                ctx.move_to(*sub[0])
                for p in sub[1:]:
                    ctx.line_to(*p)
                ctx.stroke()

                # Main line
                ctx.set_source_rgba(0.0, 0.83, 0.92, 0.95)
                ctx.set_line_width(8)
                ctx.set_dash([16, 8])
                ctx.move_to(*sub[0])
                for p in sub[1:]:
                    ctx.line_to(*p)
                ctx.stroke()
                ctx.set_dash([])

            # Title
            title = scene.get("title", "")
            subtitle = scene.get("subtitle", "")
            title_a = min(1.0, prog * 4) if prog < 0.3 else max(0.0, 1.0 - (prog - 0.8) * 5)

            ctx.select_font_face("Segoe UI", 0, 1)
            ctx.set_font_size(60)
            ctx.set_source_rgba(1, 1, 1, title_a)
            ext = ctx.text_extents(title)
            ctx.move_to((W - ext.width) / 2, 80)
            ctx.show_text(title)

            ctx.set_font_size(28)
            ctx.set_source_rgba(0.71, 0.63, 0.86, title_a)
            ext = ctx.text_extents(subtitle)
            ctx.move_to((W - ext.width) / 2, 120)
            ctx.show_text(subtitle)

            # Footer
            ctx.set_source_rgba(0, 0, 0, 0.6)
            ctx.rectangle(0, H - 50, W, 50)
            ctx.fill()
            ctx.set_font_size(20)
            ctx.set_source_rgba(0.47, 0.43, 0.59, 1)
            footer = "QUIROMANCIA TERAPEUTICA - CONTENIDO EDUCATIVO"
            ext = ctx.text_extents(footer)
            ctx.move_to((W - ext.width) / 2, H - 20)
            ctx.show_text(footer)

            # Scene/total
            num = f"{sid}/4"
            ext = ctx.text_extents(num)
            ctx.set_source_rgba(0.39, 0.35, 0.51, 1)
            ctx.move_to(W - ext.width - 20, H - 20)
            ctx.show_text(num)

            fp = scene_dir / f"f_{fi:03d}.png"
            surf.write_to_png(str(fp))
            total_frames += 1

        print(f"  Scene {sid}: {frames_per_scene} frames")

    print(f"  Total: {total_frames} frames")
    return total_frames


def step3_audio():
    """Generar audio TTS."""
    print("[3/6] Generating audio...")
    narration = (JOB / "narration.txt").read_text(encoding="utf-8")

    # Use VoiceStudio if available
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:3900/.well-known/voicestudio-speech", timeout=3) as r:
            pass
        # VoiceStudio available - generate via API
        print("  VoiceStudio detected, generating audio...")
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "generate_tts.py"),
             "--text-file", str(JOB / "narration.txt"),
             "--output-dir", str(JOB / "audio"),
             "--engine", "voicestudio"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            print("  Audio generated with VoiceStudio")
            return True
    except Exception:
        pass

    # Fallback: use SAPI
    print("  Using SAPI fallback...")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "generate_tts.py"),
         "--text-file", str(JOB / "narration.txt"),
         "--output-dir", str(JOB / "audio"),
         "--engine", "sapi"],
        capture_output=True, text=True, timeout=60,
    )
    return result.returncode == 0


def step4_video(total_frames):
    """Compilar video final."""
    print("[4/6] Compiling video...")
    import glob

    all_frames = sorted(glob.glob(str(JOB / "images" / "scene_*" / "f_*.png")))
    if not all_frames:
        print("  ERROR: No frames found")
        return False

    concat_file = JOB / "concat.txt"
    lines = []
    for f in all_frames:
        lines.append(f"file '{f.replace(chr(92), '/')}'")
        lines.append("duration 0.8")  # ~1.25 fps for 30s from 28 frames... adjust
    lines.append(f"file '{all_frames[-1].replace(chr(92), '/')}'")
    concat_file.write_text("\n".join(lines), encoding="utf-8")

    # Simple concat without heavy filters
    output = JOB / "final_30s.mp4"
    result = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
         "-vf", "fps=30",
         "-t", "30",
         "-c:v", "libx264", "-preset", "fast", "-crf", "23",
         "-pix_fmt", "yuv420p", str(output)],
        capture_output=True, text=True, timeout=300,
    )

    if output.exists():
        size_kb = output.stat().st_size / 1024
        print(f"  Video: {output.name} ({size_kb:.0f} KB)")
        return True
    else:
        print(f"  ERROR: {result.stderr[-200:]}")
        return False


def step5_add_audio():
    """Agregar audio al video."""
    print("[5/6] Adding audio...")
    import glob

    audio_files = glob.glob(str(JOB / "audio" / "*.wav")) + glob.glob(str(JOB / "audio" / "*.mp3"))
    video = JOB / "final_30s.mp4"
    output = JOB / "linea_vida_30s.mp4"

    if not audio_files:
        print("  No audio files found, using video without audio")
        import shutil
        shutil.copy2(video, output)
        return True

    audio = audio_files[0]
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(video), "-i", str(audio),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
         "-shortest", str(output)],
        capture_output=True, text=True, timeout=60,
    )

    if output.exists():
        size_kb = output.stat().st_size / 1024
        print(f"  Final: {output.name} ({size_kb:.0f} KB)")
        return True
    else:
        print(f"  WARN: Audio merge failed, using video only")
        import shutil
        shutil.copy2(video, output)
        return True


def step6_copy_renders():
    """Copiar a renders para fácil acceso."""
    print("[6/6] Copying to renders...")
    import shutil

    final = JOB / "linea_vida_30s.mp4"
    renders = DATA / "renders"
    renders.mkdir(parents=True, exist_ok=True)

    dest = renders / "linea_vida_30s_foto.mp4"
    if final.exists():
        shutil.copy2(final, dest)
        size_kb = dest.stat().st_size / 1024
        print(f"  Copied: {dest.name} ({size_kb:.0f} KB)")
        return True
    return False


if __name__ == "__main__":
    print("=== PRUEBA 30s - LINEA DE LA VIDA ===\n")

    script = step1_script()
    total = step2_frames(script)
    step3_audio()
    step4_video(total)
    step5_add_audio()
    step6_copy_renders()

    print("\n=== COMPLETADO ===")
    print(f"Video final: data/renders/linea_vida_30s_foto.mp4")
    print(f"Job dir: {JOB}")
