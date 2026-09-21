# AI Video Factory - Local (V8)

Fábrica local de videos con IA: Ollama (LLM/embeddings) + TTS local +
Supabase/pgvector (RAG) + FFmpeg, con un **motor visual vectorial
determinista** para la mano y los overlays de quiromancia.

- Arquitectura vigente: [`docs/v8/ARQUITECTURA-V8.md`](docs/v8/ARQUITECTURA-V8.md)
- Resultados de verificación: [`docs/v8/VERIFICACION-V8.md`](docs/v8/VERIFICACION-V8.md)
- Cambios: [`CHANGELOG.md`](CHANGELOG.md)
- Contratos V7 homologados: [`docs/v7/`](docs/v7/)

## Estado del sistema

- **GPU:** NVIDIA GeForce GTX 1050 4GB (la doc antigua decía GTX 1060 6GB)
- **Ollama:** en CPU (`OLLAMA_LLM_LIBRARY=cpu`) por crash PTX JIT
- **Modelos Ollama:** `qwen3.5:4b`, `nomic-embed-text`, `gemma4:*`, `video-factory-qwen`
- **TTS:** VoiceStudio (GPU, :3900) con fallback a Windows SAPI
- **Postgres+pgvector:** Docker (:54322) · **n8n:** Docker (:5678)
- **FFmpeg:** 8.1.2 en PATH

## Motor visual V8

La mano ya **no** es una foto raster. `scripts/v8/hand_geometry.py` construye
una mano paramétrica (palma + 5 dedos cápsula + muñeca) en un viewBox de
1024², con landmarks y anclas de líneas/montes en el mismo espacio. El
`compositor.py` dibuja por capas y renderiza el texto con Cairo (Segoe UI),
nunca dentro de una imagen generada.

```powershell
# Verifica que la mano tenga exactamente 5 dedos (izquierda y derecha)
python scripts\v8\hand_geometry.py --selftest
# -> {"side": "L", "digits": 5, "ok": true, "path_points": 67}

# Regenera los SVG maestros (mano izquierda + espejo derecho)
python scripts\v8\hand_geometry.py --emit
```

## Pipeline E2E

```
extract_pdf -> RAG -> generate_script -> build_storyboard -> research_images
  -> generate_tts -> policy_gate -> compositor(V8) -> generate_subtitles
  -> render_video -> validate_video -> generate_short
```

```powershell
# 16:9 + short 9:16
python scripts\pipeline.py --job-id mi-prueba --topic "línea de la vida" `
    --duration 15 --mode canned --format test_30s
```

Resultado en `data/renders/<job>.mp4` y `data/renders/<job>_short.mp4`.
El estado paso a paso queda en `data/jobs/<job>/pipeline_status.json`.

## Arranque y monitoreo

```powershell
.\scripts\start_all.ps1          # Docker + Ollama (CPU) + VoiceStudio
.\scripts\start_all.ps1 -NoWait -SkipDocker
python scripts\monitor.py        # panel web local en http://127.0.0.1:8001
```

## Puerta comercial (fail-closed)

`config/v7/commercial_policy.yaml` + `scripts/v8/policy_gate.py` bloquean
la publicación monetizada si la voz o los assets no están verificados.

```powershell
python scripts\v8\policy_gate.py --voice-json data\jobs\<job>\voice.json `
    --asset-ids HAND_L_PALM_FRONT_EDITORIAL_V001,LINE_LIFE_L_BASE_V001
```

**OmniVoice (VoiceStudio) es CC-BY-NC** y **SAPI no está verificado**: ambos
bloquean. Para monetizar hay que instalar un TTS con licencia comercial
verificada (p. ej. CosyVoice 3 Apache-2.0 / PocketTTS CC-BY-4.0).

## Validadores

```powershell
python scripts\v7\validate_asset_registry.py   # registro + huérfanos
python scripts\v8\asset_registry.py --validate
python scripts\v7\validate_spanish_text.py     # ortografía de textos visuales
python scripts\v7\audit_v7.py                  # deuda técnica (rutas, secretos)
```

## Requisitos

`pycairo`, `Pillow`, `numpy`, `PyYAML`, `jsonschema`, `scipy`, `matplotlib`,
`psycopg2`, `faster-whisper` (opcional), `python-dotenv`. El intérprete se
resuelve dinámicamente (`.venv` si tiene dependencias; si no, `sys.executable`).

## Estructura

```
<PROJECT_ROOT>\
├── README.md · CHANGELOG.md · AGENT_INSTRUCTIONS.md · PROJECT_DOCS.md
├── .env, .env.example · requirements.txt, requirements-lock.txt
├── scripts/
│   ├── pipeline.py · monitor.py · run_e2e.ps1 · start_all.ps1 · healthcheck.ps1
│   ├── rag_ingest.py · rag_query.py · topic_extract.py · generate_embeddings.py
│   ├── generate_script.py · build_storyboard.py · generate_tts.py
│   ├── generate_subtitles.py · render_video.py · generate_short.py · validate_video.py
│   ├── v7/   (audit_v7, validate_asset_registry, validate_spanish_text)
│   └── v8/   (hand_geometry, svg_render, compositor, asset_registry, policy_gate)
├── config/
│   ├── video_profiles.yaml · quality_rules.yaml · *.Modelfile
│   ├── prompts/hands.yaml
│   ├── v7/   (commercial_policy, visual_profiles, hardware_profiles, animation_recipes)
│   └── v8/render_profiles.yaml
├── schemas/  (asset, prompt, storyboard)
├── assets/v7/
│   ├── hands/ · palm_lines/ · zones/ · signs/ · symbols/ · backgrounds/ · mythology/ · history/
│   └── registry/assets.jsonl
├── licenses/COMMERCIAL-INVENTORY.csv
├── docs/v7/  (paquete V7 homologado)  · docs/v8/ (arquitectura y verificación)
├── data/     (documents, jobs, images, audio, subtitles, renders, logs)
├── supabase/migrations/001_rag.sql
├── workflows/  (comfyui, n8n)
└── tests/reports/
```
