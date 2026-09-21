# AI Video Factory - Documentación del Proyecto

## Resumen Ejecutivo

Fábrica local de videos educativos con IA para el tema de **Quiromancia Terapéutica**. Genera videos completos (guion → TTS → research de conceptos → composición vectorial multi-fotograma → subtítulos → render) usando exclusivamente herramientas locales.

**Último video generado:** `data/renders/v8-e2e-final.mp4`
- Resolución: 1920x1080 H264 · Short 1080x1920
- Audio: AAC 44100Hz stereo 192kbps
- Imágenes: Multi-frame (7 keyframes por escena)
- Mano: vectorial determinista (5 dedos verificados por QA automática)
- Conceptos: Investigación automática Openverse CC0

> Arquitectura vigente: [`docs/v8/ARQUITECTURA-V8.md`](docs/v8/ARQUITECTURA-V8.md)
> Verificación: [`docs/v8/VERIFICACION-V8.md`](docs/v8/VERIFICACION-V8.md)

---

## Stack Tecnológico

| Componente | Tecnología | Estado |
|------------|-----------|--------|
| LLM | Ollama (CPU mode) | ✅ Funcional |
| TTS | VoiceStudio v0.5.2 (GPU) | ✅ Funcional |
| RAG | Supabase Cloud + pgvector | ✅ Funcional |
| Imágenes | Motor vectorial V8 (Cairo) + research Openverse | ✅ Funcional |
| Assets mano | SVG paramétrico determinista (5 dedos) | ✅ Funcional |
| Comercial | policy_gate fail-closed (licencias/voz) | ✅ Funcional |
| Research conceptos | Openverse API (keyless, CC0/PDM) | ✅ Funcional |
| Render | FFmpeg (multi-frame zoompan) | ✅ Funcional |
| Dashboard | Python HTTP server :8001 | ✅ Funcional |

### Hardware
- **GPU:** NVIDIA GeForce GTX 1050 4GB
- **CPU:** i7-7700HQ
- **RAM:** 32GB
- **Driver:** 546.29 / CUDA 12.3

### Limitaciones conocidas
- Ollama con CUDA crash (PTX JIT bug) → funciona en CPU mode
- VoiceStudio clonación de voz requiere ~6GB VRAM → OOM en 4GB
- OmniVoice model es CC-BY-NC (no comercial) → necesita CosyVoice 3 para producción
- Openverse API: 100 req/día anónimo → suficiente para videos individuales
- pycairo: requiere `--no-cache-dir` para instalar en Windows

---

## Pipeline E2E (V8)

```
┌─────────────┐    ┌──────────────┐    ┌────────────────┐
│ extract_pdf │───▶│ topic_extract│───▶│ generate_script│
│ (PDF → MD)  │    │ (rastreo     │    │ (guion narrativo│
│             │    │  temático)   │    │  o canned)     │
└─────────────┘    └──────────────┘    └────────────────┘
                                              │
┌─────────────┐    ┌──────────────┐    ┌────────────────┐
│ render_video│◀───│ gen_subtitles│◀───│ build_storyboard│
│ (FFmpeg V2) │    │ (SRT)        │    │ (manifest)     │
└─────────────┘    └──────────────┘    └────────────────┘
       │                                      ▲
       ▼                                      │
┌─────────────┐    ┌──────────────┐    ┌────────────────┐
│validate_video│   │  compositor  │◀───│  generate_tts  │
│ (QA check)  │    │ (V8 vectorial)│   │ (VoiceStudio)  │
└─────────────┘    └──────────────┘    └────────────────┘
                         ▲                    │
                         │              ┌────────────────┐
                         │              │ research_images │
                         │              │ (Openverse CC0) │
                         │              └────────────────┘
                         │                    │
                         │              ┌────────────────┐
                         └──────────────│build_storyboard│
                                        └────────────────┘
```

### Pasos detallados

1. **extract_pdf** — Extrae texto del PDF a Markdown (pypdf)
2. **topic_extract** — Rastrea un tema específico por todo el libro
3. **rag_ingest** — Ingesta embeddings a Supabase/pgvector (background)
4. **generate_script** — Genera guion narrativo (canned/extract/live)
5. **build_storyboard** — Crea manifest con assets, duraciones, prompts visuales
6. **research_images** — **[NUEVO V5]** Investigación automática de conceptos:
   - Extrae conceptos de narración + visual_prompt (diccionario 40+ términos ES→EN)
   - Busca fotos CC0/PDM en Openverse API (keyless)
   - Descarga a `data/research/<concepto>.jpg` con caché local
7. **generate_tts** — Genera audio WAV por escena (VoiceStudio → SAPI fallback) y registra procedencia de voz
8. **policy_gate** — **[V8]** Puerta comercial fail-closed (bloquea publicación sin voz/assets verificados)
9. **compositor** — **[V8]** Genera multi-frame (7 keyframes/escena) por capas:
   - Mano vectorial determinista (5 dedos) desde `hand_geometry.py`
   - Overlays Cairo alineados por landmarks (líneas con progresión temporal)
   - Texto con Cairo/Segoe UI (nunca dentro de un raster)
   - Paneles de concepto investigados (fade-in)
10. **generate_subtitles** — Genera archivos SRT
11. **render_video** — **[V2]** Renderiza video multi-frame:
   - Cada keyframe → segmento con zoompan alternado
   - Concat segmentos por escena (concat demuxer)
   - Mux audio AAC 44100Hz stereo 192kbps
12. **validate_video** — Verifica calidad
13. **generate_short** — Video vertical 9:16 (perfil de audio desde YAML)

---

## Scripts Principales

### research_images.py [NUEVO]
Investigación automática de imágenes por concepto.

**Funcionamiento:**
1. Tokeniza narración + visual_prompt de cada escena
2. Busca en diccionario ES→EN (manzana→"red apple fruit", cosmos→"nebula stars", etc.)
3. Consulta Openverse API (solo licencias CC0/PDM)
4. Descarga y normaliza a JPEG RGB (quality=88)
5. Caché local en `data/research/` (reutiliza entre renders)

**Diccionario de conceptos:** 40+ cubiertos incluyendo:
- manzana, cosmos, universo, galaxia, nebulosa, estrella(s)
- sol, luna, planeta(s), mercurio, venus, marte, jupiter, saturno
- zeus, dios/dioses, mitología, grecia, olimpo
- mano(s), palma, quiromancia, nacimiento, corazón
- energía, naturaleza, agua, fuego, aire, montaña
- cerebro, cuerpo, antiguo, egipto, símbolo, tarot

**Uso:**
```powershell
python research_images.py --storyboard storyboard.json --topic "linea de la vida" --output-dir data/research
```

### scripts/v8/ (motor visual)
Módulos del motor visual V8: `hand_geometry.py` (mano paramétrica),
`svg_render.py` (SVG→Cairo), `compositor.py` (capas), `asset_registry.py`
(resolución segura + estados) y `policy_gate.py` (puerta comercial).

Detalle completo en [`docs/v8/ARQUITECTURA-V8.md`](docs/v8/ARQUITECTURA-V8.md).

**Uso:**
```powershell
# Verificar la mano (5 dedos) y regenerar SVG maestros
python scripts\v8\hand_geometry.py --selftest
python scripts\v8\hand_geometry.py --emit

# Componer keyframes
python scripts\v8\compositor.py --storyboard storyboard.json --research research.json --frames 7 --width 1920 --height 1080
```

### render_video.py V2
Renderiza video final con soporte multi-fotograma.

**Flujo por escena:**
```
keyframes → segmentos (zoompan alternado in/out) → concat (video only) → mux audio (AAC 44100 stereo)
```

**Audio:** Re-encode integrado a AAC 44100Hz stereo 192kbps en cada mux y en la concatenación final.

**Uso:**
```powershell
python render_video.py --manifest manifest.json --output renders/final.mp4 --profile test_30s
```

### generate_script.py
Genera guion narrativo (canned/extract/live).

### generate_tts.py
Genera narración de voz (VoiceStudio → SAPI fallback).

### pipeline.py V8
Orquestador del pipeline completo con compositor V8 y policy_gate.

**Uso:**
```powershell
python pipeline.py --job-id "mi-video" --topic "linea de la vida" --duration 15 --mode canned --gender female --format test_30s
```

---

## Estructura de Archivos

```
D_OLLAMA_VIDEO/
├── scripts/
│   ├── pipeline.py              # Orquestador principal (V8)
│   ├── extract_pdf.py           # PDF → Markdown
│   ├── topic_extract.py         # Rastreo temático
│   ├── rag_ingest.py            # Ingesta RAG (Supabase)
│   ├── rag_query.py             # Búsqueda semántica
│   ├── generate_script.py       # Generación de guion
│   ├── build_storyboard.py      # Manifest de producción (valida schema)
│   ├── research_images.py       # Investigación conceptos Openverse
│   ├── generate_tts.py          # Síntesis de voz + procedencia
│   ├── generate_subtitles.py    # Subtítulos SRT
│   ├── render_video.py          # [V2] Render FFmpeg multi-frame
│   ├── validate_video.py        # QA de video
│   ├── generate_short.py        # Video vertical 9:16 (perfil YAML)
│   ├── monitor.py               # Dashboard web :8001
│   ├── v7/                      # Validadores y auditoría V7
│   └── v8/                      # Motor visual V8 (hand_geometry, svg_render,
│                                #   compositor, asset_registry, policy_gate)
├── assets/v7/
│   ├── hands/                   # Mano vectorial L + R
│   ├── palm_lines/              # Líneas SVG
│   └── registry/assets.jsonl    # Registro de assets (fuente de rutas)
├── config/
│   ├── video_profiles.yaml      # Perfiles de render (audio 44100 stereo)
│   ├── v7/ · v8/ · prompts/     # Políticas, perfiles y prompts
│   └── QwenVideoFactory.Modelfile
├── schemas/                     # Contratos (storyboard, asset, prompt)
├── licenses/                    # Inventario comercial
├── data/
│   ├── documents/               # PDFs extraídos
│   ├── jobs/                    # Output por job
│   │   └── <job-id>/
│   │       ├── script.json
│   │       ├── storyboard.json
│   │       ├── voice.json
│   │       ├── research.json    # [NUEVO] Conceptos investigados
│   │       ├── images.json      # [NUEVO] Índice de keyframes
│   │       └── render.json
│   ├── images/                  # Imágenes generadas
│   │   ├── scene_XXX/           # Keyframes por escena (f_000..f_006)
│   │   └── _bg_space.png        # Fondo espacial cacheado
│   ├── research/                # [NUEVO] Caché fotos CC0
│   │   ├── mano.jpg, quiromancia.jpg, energia.jpg, ...
│   ├── audio/                   # Audio TTS
│   ├── subtitles/               # Archivos SRT
│   ├── renders/                 # Videos finales
│   └── logs/
├── supabase/migrations/001_rag.sql
├── .env
├── PROJECT_DOCS.md
├── PLAN_ENTORNO_IA_VIDEO_LOCAL_GTX1060.md
├── AGENT_INSTRUCTIONS.md
└── README.md
```

---

## Videos Generados (Historial)

| Job ID | Tema | Duración | Frames | Audio | Tamaño | Estado |
|--------|------|----------|--------|-------|--------|--------|
| test-simple | quiromancia | 52s | 1/escena | 48kHz mono | ~2MB | ✅ |
| test-linea-vida | linea de la vida | 50s | 1/escena | 48kHz mono | ~2MB | ✅ |
| linea-vida-v2 | linea de la vida | 28s | 1/escena | 48kHz mono | 3.4MB | ✅ |
| linea-vida-v3 | linea de la vida | 40s | 1/escena | 48kHz mono | 4.4MB | ✅ |
| linea-vida-v4 | linea de la vida | 47s | 1/escena | 48kHz mono | 7.5MB | ✅ |
| linea-vida-v5 | linea de la vida | 49s | 1/escena | 48kHz mono | 6.3MB | ✅ |
| linea-vida-v6 | linea de la vida | 49s | 1/escena | 44.1kHz stereo | 6.0MB | ✅ |
| linea-vida-v7 | linea de la vida | 49s | 1/escena | 44.1kHz stereo | 6.8MB | ✅ |
| linea-vida-v8 | linea de la vida | 49s | 1/escena | 44.1kHz stereo | 6.0MB | ✅ |
| linea-vida-final | linea de la vida | 49s | 1/escena | 44.1kHz stereo | 6.6MB | ✅ |
| linea-vida-v9 | linea de la vida | 49s | 7/escena | 44.1kHz stereo | 7.7MB | ✅ |
| linea-vida-v10 | linea de la vida | 49s | 7/escena | 44.1kHz stereo | 7.6MB | ✅ |
| linea-vida-v11 | linea de la vida | 49s | 7/escena | 44.1kHz stereo | 8.7MB | ✅ |
| **linea-vida-v12** | linea de la vida | 49s | 7/escena | 44.1kHz stereo | 8.7MB | ✅ |
| **v8-mvp-15** | linea de la vida | 51s | 7/escena | 44.1kHz stereo | 8.4MB | ✅ V8 |
| **v8-e2e-final** | linea de la vida | 51s | 7/escena | 44.1kHz stereo | — | ✅ ÚLTIMO (V8) |

> Nota: la duración la fija el audio TTS (SAPI narra el guion completo),
> por eso un `--duration 15` con narración larga produce ~51s.

---

## Bugs Corregidos

### 1. Deadlock en PipelineState (CRITICAL)
**Problema:** `set_step()` adquiría `self._lock` y llamaba `_write()` que también lo adquiría → deadlock.
**Solución:** Eliminar lock interno de `_write()`.

### 2. Audio truncado en video
**Problema:** `-shortest` truncaba video al stream más corto.
**Solución:** Sincronizar duraciones DESPUÉS del TTS usando voice.json.

### 3. Narración textual cruda
**Problema:** Modo `extract` generaba narraciones con texto crudo del PDF.
**Solución:** Templates predefinidos de alta calidad.

### 4. Imágenes de baja calidad
**Problema:** Placeholders básicos.
**Solución:** Motor vectorial V8 determinista (mano paramétrica + overlays
alineados por landmarks). Los generadores raster V6 se retiraron.

### 5. Audio inaudible (CRITICAL)
**Problema:** WAV mono 48kHz de VoiceStudio inaudible en reproductores.
**Solución:** Re-encode a AAC stereo 44100Hz 192kbps (render_video V2) y
`generate_short.py` lee el perfil YAML (antes forzaba 48000 mono).

### 6. Mano fundida en masa amorfa (CRITICAL V6)
**Problema:** `HandPhoto.resized_filled()` aplicaba `MaxFilter(7)+MaxFilter(5)+
GaussianBlur(2)` sobre un dibujo de línea fina (alfa 8.2%, centro de palma
alfa 0), fundiendo los dedos.
**Solución:** Mano vectorial determinista (`hand_geometry.py`): 5 dedos
separados, puntas redondeadas, muñeca completa. QA automática de 5 dedos.

### 7. Un solo fotograma por escena
**Problema:** Cada escena = 1 imagen estática con slow zoom.
**Solución:** Compositor V8 genera 7 keyframes por escena con animación secuencial.

### 8. No había research de conceptos
**Problema:** Imágenes siempre iguales sin importar contenido narrativo.
**Solución:** research_images.py extrae conceptos y busca fotos CC0 en Openverse.

### 9. API Openverse no encontraba resultados
**Problema:** Queries en español no devolvían resultados relevantes.
**Solución:** Diccionario ES→EN con queries optimizadas para Openverse.

### 10. Schema contradictorio y publicación sin control (V8)
**Problema:** `storyboard.schema.json` exigía campos que el código no emitía;
ningún código leía la política comercial; `nearest_section_index()` era un
stub que dejaba 387/387 fragmentos sin sección.
**Solución:** Schema alineado y validado en el pipeline; `policy_gate.py`
fail-closed; RAG vincula por solapamiento de rangos (0 huérfanos).

---

## Configuración de Audio (CRITICAL)

Audio DEBE ser **AAC stereo 44100Hz** para reproducirse correctamente.

```yaml
# config/video_profiles.yaml
audio_codec: aac
audio_samplerate: 44100
audio_bitrate: 192k
# PCM channels se fuerza con -ac 2 en render_video.py
```

**Debug:** Si audio suena mute, verificar:
1. Profile tiene `audio_samplerate: 44100` (NO 48000)
2. render_video.py usa `-ac 2` en mux y concat
3. WAV de VoiceStudio se re-encode durante mux

---

## Cómo Ejecutar

### Pipeline completo (recomendado)
```powershell
# 1. Arrancar servicios
.\scripts\start_all.ps1

# 2. Generar video (canned = rápido, sin LLM)
$py = ".\.venv\Scripts\python.exe"
& $py -X utf8 -u scripts\pipeline.py --job-id "mi-video" --topic "linea de la vida" --duration 15 --mode canned --gender female --format test_30s

# 3. Ver resultado
# Video: data/renders/mi-video.mp4  ·  Short: data/renders/mi-video_short.mp4
# Estado: data/jobs/mi-video/pipeline_status.json
# Dashboard: http://127.0.0.1:8001
```

### Solo imágenes (desarrollo/debug)
```powershell
$py = ".\.venv\Scripts\python.exe"

# Research
& $py -u scripts\research_images.py --storyboard data\jobs\<job>\storyboard.json --topic "tema" --output-dir data\research

# Componer keyframes (V8)
& $py -u scripts\v8\compositor.py --storyboard data\jobs\<job>\storyboard.json --research data\jobs\<job>\research.json --frames 7

# Render
& $py scripts\render_video.py --manifest data\jobs\<job>\manifest.json --output data\renders\test.mp4 --profile test_30s
```

---

## Dependencias

### Python (hermes venv)
```bash
pip install pycairo Pillow numpy requests  # pycairo: --no-cache-dir
```

### Sistema
- FFmpeg (PATH global)
- VoiceStudio v0.5.2 (localhost:3900)
- Ollama (localhost:11434, CPU mode)

### APIs externas
- **Openverse API** (keyless): `https://api.openverse.org/v1/images/`
  - Rate limit: 100 req/día anónimo
  - Solo licencias CC0/PDM

---

*Documentación generada: 2026-09-13*
*Última actualización: Motor visual V8 (mano vectorial + compositor por capas),
schema alineado, policy_gate fail-closed, RAG sin huérfanos, audio 44100 stereo en 16:9 y 9:16.*
