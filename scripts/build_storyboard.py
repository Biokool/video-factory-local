"""
Genera un storyboard a partir de un guion (script.json).

Crea un manifest con assets, duraciones, prompts visuales descriptivos
y narración consolidada optimizada para TTS.
"""
import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent.parent

# ── Prompts visuales específicos por tipo de escena ─────────────────────
VISUAL_PROMPTS = {
    "life_intro": (
        "Diagrama anatómico de mano palmar vista cenital, fondo oscuro gradiente. "
        "Línea de la vida resaltada en rojo brillante con efecto de brillo. "
        "Silueta de mano realista con piel cálida, líneas palmares visibles. "
        "Estilo educativo profesional, iluminación lateral suave."
    ),
    "life_start": (
        "Diagrama de mano palmar con tres puntos de origen marcados en la línea de la vida. "
        "Puntos numerados 1, 2, 3 con conectores punteados. "
        "Fondo oscuro, mano iluminada con luz cálida lateral. "
        "Labels anatómicos discretos, estilo infografía médica."
    ),
    "life_form": (
        "Comparación visual de dos formas de nacimiento de la línea de la vida: "
        "curva amplia vs estrecha, lado a lado. "
        "Diagrama anatómico estilo medical illustration, fondo gradiente oscuro. "
        "Líneas resaltadas con colores diferenciados."
    ),
    "life_depth": (
        "Primer plano de palma con la línea de la vida mostrando variaciones de profundidad. "
        "Sección transversal conceptual mostrando capas de la piel. "
        "Fondo oscuro, iluminación dramática lateral. "
        "Estilo educativo-científico."
    ),
    "life_breaks": (
        "Diagrama de mano con la línea de la vida mostrando interrupciones y pausas. "
        "Marcas de círculos en los puntos de interrupción. "
        "Fondo oscuro gradiente, mano realista con iluminación cálida. "
        "Estilo infografía terapéutica."
    ),
    "default": (
        "Diagrama anatómico de mano palmar profesional, fondo oscuro gradiente. "
        "Líneas palmares visibles con la línea de la vida resaltada. "
        "Silueta realista, iluminación lateral cálida. "
        "Estilo educativo-clean."
    ),
}


def get_visual_prompt(scene: dict, scene_type: str = "default") -> str:
    """Retorna un prompt visual descriptivo para la escena."""
    base = VISUAL_PROMPTS.get(scene_type, VISUAL_PROMPTS["default"])
    return base


def infer_scene_type(scene: dict, scene_id: int, total: int) -> str:
    """Infiere el tipo de escena basado en su contenido."""
    narration = scene.get("narration", "").lower()
    on_screen = scene.get("on_screen_text", "").lower()

    if scene_id == 1 or "introducción" in on_screen or "línea de la vida" in on_screen and scene_id == 1:
        return "life_intro"
    elif "punto" in narration or "partida" in narration or "origen" in narration:
        return "life_start"
    elif "forma" in narration or "nacimiento" in narration or "curva" in narration:
        return "life_form"
    elif "profundidad" in narration or "dirección" in narration or "energía" in narration:
        return "life_depth"
    elif "interrup" in narration or "pausa" in narration or "corte" in narration:
        return "life_breaks"
    else:
        return "default"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", default=str(SCRIPT_DIR / "data" / "jobs" / "default" / "script.json"))
    parser.add_argument("--output-dir", default=str(SCRIPT_DIR / "data" / "jobs" / "default"))
    args = parser.parse_args()

    script_path = Path(args.script)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    script = json.loads(script_path.read_text(encoding="utf-8"))
    scenes = script["scenes"]

    job_id = output_dir.name
    project_id = job_id if job_id != "default" else f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    manifest = {
        "project_id": project_id,
        "profile": "test_30s",
        "title": script.get("title", ""),
        "hook": script.get("hook", ""),
        "target_duration_sec": sum(s["duration_sec"] for s in scenes),
        "scenes": [],
    }

    consolidated_narration = []
    for scene in scenes:
        scene_id = scene["id"]
        scene_type = infer_scene_type(scene, scene_id, len(scenes))
        visual_prompt = get_visual_prompt(scene, scene_type)

        manifest["scenes"].append({
            "id": scene_id,
            "duration_sec": scene["duration_sec"],
            "image": f"../../images/scene_{scene_id:03d}.png",
            "voice": f"../../audio/scene_{scene_id:03d}.wav",
            "subtitle": f"../../subtitles/scene_{scene_id:03d}.srt",
            "narration": scene.get("narration") or scene.get("base_narration", ""),
            "visual_prompt": visual_prompt,
            "on_screen_text": scene.get("on_screen_text", ""),
            "effect": "slow_zoom_in",
            "source_chunk_ids": scene.get("source_chunk_ids", []),
            "scene_type": scene_type,
        })
        consolidated_narration.append(scene.get("narration") or scene.get("base_narration", ""))

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    narration_path = SCRIPT_DIR / "data" / "scenes" / "narration.txt"
    narration_path.parent.mkdir(parents=True, exist_ok=True)
    narration_path.write_text("\n\n".join(consolidated_narration), encoding="utf-8")

    storyboard_path = output_dir / "storyboard.json"
    storyboard_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Manifest guardado en {manifest_path}")
    print(f"Storyboard guardado en {storyboard_path}")
    print(f"Narración consolidada en {narration_path}")
    print(json.dumps({
        "project_id": project_id,
        "scenes": len(manifest["scenes"]),
        "total_duration_sec": manifest["target_duration_sec"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
