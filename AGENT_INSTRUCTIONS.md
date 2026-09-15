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

3. **Imágenes:** Sistema híbrido V6 (Cairo + Pillow + Openverse API)
   - **Mano:** Foto real CC0 recortada con alfa feathered (`assets/hands/hand_base.png`)
   - **Piel:** `resized_filled()` crea silueta opaca de piel cálida (224,182,150) con dilatación alfa
   - **Overlays:** Cairo dibuja líneas palmares animadas con progresión temporal
   - **Research:** Openverse API keyless busca fotos CC0 por concepto (40+ términos ES→EN)
   - **Multi-frame:** 7 keyframes por escena con animación secuencial
   - **ComfyUI/SD1.5:** No disponible (NumPy 2.x incompatible, pip timeouts)

4. **Postgres+pgvector:** Usamos **`pgvector/pgvector:pg16`** directamente (Docker, puerto 54322).

5. **LLM (qwen3.5:4b):** Modo `canned` por defecto (templates de alta calidad); modo `live` invoca al LLM real (lento en CPU).

6. **Audio CRITICAL:** Re-encode a **AAC 44100Hz stereo 192kbps** en cada mux. Si audio suena mute, verificar `audio_samplerate: 44100` en profiles y `-ac 2` en render_video.py.

## Pipeline E2E (V5)

```
extract_pdf → topic_extract → generate_script → build_storyboard →
research_images → generate_tts → sync durations → generate_images →
generate_subtitles → render_video → validate_video → generate_short
```

## Arranque y monitoreo

```powershell
# Arranque rápido de todas las instancias (Docker + Ollama CPU + VoiceStudio GPU)
.\scripts\start_all.ps1

# Dashboard de monitoreo (http://127.0.0.1:8001)
& "C:\Users\mauri\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" scripts\monitor.py
```

## Comandos clave (ACTUALIZADOS)

```powershell
# Pre-flight
.\scripts\preflight.ps1

# Healthcheck completo
.\scripts\healthcheck.ps1

# E2E completo (recomendado — mode canned, ~2 min)
$env:SUPABASE_DB_URL = $env:SUPABASE_DB_URL  # from .env
$py = "C:\Users\mauri\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
& $py -X utf8 -u scripts\pipeline.py --job-id "mi-video" --topic "linea de la vida" --duration 49 --mode canned --gender female --format test_30s

# Solo research de conceptos
& $py -u scripts\research_images.py --storyboard data\jobs\<job>\storyboard.json --topic "tema" --output-dir data\research

# Solo generar imágenes (keyframes)
& $py -u scripts\generate_images.py --storyboard data\jobs\<job>\storyboard.json --research data\jobs\<job>\research.json --frames 7

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
- `scripts/research_images.py` — Investigación conceptos Openverse (NUEVO)
- `scripts/generate_images.py` — V6 multi-frame hybrid (Cairo+Pillow+foto)
- `scripts/render_video.py` — V2 multi-frame + audio stereo
- `scripts/pipeline.py` — V5 con step research_images
- `config/video_profiles.yaml` — Audio 44100 stereo
- `assets/hands/hand_base.png` — Mano CC0 recortada
- `config/QwenVideoFactory.Modelfile` — modelo LLM
- `config/quality_rules.yaml` — reglas QA
- `supabase/migrations/001_rag.sql` — schema RAG

## Resultado E2E verificado (2026-09-14)

- **Video:** `linea-vida-v12.mp4` — 1920x1080, H.264, 49.3s, 8.7MB
- **Audio:** AAC 44100Hz stereo 192kbps
- **Imágenes:** 7 keyframes/escena × 4 escenas = 28 frames
- **Mano:** Foto CC0 con piel cálida + overlays Cairo animados
- **Conceptos:** 5 investigados (mano, quiromancia, energía, naturaleza, nacimiento)
- **Tiempo total E2E:** ~3 minutos (mode canned)

## Próximos pasos

1. **Ajustar anclas de mano** — Verificar visualmente que líneas palmares coinciden con foto real
2. **Escalar a 40 minutos** — Reducir frames/escena o optimizar render
3. **Probar con otros temas** — Cosmos, planetas, dioses griegos (conceptos más relevantes)
4. **Mejorar transiciones** — Crossfade entre keyframes (actualmente hard cuts)
5. **Resolver bug CUDA Ollama** — Para modo `live` con LLM real
6. **Instalar ComfyUI** — Para imágenes de mayor calidad (pendiente NumPy compatibility)
7. **VoiceStudio clonación** — Requiere GPU con más VRAM (6GB+)
