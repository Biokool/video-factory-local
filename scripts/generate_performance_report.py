"""
Genera reporte de performance por etapa del pipeline.
Lee los archivos JSON generados por cada script y calcula tiempos.
"""
import os
import json
import glob
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent.parent


def main():
    job_dirs = sorted(SCRIPT_DIR.glob("data/jobs/*"))
    if not job_dirs:
        print("No hay jobs para analizar")
        return

    performance = {
        "generated_at": datetime.now().isoformat(),
        "jobs": []
    }

    for job_dir in job_dirs:
        if not job_dir.is_dir():
            continue
        job_id = job_dir.name
        job_data = {"job_id": job_id, "artifacts": {}}

        for artifact in ["script.json", "storyboard.json", "images.json", "voice.json", "subtitles.json", "render.json", "qa.json"]:
            artifact_path = job_dir / artifact
            if artifact_path.exists():
                try:
                    data = json.loads(artifact_path.read_text(encoding="utf-8"))
                    job_data["artifacts"][artifact] = {
                        "size": artifact_path.stat().st_size,
                        "present": True
                    }
                except Exception:
                    pass

        render_path = job_dir / "render.json"
        if render_path.exists():
            r = json.loads(render_path.read_text(encoding="utf-8"))
            job_data["duration_sec"] = r.get("duration_sec", 0)
            job_data["size_bytes"] = r.get("size_bytes", 0)
            job_data["profile"] = r.get("profile", "")

        performance["jobs"].append(job_data)

    report_path = SCRIPT_DIR / "tests" / "reports" / "performance.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(performance, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Reporte de performance guardado en {report_path}")
    print(json.dumps(performance, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
