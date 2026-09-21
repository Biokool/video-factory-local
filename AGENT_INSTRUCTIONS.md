# Instrucciones para la IA Agente

## Hardware real detectado (2026-09-08)

IMPORTANTE: El plan maestro menciona **GTX 1060 6 GB**, pero la máquina real tiene:

- **GPU:** NVIDIA GeForce GTX **1050 4GB** (no 6GB)
- **Driver:** 546.29 / CUDA 12.3
- **CPU:** Intel Core i7-7700HQ 2.8 GHz, 4C/8T
- **RAM:** 32 GB DDR4

## Bug crítico de Ollama CUDA en este sistema

Ollama v0.32.15 con CUDA 12 falla consistentemente con:
```
llama-server process has terminated: exit status 0xc0000409
The system detected an overrun of a stack-based buffer
CUDA error: a PTX JIT compilation failed
```

**Workaround aplicado:** arrancar Ollama con `OLLAMA_LLM_LIBRARY=cpu` y `CUDA_VISIBLE_DEVICES=""`.

Script: `scripts/start_ollama_cpu.ps1`

## Decisiones de implementación (ACTUALIZADO 2026-09-14)

1. **TTS — VoiceStudio (motor principal):** Voz natural en español con selector de género (`female|male`), generada en GPU local.
   - App: VoiceStudio v0.5.2 (MSI current-user), backend FastAPI en `http://127.0.0.1:3900`
   - API compatible con OpenAI: `POST /v1/audio/speech`
   - El campo `instruct` controla el género (`female`/`male`).
   - **GPU activa:** PyTorch 2.8.0+cu128 soporta `sm_61` (Pascal). Síntesis ~15s/escena.
   - **Licencia:** OmniVoice por defecto = CC-BY-NC (no comercial). Para producción comercial usar CosyVoice 3 (Apache-2.0) o PocketTTS (CC-BY-4.0).
   - **Clonación de voz:** OOM en 4GB VRAM (requiere ~6GB). Pendiente para hardware con más VRAM.

2. **TTS — Windows SAPI (fallback):** incluido en Windows. Se usa si VoiceStudio no responde (health check de 3s).

3. **Imágenes — motor visual V8 (vectorial determinista):**
   - **Mano:** `scripts/v8/hand_geometry.py` construye una mano paramétrica
     (palma + 5 dedos cápsula + muñeca) en viewBox 1024², con contorno
     exterior continuo. Sin raster, sin foto, sin ML. Emite SVG maestro y
     espejo derecho declarado.
   - **Compositor:** `scripts/v8/compositor.py` dibuja por capas
     (`background → hand → natural_creases → palm_lines → zones → markers →
     guides → labels → captions → effects`). El texto se renderiza con Cairo
     (Segoe UI), nunca dentro de una imagen generada.
   - **Render SVG:** `scripts/v8/svg_render.py` (tokenizador SVG→Cairo, sin
     `cairosvg`).
   - **Registro:** `assets/v7/registry/assets.jsonl` + `scripts/v8/asset_registry.py`.
   - **Research:** Openverse API keyless busca fotos CC0 por concepto.
   - **Multi-frame:** 7 keyframes por escena con animación secuencial.
   - **ComfyUI/SD1.5:** No disponible (NumPy 2.x incompatible, pip timeouts).
   - **Retirado:** `generate_images.py` / `generate_images_v6.py` (motor
     raster V6) y la foto `assets/hands/hand_base.png`. Su dilatación
     morfológica fundía la mano en una masa sin dedos.

4. **Postgres+pgvector:** Usamos **`pgvector/pgvector:pg16`** directamente (Docker, puerto 54322).

5. **LLM (qwen3.5:4b):** Modo `canned` por defecto (templates de alta calidad); modo `live` invoca al LLM real (lento en CPU).

6. **Audio CRITICAL:** Re-encode a **AAC 44100Hz stereo 192kbps** en cada mux. Si audio suena mute, verificar `audio_samplerate: 44100` en profiles y `-ac 2` en render_video.py.

## Pipeline E2E (V8)

```
extract_pdf → topic_extract → generate_script → build_storyboard →
research_images → generate_tts → policy_gate → compositor(V8) →
generate_subtitles → render_video → validate_video → generate_short
```

La puerta comercial (`policy_gate`) es fail-closed: bloquea la publicación
monetizada si la voz o los assets no están verificados.

## Arranque y monitoreo

```powershell
# Arranque rápido de todas las instancias (Docker + Ollama CPU + VoiceStudio GPU)
.\scripts\start_all.ps1

# Dashboard de monitoreo (http://127.0.0.1:8001)
& .\.venv\Scripts\python.exe scripts\monitor.py
```

## Comandos clave (ACTUALIZADOS)

```powershell
# Pre-flight
.\scripts\preflight.ps1

# Healthcheck completo
.\scripts\healthcheck.ps1

# E2E completo (recomendado — mode canned, ~2 min)
$env:SUPABASE_DB_URL = $env:SUPABASE_DB_URL  # from .env
$py = ".\.venv\Scripts\python.exe"
& $py -X utf8 -u scripts\pipeline.py --job-id "mi-video" --topic "linea de la vida" --duration 49 --mode canned --gender female --format test_30s

# Solo research de conceptos
& $py -u scripts\research_images.py --storyboard data\jobs\<job>\storyboard.json --topic "tema" --output-dir data\research

# Solo generar imágenes (keyframes V8)
& $py -u scripts\v8\compositor.py --storyboard data\jobs\<job>\storyboard.json --research data\jobs\<job>\research.json --frames 7

# Verificar la mano (5 dedos) y regenerar SVG maestros
& $py scripts\v8\hand_geometry.py --selftest
& $py scripts\v8\hand_geometry.py --emit

# Puerta comercial
& $py scripts\v8\policy_gate.py --voice-json data\jobs\<job>\voice.json --asset-ids HAND_L_PALM_FRONT_EDITORIAL_V001,LINE_LIFE_L_BASE_V001

# Solo renderizar video
& $py scripts\render_video.py --manifest data\jobs\<job>\manifest.json --output data\renders\test.mp4 --profile test_30s

# Generar solo el audio de narración
& $py scripts\generate_tts.py --storyboard data\jobs\<job>\storyboard.json --engine auto --gender female

# Tests RAG
& $py scripts\rag_ingest.py data\documents\demo_quiro.doc.md --category quiromancia
& $py scripts\rag_query.py "línea del corazón" --top-k 3
```

## Nota de recuperación de VoiceStudio

Si una clonación de voz falla con `CUDA out of memory`, el contexto CUDA queda contaminado (incluso la síntesis simple falla). **Solución:** reiniciar VoiceStudio (cerrar la app y relanzar, o matar `omnivoice-studio.exe` y el backend). Tras el reinicio la VRAM se limpia y la síntesis simple vuelve a funcionar.

## Estructura del proyecto

Archivos clave actualizados:
- `scripts/v8/hand_geometry.py` — mano paramétrica vectorial + landmarks (NUEVO)
- `scripts/v8/svg_render.py` — render SVG→Cairo (NUEVO)
- `scripts/v8/compositor.py` — compositor por capas (reemplaza generate_images) (NUEVO)
- `scripts/v8/asset_registry.py` — resolución segura + estados (NUEVO)
- `scripts/v8/policy_gate.py` — puerta comercial fail-closed (NUEVO)
- `scripts/render_video.py` — V2 multi-frame + audio stereo + resolve_path seguro
- `scripts/pipeline.py` — V8 con compositor y policy_gate
- `scripts/generate_short.py` — perfil de audio desde YAML
- `scripts/rag_ingest.py` — vínculo chunk↔sección por rangos
- `config/video_profiles.yaml` — Audio 44100 stereo
- `config/v8/render_profiles.yaml` — configuración consolidada V8
- `schemas/storyboard.schema.json` — contrato completo V7/V8
- `assets/v7/hands/` — mano vectorial (L + R)
- `supabase/migrations/001_rag.sql` — schema RAG

## Resultado E2E verificado (V8)

- **Video:** `data/renders/v8-e2e-final.mp4` — 1920x1080, H.264
- **Short:** `data/renders/v8-e2e-final_short.mp4` — 1080x1920
- **Audio:** AAC 44100 Hz estéreo 192kbps en ambos formatos
- **Mano:** vectorial determinista, 5 dedos verificados por QA automática
- **Pasos:** todos `done`; `policy_gate: warn` (BLOCK por SAPI, correcto)
- **Detalle:** `docs/v8/VERIFICACION-V8.md`

## Próximos pasos

1. **TTS comercial verificado** — instalar CosyVoice 3 / PocketTTS para poder
   publicar monetizado (OmniVoice y SAPI quedan bloqueados por política).
2. **Calibrar líneas palmares** contra las figuras del manual y declararlas
   APPROVED/FROZEN tras revisión visual.
3. **Revisión visual de la mano** en pantalla antes de declararla FROZEN.
4. **Escalar a 8-10 min** con render por bloques reanudables.
5. **Resolver bug CUDA Ollama** — para modo `live` con LLM real.
6. **Instalar ComfyUI** — para fondos de mayor calidad (pendiente NumPy).
