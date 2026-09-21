"""
Panel de control de la Fábrica Local de Video IA (backend).

Endpoints:
  GET  /                      -> dashboard HTML (desde monitor_dashboard.html)
  GET  /api/status            -> servicios + GPU + jobs resumen
  GET  /api/jobs              -> lista de jobs ejecutados
  GET  /api/jobs/<id>         -> estado detallado de un job
  GET  /api/videos            -> videos generados
  GET  /videos/<name>         -> sirve video (con Range)
  GET  /frames/<job>/<scene>  -> sirve frame PNG
  POST /api/generate          -> lanza pipeline
"""
import argparse
import cgi
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
DASHBOARD_FILE = Path(__file__).resolve().parent / "monitor_dashboard.html"


def resolve_python() -> str:
    for candidate in [
        SCRIPT_DIR / ".venv" / "Scripts" / "python.exe",
        Path(sys.executable),
    ]:
        if candidate.exists():
            try:
                probe = subprocess.run(
                    [str(candidate), "-c", "import cairo, PIL, yaml"],
                    capture_output=True, text=True, timeout=10,
                )
                if probe.returncode == 0:
                    return str(candidate)
            except Exception:
                pass
    return sys.executable


PYTHON = resolve_python()
DOCS_DIR = SCRIPT_DIR / "data" / "documents"
JOBS_DIR = SCRIPT_DIR / "data" / "jobs"
RENDERS_DIR = SCRIPT_DIR / "data" / "renders"
FRAMES_DIR = SCRIPT_DIR / "data" / "frames"

# ── Service checks ──────────────────────────────────────────────────

def _http_get(url: str, timeout: float = 4.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception:
        return None, ""


def check_ollama() -> dict:
    st, body = _http_get("http://127.0.0.1:11434/api/version")
    if st == 200:
        try:
            return {"name": "Ollama (LLM)", "status": "OK", "detail": f"v{json.loads(body).get('version', '?')}"}
        except Exception:
            return {"name": "Ollama (LLM)", "status": "OK", "detail": "activo"}
    return {"name": "Ollama (LLM)", "status": "OFF", "detail": "11434"}


def check_ollama_models() -> dict:
    st, body = _http_get("http://127.0.0.1:11434/api/tags")
    if st == 200:
        try:
            names = [m.get("name", "?") for m in json.loads(body).get("models", [])]
            return {"name": "Modelos Ollama", "status": "OK" if names else "WARN",
                    "detail": ", ".join(names[:5]) + (f" +{len(names)-5}" if len(names) > 5 else "")}
        except Exception:
            pass
    return {"name": "Modelos Ollama", "status": "WARN", "detail": "no listados"}


def check_postgres() -> dict:
    try:
        out = subprocess.run(
            ["docker", "ps", "--filter", "name=video-factory-db", "--format", "{{.Status}}"],
            capture_output=True, text=True, timeout=8,
        )
        status = out.stdout.strip()
        return {"name": "Postgres+pgvector", "status": "OK" if status else "OFF",
                "detail": status or "contenedor inactivo"}
    except Exception as e:
        return {"name": "Postgres+pgvector", "status": "OFF", "detail": str(e)[:60]}


def check_voicestudio() -> dict:
    st, body = _http_get("http://127.0.0.1:3900/.well-known/voicestudio-speech")
    if st == 200:
        try:
            v = json.loads(body).get("service_version", "?")
            return {"name": "VoiceStudio (TTS)", "status": "OK", "detail": f"v{v}"}
        except Exception:
            return {"name": "VoiceStudio (TTS)", "status": "OK", "detail": "activo"}
    return {"name": "VoiceStudio (TTS)", "status": "OFF", "detail": "3900"}


def check_ffmpeg() -> dict:
    ff = shutil.which("ffmpeg")
    return {"name": "FFmpeg", "status": "OK" if ff else "OFF", "detail": ff or "no encontrado"}


def check_gpu() -> dict | None:
    try:
        out = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=8,
        )
        if out.returncode != 0 or not out.stdout.strip():
            return None
        parts = [p.strip() for p in out.stdout.strip().split(",")]
        return {
            "status": "OK",
            "name": parts[0],
            "used_mb": int(parts[1]),
            "total_mb": int(parts[2]),
            "util_pct": int(parts[3]),
            "temp_c": int(parts[4]),
        }
    except Exception:
        return None


def build_status() -> dict:
    services = [check_ollama(), check_ollama_models(), check_postgres(),
                check_voicestudio(), check_ffmpeg()]
    gpu = check_gpu()
    jobs = list_jobs()
    ok = sum(1 for s in services if s["status"] == "OK")
    running = sum(1 for j in jobs if j.get("status") == "running")
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "services": services,
        "gpu": gpu,
        "summary": {
            "ok": ok,
            "total": len(services),
            "ready": ok >= 3,
            "total_jobs": len(jobs),
            "running_jobs": running,
            "completed_jobs": sum(1 for j in jobs if j.get("status") == "done"),
        },
    }


# ── Jobs & Videos ───────────────────────────────────────────────────

def list_jobs() -> list:
    jobs = []
    if not JOBS_DIR.exists():
        return jobs
    for d in sorted(JOBS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        st = d / "pipeline_status.json"
        if not st.exists():
            continue
        try:
            s = json.loads(st.read_text(encoding="utf-8"))
            elapsed = ""
            if s.get("started_at") and s.get("finished_at"):
                try:
                    t0 = time.mktime(time.fromisoformat(s["started_at"]))
                    t1 = time.mktime(time.fromisoformat(s["finished_at"]))
                    elapsed = f"{int(t1 - t0)}s"
                except Exception:
                    pass
            step_summary = {}
            for step in s.get("steps", []):
                step_summary[step["name"]] = step.get("status", "pending")
            video_name = None
            if s.get("video"):
                video_name = Path(s["video"]).name
            short_name = None
            if s.get("short"):
                short_name = Path(s["short"]).name
            jobs.append({
                "job_id": d.name,
                "status": s.get("status", "unknown"),
                "video": video_name,
                "short": short_name,
                "started_at": s.get("started_at", ""),
                "finished_at": s.get("finished_at", ""),
                "elapsed": elapsed,
                "topic": s.get("topic", ""),
                "steps": step_summary,
                "error": s.get("error", ""),
            })
        except Exception:
            pass
    return jobs


def list_videos() -> list:
    vids = []
    if not RENDERS_DIR.exists():
        return vids
    for f in sorted(RENDERS_DIR.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True):
        mtime = f.stat().st_mtime
        vids.append({
            "name": f.name,
            "size_mb": round(f.stat().st_size / 1e6, 1),
            "date": time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime)),
            "date_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(mtime)),
        })
    return vids


# ── Pipeline runner ─────────────────────────────────────────────────

def _run_pipeline(job_id, topic, duration, instructions, gender, engine, fmt, mode, pdf_path, skip_short):
    cmd = [
        PYTHON, str(SCRIPT_DIR / "scripts" / "pipeline.py"),
        "--job-id", job_id, "--topic", topic, "--duration", str(duration),
        "--gender", gender, "--engine", engine, "--format", fmt, "--mode", mode,
    ]
    if instructions:
        cmd += ["--instructions", instructions]
    if pdf_path:
        cmd += ["--pdf", pdf_path]
    if skip_short:
        cmd += ["--skip-short"]
    try:
        subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except Exception as e:
        st_path = JOBS_DIR / job_id / "pipeline_status.json"
        try:
            data = json.loads(st_path.read_text(encoding="utf-8")) if st_path.exists() else {}
        except Exception:
            data = {}
        data["status"] = "error"
        data["error"] = str(e)
        st_path.parent.mkdir(parents=True, exist_ok=True)
        st_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ── HTTP Handler ────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, status=200):
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _html(self, content: str):
        data = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_file(self, path: Path, content_type: str, range_header: str | None = None):
        if not path.exists() or not path.is_file():
            self._json({"error": "no encontrado"}, 404)
            return
        file_size = path.stat().st_size
        if range_header:
            m = re.match(r"bytes=(\d+)-(\d*)", range_header)
            if m:
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else file_size - 1
                end = min(end, file_size - 1)
                length = end - start + 1
                self.send_response(206)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                with open(path, "rb") as f:
                    f.seek(start)
                    self.wfile.write(f.read(length))
                return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        range_hdr = self.headers.get("Range")

        if path == "/api/status":
            self._json(build_status())
        elif path == "/api/jobs":
            self._json({"jobs": list_jobs()})
        elif path.startswith("/api/jobs/"):
            job_id = path.split("/")[-1]
            st = JOBS_DIR / job_id / "pipeline_status.json"
            if st.exists():
                try:
                    self._json(json.loads(st.read_text(encoding="utf-8")))
                except Exception:
                    self._json({"error": "ilegible"}, 500)
            else:
                self._json({"error": "no encontrado"}, 404)
        elif path == "/api/videos":
            self._json({"videos": list_videos()})
        elif path.startswith("/videos/"):
            name = path.split("/")[-1]
            self._serve_file(RENDERS_DIR / name, "video/mp4", range_hdr)
        elif path.startswith("/frames/"):
            parts = path.split("/")
            if len(parts) >= 4:
                job_id = parts[2]
                frame_name = "/".join(parts[3:])
                fp = FRAMES_DIR / job_id / frame_name
                if not fp.exists():
                    fp = JOBS_DIR / job_id / "frames" / frame_name
                self._serve_file(fp, "image/png")
            else:
                self._json({"error": "ruta inválida"}, 400)
        elif path in ("/", "/index.html"):
            try:
                html = DASHBOARD_FILE.read_text(encoding="utf-8")
            except FileNotFoundError:
                html = "<h1>monitor_dashboard.html no encontrado</h1>"
            self._html(html)
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path == "/api/generate":
            ct = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in ct:
                self._json({"error": "multipart requerido"}, 400)
                return
            form = cgi.FieldStorage(
                fp=self.rfile, headers=self.headers,
                environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": ct},
            )
            topic = (form.getvalue("topic") or "").strip()
            if not topic:
                self._json({"error": "tema requerido"}, 400)
                return
            duration = int(form.getvalue("duration") or 60)
            instructions = (form.getvalue("instructions") or "").strip()
            gender = form.getvalue("gender") or "female"
            engine = form.getvalue("engine") or "auto"
            fmt = form.getvalue("format") or "test_30s"
            mode = form.getvalue("mode") or "live"

            pdf_path = None
            pdf_item = form["pdf"] if "pdf" in form else None
            if pdf_item is not None and getattr(pdf_item, "filename", None):
                DOCS_DIR.mkdir(parents=True, exist_ok=True)
                pdf_path = DOCS_DIR / pdf_item.filename
                with open(pdf_path, "wb") as f:
                    f.write(pdf_item.file.read())

            job_id = time.strftime("%Y%m%d-%H%M%S") + "-" + __import__("uuid").uuid4().hex[:6]
            skip_short = (fmt == "short")
            threading.Thread(
                target=_run_pipeline,
                args=(job_id, topic, duration, instructions, gender, engine, fmt, mode,
                      str(pdf_path) if pdf_path else None, skip_short),
                daemon=True,
            ).start()
            self._json({"job_id": job_id, "status": "started"})
        else:
            self._json({"error": "not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, fmt, *args):
        return


def main():
    parser = argparse.ArgumentParser(description="Video Factory Monitor")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    print(f"  Panel de control: http://{args.host}:{args.port}")
    print(f"  Dashboard file:  {DASHBOARD_FILE}")
    print(f"  Python:          {PYTHON}")
    print("  Presiona Ctrl+C para detener.\n")

    server = HTTPServer((args.host, args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
