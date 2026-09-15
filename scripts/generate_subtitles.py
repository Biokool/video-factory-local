"""
Genera subtítulos SRT por escena.
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent.parent


def format_timestamp(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--storyboard", default=str(SCRIPT_DIR / "data" / "jobs" / "default" / "storyboard.json"))
    parser.add_argument("--voice", default=str(SCRIPT_DIR / "data" / "jobs" / "default" / "voice.json"))
    parser.add_argument("--output-dir", default=str(SCRIPT_DIR / "data" / "subtitles"))
    args = parser.parse_args()

    sb = json.loads(Path(args.storyboard).read_text(encoding="utf-8"))
    voice_data = json.loads(Path(args.voice).read_text(encoding="utf-8"))
    voice_durations = {v["scene_id"]: v["duration_sec"] for v in voice_data["scenes"]}

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_subtitles = []
    current_time = 0.0
    for scene in sb["scenes"]:
        scene_id = scene["id"]
        duration = voice_durations.get(scene_id, scene["duration_sec"])
        narration = scene["narration"]
        text = scene.get("on_screen_text", "") or narration
        if not text.strip():
            continue

        start = current_time
        end = current_time + duration
        srt_path = out_dir / f"scene_{scene_id:03d}.srt"
        srt_content = f"1\n{format_timestamp(start)} --> {format_timestamp(end)}\n{text.strip()}\n"
        srt_path.write_text(srt_content, encoding="utf-8")

        all_subtitles.append({
            "scene_id": scene_id,
            "file": srt_path.name,
            "start": start,
            "end": end,
            "text": text,
        })
        print(f"  Scene {scene_id}: {srt_path.name} [{format_timestamp(start)} --> {format_timestamp(end)}]")
        current_time = end

    combined = out_dir / "all_subtitles.srt"
    with open(combined, "w", encoding="utf-8") as f:
        for i, s in enumerate(all_subtitles, 1):
            f.write(f"{i}\n{format_timestamp(s['start'])} --> {format_timestamp(s['end'])}\n{s['text']}\n\n")

    meta_path = SCRIPT_DIR / "data" / "jobs" / Path(args.storyboard).parent.name / "subtitles.json"
    meta_path.write_text(json.dumps({
        "scenes": all_subtitles,
        "total_duration": current_time,
        "combined_file": combined.name,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Subtítulos combinados en {combined}")
    print(f"Total duración subtítulos: {current_time:.1f}s")


if __name__ == "__main__":
    main()
