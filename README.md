# AI Video Factory - Local

Fábrica local de videos con IA, basada en Ollama + VoiceStudio (TTS) + Supabase/pgvector + FFmpeg.

## Estado del sistema (verificado 2026-09-12)

- **GPU detectada:** NVIDIA GeForce GTX 1050 4GB (la doc habla de GTX 1060 6GB; la máquina real es 1050 4GB)
- **Driver:** 546.29 / CUDA 12.3
- **Ollama:** 0.32.15 funcionando en CPU (`OLLAMA_LLM_LIBRARY=cpu`)
- **Modelos Ollama:** `qwen3.5:4b`, `nomic-embed-text`, `gemma4:*`, `video-factory-qwen`
- **VoiceStudio:** v0.5.2 instalado (MSI current-user) — **TTS natural en GPU** en `http://127.0.0.1:3900`
- **Postgres+pgvector:** en Docker (puerto 54322)
- **n8n:** Docker (puerto 5678)
- **FFmpeg:** instalado (winget)

## TTS — Voz natural (VoiceStudio)

Voz en español con **selector femenino/masculino**, generada localmente en GPU.

```powershell
# Generar narración por escena (usa VoiceStudio, fallback a SAPI)
& "C:\Users\mauri\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" `
  scripts\generate_tts.py --storyboard data\jobs\default\storyboard.json `
  --engine auto --gender female
```

- `--gender female|male` elige la voz.
- `--engine auto` prueba VoiceStudio y degrada a Windows SAPI si no está corriendo.
- `voice.json` registra por escena el motor usado (`voicestudio` o `sapi`).

**Nota de licencia:** el motor por defecto OmniVoice usa pesos **CC-BY-NC (no comercial)**. Para producción comercial, instalar CosyVoice 3 (Apache-2.0) o PocketTTS (CC-BY-4.0) desde el Model Catalogue de VoiceStudio.

**Clonación de voz:** requiere ~6 GB de VRAM; en esta máquina (4 GB) da OOM. Pendiente para hardware con más VRAM.

## Arranque rápido

```powershell
# Levanta Docker Desktop + Ollama (CPU) + VoiceStudio (GPU)
.\scripts\start_all.ps1

# Opciones
.\scripts\start_all.ps1 -NoWait        # no espera al final
.\scripts\start_all.ps1 -SkipDocker    # omite Docker
```

## Dashboard de monitoreo

```powershell
# Sirve un panel web local en http://127.0.0.1:8001
& "C:\Users\mauri\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" scripts\monitor.py
```

Muestra en tiempo real: Ollama, modelos, Postgres/pgvector, n8n, VoiceStudio, FFmpeg y uso de VRAM. Endpoint JSON: `GET /api/status`.

## Pipeline E2E

```
RAG Ingest → RAG Query → Generate Script → Build Storyboard
   → Generate TTS (VoiceStudio/SAPI) → Generate Images (Pillow)
   → Generate Subtitles → Render Video (FFmpeg)
   → Validate Video (QA) → Generate Short
```

```powershell
cd F:\__AGENCIA_AIMA\D_OLLAMA_VIDEO
.\scripts\run_e2e.ps1 -JobId "mi-prueba-001" -Mode canned -Gender female
```

Resultado: video 16:9 (1920x1080) + short 9:16 (1080x1920) en `data/renders/`.

## Estructura

```
F:\__AGENCIA_AIMA\D_OLLAMA_VIDEO\
├── README.md
├── AGENT_INSTRUCTIONS.md
├── .env, .env.example
├── requirements.txt, requirements-lock.txt
├── scripts/
│   ├── start_all.ps1        (arranque rápido de todas las instancias)
│   ├── monitor.py           (dashboard de monitoreo :8001)
│   ├── preflight.ps1
│   ├── healthcheck.ps1
│   ├── run_e2e.ps1
│   ├── rag_ingest.py / rag_query.py / generate_embeddings.py
│   ├── generate_script.py / build_storyboard.py
│   ├── generate_tts.py      (VoiceStudio + SAPI, selector de género)
│   ├── generate_images.py / generate_subtitles.py
│   ├── render_video.py / generate_short.py / validate_video.py
├── config/
│   ├── QwenVideoFactory.Modelfile
│   ├── video_profiles.yaml
│   └── quality_rules.yaml
├── data/
│   ├── documents/    (Markdown para RAG)
│   ├── jobs/         (Outputs por job)
│   ├── images/, audio/, subtitles/, renders/
│   └── logs/
├── supabase/migrations/001_rag.sql
├── workflows/
│   ├── comfyui/sd15_test.json
│   └── n8n/VIDEO_FACTORY_E2E_TEST.json
└── tests/reports/   (Reportes JSON de cada run)
```
