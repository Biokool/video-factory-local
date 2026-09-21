"""
Orquestador del pipeline de generación de video.

Ejecuta el flujo completo y registra el progreso en un archivo de estado
JSON que el panel de monitoreo lee en tiempo real.

Flujo:
  1. extraer PDF (si aplica) -> .md
  2. ingesta RAG
  3. generar guion (LLM live o canned)
  4. construir storyboard
  5. TTS (VoiceStudio/SAPI, género)
  6. generar imágenes (compositor vectorial V8)
  7. generar subtítulos
  8. renderizar video (FFmpeg)
  9. validar (QA)
  10. short opcional

Uso:
  python pipeline.py --job-id mi-job --topic "..." --duration 60 \
      --instructions "..." --gender female [--pdf doc.pdf] [--format test_30s]

El estado se escribe en data/jobs/<job-id>/pipeline_status.json con:
  { status, current_step, steps: [{name,status,detail}], video, ... }
"""
import sys
import os
import json
import argparse
import subprocess
import threading
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent.parent


def resolve_python() -> str:
    """Resuelve el interprete dinamicamente.

    Prefiere el .venv del proyecto SOLO si tiene las dependencias reales
    (cairo); si esta vacio, usa el interprete en ejecucion. Evita rutas
    absolutas hardcodeadas y venvs rotos.
    """
    venv_py = SCRIPT_DIR / ".venv" / "Scripts" / "python.exe"
    if venv_py.exists():
        probe = subprocess.run(
            [str(venv_py), "-c", "import cairo, PIL, yaml"],
            capture_output=True, text=True)
        if probe.returncode == 0:
            return str(venv_py)
    return sys.executable


PYTHON = resolve_python()

STEPS = [
    "extract_pdf",
    "rag_ingest",
    "generate_script",
    "build_storyboard",
    "research_images",
    "generate_tts",
    "policy_gate",
    "generate_images",
    "generate_subtitles",
    "render_video",
    "validate_video",
    "generate_short",
]


def run(cmd, timeout=900):
    """Ejecuta un comando y devuelve (returncode, stdout, stderr)."""
    print(f"[pipeline] ejecutando: {' '.join(cmd[:4])}...", flush=True)
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


class PipelineState:
    def __init__(self, job_dir: Path, job_id: str):
        self.job_dir = job_dir
        self.job_id = job_id
        self.path = job_dir / "pipeline_status.json"
        self.state = {
            "job_id": job_id,
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
            "current_step": None,
            "steps": [{"name": s, "status": "pending", "detail": ""} for s in STEPS],
            "video": None,
            "short": None,
            "error": None,
        }
        self._lock = threading.Lock()
        self._write()

    def _write(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.state, indent=2, ensure_ascii=False), encoding="utf-8")

    def set_step(self, name, status, detail=""):
        with self._lock:
            self.state["current_step"] = name
            for s in self.state["steps"]:
                if s["name"] == name:
                    s["status"] = status
                    s["detail"] = detail
            self._write()

    def finish(self, status, video=None, short=None, error=None):
        with self._lock:
            self.state["status"] = status
            self.state["finished_at"] = datetime.now().isoformat()
            self.state["video"] = video
            self.state["short"] = short
            self.state["error"] = error
            self._write()


def main():
    print(f"[{datetime.now().isoformat()}] START main()", flush=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--instructions", default="")
    parser.add_argument("--gender", default="female", choices=["female", "male"])
    parser.add_argument("--engine", default="auto", choices=["auto", "voicestudio", "sapi"])
    parser.add_argument("--voice", default=None, help="Voz SAPI (ej: Microsoft Sabina Desktop)")
    parser.add_argument("--format", default="test_30s", choices=["test_30s", "long", "short"])
    parser.add_argument("--pdf", default=None)
    parser.add_argument("--mode", default="extract", choices=["live", "canned", "extract"])
    parser.add_argument("--skip-short", action="store_true")
    args = parser.parse_args()

    print(f"[{datetime.now().isoformat()}] Args parsed", flush=True)

    job_dir = SCRIPT_DIR / "data" / "jobs" / args.job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    state = PipelineState(job_dir, args.job_id)

    print(f"[{datetime.now().isoformat()}] State created", flush=True)

    topic = args.topic
    duration = args.duration
    instructions = args.instructions
    gender = args.gender
    engine = args.engine
    fmt = args.format
    mode = args.mode

    md_path = None

    try:
        # ── 1. Extraer PDF ────────────────────────────────────────────────
        if args.pdf:
            print(f"[{datetime.now().isoformat()}] Step: extract_pdf START", flush=True)
            pdf_path = Path(args.pdf)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")
            state.set_step("extract_pdf", "running", str(pdf_path))
            md_path = SCRIPT_DIR / "data" / "documents" / (pdf_path.stem + ".md")
            rc, out, err = run([PYTHON, str(SCRIPT_DIR / "scripts" / "extract_pdf.py"),
                                str(pdf_path), "--output", str(md_path)])
            if rc != 0:
                raise RuntimeError(f"extract_pdf: {err[-500:]}")
            state.set_step("extract_pdf", "done", str(md_path))
            print(f"[{datetime.now().isoformat()}] extract_pdf done", flush=True)
        else:
            state.set_step("extract_pdf", "skipped", "sin PDF")
            print(f"[{datetime.now().isoformat()}] extract_pdf skipped", flush=True)

        # ── 1b. Extracción temática (rastrear el tema por todo el libro) ───
        topic_context_file = None
        if md_path and md_path.exists():
            print(f"[{datetime.now().isoformat()}] Step: topic_extract START", flush=True)
            state.set_step("rag_ingest", "running", f"rastreando tema '{topic}'")
            topic_context_file = SCRIPT_DIR / "data" / "documents" / (md_path.stem + ".topic.json")
            rc, out, err = run([PYTHON, str(SCRIPT_DIR / "scripts" / "topic_extract.py"),
                                str(md_path), "--topic", topic,
                                "--output", str(topic_context_file)])
            if rc != 0:
                raise RuntimeError(f"topic_extract: {err[-500:]}")
            try:
                summary = json.loads(out.strip().split("\n")[0]) if out.strip() else {}
                detail = f"{summary.get('total_menciones', 0)} menciones, {summary.get('total_secciones', 0)} secciones"
            except Exception:
                detail = "contexto extraído"
            state.set_step("rag_ingest", "done", detail)

            # ── 2. Ingesta RAG (embeddings a pgvector) en segundo plano ────
            #   La ingesta del manual completo (~287 chunks) tarda minutos en
            #   CPU; no bloquea el pipeline. El contexto temático ya alimenta
            #   el guion, así que el RAG es solo para búsqueda semántica futura.
            def _background_rag_ingest():
                try:
                    rc, out, err = run([PYTHON, str(SCRIPT_DIR / "scripts" / "rag_ingest.py"),
                                        str(md_path), "--category", "video"],
                                       timeout=3600)
                    print(f"[{datetime.now().isoformat()}] [bg] rag_ingest rc={rc}")
                except Exception as e:
                    print(f"[background] rag_ingest error: {e}")
            threading.Thread(target=_background_rag_ingest, daemon=True).start()
            print(f"[{datetime.now().isoformat()}] RAG ingest started in background", flush=True)
        else:
            state.set_step("rag_ingest", "skipped", "sin documento nuevo")
            print(f"[{datetime.now().isoformat()}] rag_ingest skipped", flush=True)

        # ── 3. Generar guion ──────────────────────────────────────────────
        print(f"[{datetime.now().isoformat()}] Step: generate_script START", flush=True)
        state.set_step("generate_script", "running", f"modo {mode}")
        script_path = job_dir / "script.json"
        cmd = [PYTHON, str(SCRIPT_DIR / "scripts" / "generate_script.py"),
               "--topic", topic, "--duration", str(duration),
               "--mode", mode, "--output", str(script_path)]
        if instructions:
            cmd += ["--instructions", instructions]
        if topic_context_file and topic_context_file.exists():
            cmd += ["--context-file", str(topic_context_file)]
        rc, out, err = run(cmd, timeout=1200)
        if rc != 0:
            raise RuntimeError(f"generate_script: {err[-500:]}")
        state.set_step("generate_script", "done", out.strip().splitlines()[-1] if out else "")
        print(f"[{datetime.now().isoformat()}] generate_script done", flush=True)

        # ── 4. Storyboard ─────────────────────────────────────────────────
        state.set_step("build_storyboard", "running", "")
        rc, out, err = run([PYTHON, str(SCRIPT_DIR / "scripts" / "build_storyboard.py"),
                            "--script", str(script_path), "--output-dir", str(job_dir),
                            "--topic", topic])
        if rc != 0:
            raise RuntimeError(f"build_storyboard: {err[-500:]}")
        state.set_step("build_storyboard", "done", "")

        # ── 4b. Research de imagenes por concepto ────────────────────────
        #   Busca fotos CC0 en Openverse para conceptos mencionados en la
        #   narracion (manzana, cosmos, sol, planetas, dioses, etc.)
        research_path = job_dir / "research.json"
        try:
            state.set_step("research_images", "running", f"tema: {topic}")
            rc, out, err = run([PYTHON, str(SCRIPT_DIR / "scripts" / "research_images.py"),
                                "--storyboard", str(job_dir / "storyboard.json"),
                                "--topic", topic,
                                "--output-dir", str(SCRIPT_DIR / "data" / "research")],
                               timeout=300)
            if rc == 0:
                state.set_step("research_images", "done", "conceptos investigados")
            else:
                state.set_step("research_images", "warn", f"research falló: {err[-200:]}")
                research_path = None
        except Exception as e:
            state.set_step("research_images", "warn", str(e)[:200])
            research_path = None

        # ── 5. TTS ────────────────────────────────────────────────────────
        state.set_step("generate_tts", "running", f"voz {gender} · {engine}")
        tts_cmd = [PYTHON, str(SCRIPT_DIR / "scripts" / "generate_tts.py"),
                   "--storyboard", str(job_dir / "storyboard.json"),
                   "--output-dir", str(SCRIPT_DIR / "data" / "audio"),
                   "--engine", engine, "--gender", gender]
        if args.voice:
            tts_cmd += ["--voice", args.voice]
        rc, out, err = run(tts_cmd, timeout=1800)
        if rc != 0:
            raise RuntimeError(f"generate_tts: {err[-500:]}")
        state.set_step("generate_tts", "done", "")

        # ── 5b. Sincronizar duraciones de escena con audio real ──────────
        #   Después del TTS, las duraciones reales del audio pueden diferir
        #   de las originales. Actualizamos el storyboard para que cada escena
        #   dure exactamente lo que dura su audio.
        voice_path = job_dir / "voice.json"
        if voice_path.exists():
            voice_data = json.loads(voice_path.read_text(encoding="utf-8"))
            sb_path = job_dir / "storyboard.json"
            sb = json.loads(sb_path.read_text(encoding="utf-8"))
            for vs in voice_data.get("scenes", []):
                for sc in sb.get("scenes", []):
                    if sc["id"] == vs["scene_id"]:
                        sc["duration_sec"] = round(vs["duration_sec"] + 0.5, 1)
                        break
            sb["target_duration_sec"] = sum(sc["duration_sec"] for sc in sb["scenes"])
            sb_path.write_text(json.dumps(sb, indent=2, ensure_ascii=False), encoding="utf-8")
            # También actualizar manifest.json
            manifest_path = job_dir / "manifest.json"
            if manifest_path.exists():
                manifest_path.write_text(json.dumps(sb, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"[{datetime.now().isoformat()}] Duraciones sincronizadas con audio real", flush=True)

        # ── 5c. Puerta comercial fail-closed (no publicar sin voz verificada)
        try:
            voice_json = job_dir / "voice.json"
            sb_data = json.loads((job_dir / "storyboard.json").read_text(encoding="utf-8"))
            asset_ids = sorted({
                a for sc in sb_data.get("scenes", []) for a in sc.get("asset_ids", [])
            })
            state.set_step("policy_gate", "running", "evaluando política comercial")
            rc, out, err = run([PYTHON, str(SCRIPT_DIR / "scripts" / "v8" / "policy_gate.py"),
                                "--voice-json", str(voice_json),
                                "--asset-ids", ",".join(asset_ids)])
            decision = "BLOCK"
            try:
                decision = json.loads(out).get("voice", {}).get("decision", "BLOCK")
            except Exception:
                pass
            if rc == 0 and decision == "ALLOW":
                state.set_step("policy_gate", "done", "ALLOW (voz verificada)")
            else:
                state.set_step("policy_gate", "warn",
                               "BLOCK: publicación monetizada no permitida (fail-closed)")
        except Exception as e:
            state.set_step("policy_gate", "warn", f"error: {str(e)[:200]}")

        # ── 6. Imágenes (compositor V8 vectorial) ─────────────────────────
        state.set_step("generate_images", "running", "compositor V8")
        img_cmd = [PYTHON, str(SCRIPT_DIR / "scripts" / "v8" / "compositor.py"),
                    "--storyboard", str(job_dir / "storyboard.json"),
                    "--width", "1920", "--height", "1080",
                    "--frames", "7"]
        if research_path and research_path.exists():
            img_cmd += ["--research", str(research_path)]
        rc, out, err = run(img_cmd)
        if rc != 0:
            raise RuntimeError(f"compositor: {err[-500:]}")
        state.set_step("generate_images", "done", "vector-v8")

        # ── 7. Subtítulos ─────────────────────────────────────────────────
        state.set_step("generate_subtitles", "running", "")
        rc, out, err = run([PYTHON, str(SCRIPT_DIR / "scripts" / "generate_subtitles.py"),
                            "--storyboard", str(job_dir / "storyboard.json"),
                            "--voice", str(job_dir / "voice.json")])
        if rc != 0:
            raise RuntimeError(f"generate_subtitles: {err[-500:]}")
        state.set_step("generate_subtitles", "done", "")

        # ── 8. Render ─────────────────────────────────────────────────────
        state.set_step("render_video", "running", "")
        video_path = SCRIPT_DIR / "data" / "renders" / f"{args.job_id}.mp4"
        rc, out, err = run([PYTHON, str(SCRIPT_DIR / "scripts" / "render_video.py"),
                            "--manifest", str(job_dir / "manifest.json"),
                            "--output", str(video_path),
                            "--profile", fmt,
                            "--burn-subtitles"])
        if rc != 0:
            raise RuntimeError(f"render_video: {err[-500:]}")
        state.set_step("render_video", "done", str(video_path))

        # ── 9. Validación ─────────────────────────────────────────────────
        state.set_step("validate_video", "running", "")
        rc, out, err = run([PYTHON, str(SCRIPT_DIR / "scripts" / "validate_video.py"),
                            "--video", str(video_path),
                            "--job-dir", str(job_dir),
                            "--profile", fmt])
        state.set_step("validate_video", "done" if rc == 0 else "warn",
                       (out or err).strip()[-300:])

        # ── 10. Short nativo 9:16 ─────────────────────────────────────────
        short_path = None
        if not args.skip_short:
            state.set_step("generate_short", "running", "render nativo 9:16")
            short_path = SCRIPT_DIR / "data" / "renders" / f"{args.job_id}_short.mp4"
            portrait_dir = job_dir / "images_portrait"
            rc, out, err = run([PYTHON, str(SCRIPT_DIR / "scripts" / "v8" / "compositor.py"),
                                "--storyboard", str(job_dir / "storyboard.json"),
                                "--width", "1080", "--height", "1920",
                                "--frames", "7", "--output-dir", str(portrait_dir)])
            if rc != 0:
                state.set_step("generate_short", "warn", f"compositor 9:16: {err[-200:]}")
            else:
                rc, out, err = run([PYTHON, str(SCRIPT_DIR / "scripts" / "render_video.py"),
                                    "--manifest", str(job_dir / "manifest.json"),
                                    "--output", str(short_path),
                                    "--profile", "short",
                                    "--burn-subtitles"])
                if rc != 0:
                    state.set_step("generate_short", "warn", err[-300:])
                else:
                    state.set_step("generate_short", "done", str(short_path))
        else:
            state.set_step("generate_short", "skipped", "")

        state.finish("done", video=str(video_path), short=str(short_path) if short_path else None)
        print(json.dumps({"status": "done", "video": str(video_path), "short": str(short_path) if short_path else None}))

    except Exception as e:
        state.finish("error", error=str(e))
        print(json.dumps({"status": "error", "error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
