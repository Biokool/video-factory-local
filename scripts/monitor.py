"""
Panel de control de la Fábrica Local de Video IA.

Funcionalidades:
  1. Estado en tiempo real de todas las instancias (Ollama, pgvector, n8n,
     VoiceStudio, FFmpeg, GPU).
  2. Generación de video: subir un PDF (contexto), definir tema, duración,
     instrucciones/enfoque, género y formato.
  3. Lanzar el pipeline completo y monitorear su progreso paso a paso.
  4. Listar los videos generados.

Sin dependencias externas (solo stdlib). El pipeline se ejecuta en subproceso.

Endpoints:
  GET  /                      -> dashboard HTML
  GET  /api/status            -> estado de servicios (JSON)
  POST /api/generate          -> sube PDF + parámetros y lanza el pipeline
  GET  /api/jobs/<id>         -> estado de un job del pipeline
  GET  /api/jobs              -> lista de jobs
  GET  /api/videos            -> lista de videos generados
  GET  /videos/<name>         -> sirve un video generado

Uso:
  python scripts/monitor.py            # http://127.0.0.1:8001
"""
import argparse
import cgi
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
PYTHON = r"C:\Users\mauri\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
DOCS_DIR = SCRIPT_DIR / "data" / "documents"
JOBS_DIR = SCRIPT_DIR / "data" / "jobs"
RENDERS_DIR = SCRIPT_DIR / "data" / "renders"

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Video Factory — Panel de Control</title>
<style>
  :root { --bg:#0d1117; --panel:#161b22; --border:#30363d; --ok:#3fb950; --off:#f85149; --warn:#d29922; --txt:#e6edf3; --muted:#8b949e; --accent:#58a6ff; }
  * { box-sizing: border-box; }
  body { margin:0; font-family:'Segoe UI',system-ui,-apple-system,sans-serif; background:var(--bg); color:var(--txt); }
  header { padding:16px 24px; border-bottom:1px solid var(--border); display:flex; align-items:center; gap:16px; flex-wrap:wrap; }
  header h1 { margin:0; font-size:1.2rem; font-weight:600; }
  header .sub { color:var(--muted); font-size:.8rem; }
  .dot { width:10px; height:10px; border-radius:50%; display:inline-block; }
  .dot.ok{background:var(--ok)} .dot.off{background:var(--off)} .dot.warn{background:var(--warn)}
  .wrap { display:grid; grid-template-columns:1fr 1fr; gap:18px; padding:20px 24px; }
  @media (max-width: 900px) { .wrap { grid-template-columns:1fr; } }
  .card { background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:18px; }
  .card h2 { margin:0 0 12px; font-size:.95rem; font-weight:600; text-transform:uppercase; letter-spacing:.4px; color:var(--muted); }
  label { display:block; font-size:.82rem; margin:10px 0 4px; color:var(--muted); }
  input, textarea, select { width:100%; background:#0d1117; border:1px solid var(--border); color:var(--txt); border-radius:6px; padding:8px 10px; font-size:.9rem; font-family:inherit; }
  textarea { min-height:70px; resize:vertical; }
  .row { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  button { background:var(--accent); color:#fff; border:0; border-radius:6px; padding:10px 16px; font-size:.9rem; font-weight:600; cursor:pointer; margin-top:14px; }
  button:hover { filter:brightness(1.1); }
  button:disabled { opacity:.5; cursor:not-allowed; }
  .svc { display:flex; align-items:center; gap:8px; padding:6px 0; border-bottom:1px solid #1c2128; font-size:.88rem; }
  .svc:last-child { border-bottom:0; }
  .svc .n { flex:1; }
  .svc .d { color:var(--muted); font-size:.75rem; }
  .steps { margin-top:14px; }
  .step { display:flex; align-items:center; gap:10px; padding:7px 10px; border-radius:6px; font-size:.85rem; margin:4px 0; background:#0d1117; border:1px solid var(--border); }
  .step.done { border-color:var(--ok); }
  .step.running { border-color:var(--accent); }
  .step.warn { border-color:var(--warn); }
  .step.error, .step.failed { border-color:var(--off); }
  .step .tag { font-size:.68rem; padding:2px 8px; border-radius:12px; background:#21262d; }
  .step.done .tag { background:var(--ok); color:#000; }
  .step.running .tag { background:var(--accent); color:#000; }
  .step.error .tag { background:var(--off); }
  .step .detail { color:var(--muted); font-size:.72rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:320px; }
  .video-link { display:block; color:var(--accent); margin:4px 0; text-decoration:none; }
  .empty { color:var(--muted); font-size:.85rem; font-style:italic; }
  footer { padding:14px 24px; color:var(--muted); font-size:.78rem; border-top:1px solid var(--border); }
  #banner { margin:14px 24px 0; padding:12px 16px; border-radius:8px; font-size:.9rem; display:none; }
  #banner.ok { display:block; background:#12261a; border:1px solid var(--ok); color:#7ee787; }
  #banner.err { display:block; background:#2a1215; border:1px solid var(--off); color:#ffa198; }
</style>
</head>
<body>
<header>
  <div><h1>AI Video Factory</h1><div class="sub">Panel de control — generación y monitoreo local</div></div>
  <div class="sub" id="clock" style="margin-left:auto;"></div>
</header>

<div id="banner"></div>

<div class="wrap">
  <div class="card">
    <h2>Generar video</h2>
    <label>Tema (qué trata el video)</label>
    <input id="topic" placeholder="Ej: La línea del corazón en la quiromancia terapéutica">

    <label>Documento de contexto (PDF)</label>
    <input type="file" id="pdf" accept=".pdf">

    <label>Instrucciones / enfoque</label>
    <textarea id="instructions" placeholder="Ej: educativo, terapéutico, no adivinatorio, cercano y en español de México"></textarea>

    <div class="row">
      <div>
        <label>Duración aprox. (segundos)</label>
        <input id="duration" type="number" value="60" min="15" max="540">
      </div>
      <div>
        <label>Voz</label>
        <select id="gender"><option value="female">Femenina</option><option value="male">Masculina</option></select>
      </div>
    </div>

    <div class="row">
      <div>
        <label>Formato</label>
        <select id="format">
          <option value="test_30s">Prueba 30s (16:9)</option>
          <option value="long">Largo 8-9 min (16:9)</option>
          <option value="short">Short (9:16)</option>
        </select>
      </div>
      <div>
        <label>Guion</label>
        <select id="mode"><option value="live">IA (LLM + RAG)</option><option value="canned">Plantilla</option></select>
      </div>
    </div>

    <button id="generate">Generar video</button>
  </div>

  <div class="card">
    <h2>Progreso del job</h2>
    <div id="jobinfo" class="empty">Sin job activo</div>
    <div id="steps" class="steps"></div>
  </div>

  <div class="card">
    <h2>Servicios</h2>
    <div id="services"><div class="empty">Cargando…</div></div>
    <div id="gpu" style="margin-top:10px;"></div>
  </div>

  <div class="card">
    <h2>Videos generados</h2>
    <div id="videos"><div class="empty">Cargando…</div></div>
  </div>
</div>

<footer>Panel local — los datos no salen de tu máquina. Pipeline ejecutado en subproceso.</footer>

<script>
let currentJob = null;
let pollTimer = null;

async function loadServices() {
  try {
    const r = await fetch('/api/status'); const d = await r.json();
    const s = document.getElementById('services');
    s.innerHTML = (d.services||[]).map(x => `<div class="svc"><span class="dot ${x.status==='OK'?'ok':(x.status==='WARN'?'warn':'off')}"></span><span class="n">${x.name}</span><span class="d">${x.detail||''}</span></div>`).join('');
    const g = document.getElementById('gpu');
    if (d.gpu) g.innerHTML = `<div class="svc"><span class="dot ${d.gpu.status==='OK'?'ok':'off'}"></span><span class="n">GPU ${d.gpu.name||''}</span><span class="d">VRAM ${d.gpu.used_mb}/${d.gpu.total_mb} MB</span></div>`;
  } catch(e) {}
}
async function loadVideos() {
  try {
    const r = await fetch('/api/videos'); const d = await r.json();
    const v = document.getElementById('videos');
    if (!d.videos || !d.videos.length) { v.innerHTML = '<div class="empty">No hay videos todavía</div>'; return; }
    v.innerHTML = d.videos.map(x => `<div><a class="video-link" href="/videos/${x.name}" target="_blank">▶ ${x.name}</a><span class="sub"> (${x.size_mb} MB, ${x.date})</span></div>`).join('');
  } catch(e) {}
}
function statusTag(s) { return {pending:'pendiente',running:'en curso',done:'hecho',skipped:'omitido',warn:'aviso',error:'error',failed:'error'}[s] || s; }
async function loadJob(id) {
  if (!id) return;
  try {
    const r = await fetch('/api/jobs/' + id); const d = await r.json();
    const info = document.getElementById('jobinfo');
    info.innerHTML = `<b>${d.job_id}</b> · estado: <b>${d.status}</b>`;
    if (d.error) info.innerHTML += `<br><span style="color:var(--off)">${d.error}</span>`;
    const st = document.getElementById('steps');
    st.innerHTML = (d.steps||[]).map(s => `<div class="step ${s.status}"><span class="tag">${statusTag(s.status)}</span><span>${s.name}</span><span class="detail">${s.detail||''}</span></div>`).join('');
    if (d.status === 'done' || d.status === 'error') {
      if (d.video) info.innerHTML += `<br><a class="video-link" href="/videos/${d.video.split(/[\\/]/).pop()}" target="_blank">▶ Ver video</a>`;
      clearInterval(pollTimer); pollTimer = null; loadVideos();
    }
  } catch(e) {}
}
async function generate() {
  const topic = document.getElementById('topic').value.trim();
  if (!topic) { alert('Escribe un tema.'); return; }
  const banner = document.getElementById('banner');
  banner.className = ''; banner.textContent = '';
  const fd = new FormData();
  fd.append('topic', topic);
  fd.append('duration', document.getElementById('duration').value);
  fd.append('instructions', document.getElementById('instructions').value);
  fd.append('gender', document.getElementById('gender').value);
  fd.append('format', document.getElementById('format').value);
  fd.append('mode', document.getElementById('mode').value);
  const pdf = document.getElementById('pdf').files[0];
  if (pdf) fd.append('pdf', pdf);
  document.getElementById('generate').disabled = true;
  try {
    const r = await fetch('/api/generate', { method:'POST', body: fd });
    const d = await r.json();
    if (!r.ok) { banner.className='err'; banner.textContent = d.error || 'Error al iniciar'; }
    else {
      banner.className='ok'; banner.textContent = 'Generación iniciada: ' + d.job_id;
      currentJob = d.job_id;
      loadJob(currentJob);
      if (pollTimer) clearInterval(pollTimer);
      pollTimer = setInterval(() => loadJob(currentJob), 3000);
    }
  } catch(e) { banner.className='err'; banner.textContent = String(e); }
  finally { document.getElementById('generate').disabled = false; }
}
document.getElementById('generate').addEventListener('click', generate);
document.getElementById('clock').textContent = new Date().toLocaleTimeString();
setInterval(() => { document.getElementById('clock').textContent = new Date().toLocaleTimeString(); }, 1000);
loadServices(); loadVideos();
setInterval(loadServices, 5000);
setInterval(() => { if (!currentJob) loadVideos(); }, 5000);
</script>
</body>
</html>
"""


def http_get_json(url: str, timeout: float = 4.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)


def check_ollama() -> dict:
    st, body = http_get_json("http://127.0.0.1:11434/api/version")
    if st == 200:
        return {"name": "Ollama (LLM/embeddings)", "status": "OK", "detail": f"v{json.loads(body).get('version', '?')}"}
    return {"name": "Ollama (LLM/embeddings)", "status": "OFF", "detail": "sin respuesta en :11434"}


def check_ollama_models() -> dict:
    st, body = http_get_json("http://127.0.0.1:11434/api/tags")
    if st == 200:
        try:
            names = [m.get("name", "") for m in json.loads(body).get("models", [])]
            return {"name": "Modelos Ollama", "status": "OK", "detail": ", ".join(names)}
        except Exception:
            pass
    return {"name": "Modelos Ollama", "status": "WARN", "detail": "no se pudieron listar"}


def check_postgres() -> dict:
    try:
        out = subprocess.run(
            ["docker", "ps", "--filter", "name=video-factory-db", "--format", "{{.Status}}"],
            capture_output=True, text=True, timeout=8,
        )
        status = out.stdout.strip()
        if status:
            return {"name": "Postgres + pgvector", "status": "OK", "detail": status}
        return {"name": "Postgres + pgvector", "status": "OFF", "detail": "contenedor no activo"}
    except Exception as e:
        return {"name": "Postgres + pgvector", "status": "OFF", "detail": f"Docker no disponible: {e}"}


def check_n8n() -> dict:
    st, _ = http_get_json("http://127.0.0.1:5678")
    if st == 200:
        return {"name": "n8n (orquestador)", "status": "OK", "detail": "respondiendo en :5678"}
    return {"name": "n8n (orquestador)", "status": "OFF", "detail": "sin respuesta en :5678"}


def check_voicestudio() -> dict:
    st, body = http_get_json("http://127.0.0.1:3900/.well-known/voicestudio-speech")
    if st == 200:
        try:
            v = json.loads(body).get("service_version", "?")
            return {"name": "VoiceStudio (TTS)", "status": "OK", "detail": f"v{v} · GPU"}
        except Exception:
            return {"name": "VoiceStudio (TTS)", "status": "OK", "detail": "respondiendo en :3900"}
    return {"name": "VoiceStudio (TTS)", "status": "OFF", "detail": "sin respuesta en :3900"}


def check_ffmpeg() -> dict:
    ff = shutil.which("ffmpeg")
    if ff:
        return {"name": "FFmpeg", "status": "OK", "detail": ff}
    return {"name": "FFmpeg", "status": "OFF", "detail": "no encontrado en PATH"}


def check_gpu() -> dict | None:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=8,
        )
        if out.returncode != 0 or not out.stdout.strip():
            return None
        name, used, total = out.stdout.strip().split(",")
        return {"status": "OK", "name": name.strip(),
                "used_mb": int(used.strip()), "total_mb": int(total.strip())}
    except Exception:
        return None


def build_status() -> dict:
    services = [check_ollama(), check_ollama_models(), check_postgres(), check_n8n(), check_voicestudio(), check_ffmpeg()]
    gpu = check_gpu()
    ok = sum(1 for s in services if s["status"] == "OK")
    return {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "services": services, "gpu": gpu,
            "summary": {"ok": ok, "total": len(services), "ready": ok == len(services)}}


def list_jobs() -> list:
    jobs = []
    if not JOBS_DIR.exists():
        return jobs
    for d in sorted(JOBS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        st = d / "pipeline_status.json"
        if st.exists():
            try:
                s = json.loads(st.read_text(encoding="utf-8"))
                jobs.append({"job_id": d.name, "status": s.get("status"),
                             "video": s.get("video"), "short": s.get("short"),
                             "started_at": s.get("started_at")})
            except Exception:
                pass
    return jobs


def list_videos() -> list:
    vids = []
    if not RENDERS_DIR.exists():
        return vids
    for f in sorted(RENDERS_DIR.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True):
        vids.append({"name": f.name, "size_mb": round(f.stat().st_size / 1e6, 1),
                     "date": time.strftime("%Y-%m-%d %H:%M", time.localtime(f.stat().st_mtime))})
    return vids


def _run_pipeline(job_id, topic, duration, instructions, gender, fmt, mode, pdf_path, skip_short):
    cmd = [PYTHON, str(SCRIPT_DIR / "scripts" / "pipeline.py"),
           "--job-id", job_id, "--topic", topic, "--duration", str(duration),
           "--gender", gender, "--format", fmt, "--mode", mode]
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


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, status=200):
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _html(self, payload):
        data = payload.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/status":
            self._json(build_status())
        elif self.path == "/api/jobs":
            self._json({"jobs": list_jobs()})
        elif self.path.startswith("/api/jobs/"):
            job_id = self.path.split("/")[-1]
            st = JOBS_DIR / job_id / "pipeline_status.json"
            if st.exists():
                try:
                    self._json(json.loads(st.read_text(encoding="utf-8")))
                except Exception:
                    self._json({"error": "estado ilegible"}, 500)
            else:
                self._json({"error": "job no encontrado"}, 404)
        elif self.path == "/api/videos":
            self._json({"videos": list_videos()})
        elif self.path.startswith("/videos/"):
            name = self.path.split("/")[-1]
            fp = RENDERS_DIR / name
            if fp.exists() and fp.suffix == ".mp4":
                data = fp.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self._json({"error": "no encontrado"}, 404)
        elif self.path in ("/", "/index.html"):
            self._html(DASHBOARD_HTML)
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path == "/api/generate":
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in content_type:
                self._json({"error": "se requiere multipart/form-data"}, 400)
                return
            form = cgi.FieldStorage(
                fp=self.rfile, headers=self.headers,
                environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type},
            )
            topic = (form.getvalue("topic") or "").strip()
            if not topic:
                self._json({"error": "tema requerido"}, 400)
                return
            duration = int(form.getvalue("duration") or 60)
            instructions = (form.getvalue("instructions") or "").strip()
            gender = form.getvalue("gender") or "female"
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
                args=(job_id, topic, duration, instructions, gender, fmt, mode, str(pdf_path) if pdf_path else None, skip_short),
                daemon=True,
            ).start()
            self._json({"job_id": job_id, "status": "started"})
        else:
            self._json({"error": "not found"}, 404)

    def log_message(self, fmt, *args):
        return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), Handler)
    print(f"Panel de control: http://{args.host}:{args.port}")
    print("Presiona Ctrl+C para detener.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
