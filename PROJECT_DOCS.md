# AI Video Factory - Documentación del Proyecto

## Resumen Ejecutivo

Fábrica local de videos educativos con IA para el tema de **Quiromancia Terapéutica**. Genera videos completos (guion → TTS → research de conceptos → imágenes multi-fotograma → subtítulos → render) usando exclusivamente herramientas locales.

**Último video generado:** `data/renders/linea-vida-v12.mp4`
- Resolución: 1920x1080 H264
- Duración: 49.3 segundos
- Audio: AAC 44100Hz stereo 192kbps (VoiceStudio femenina)
- Imágenes: Multi-frame (7 keyframes por escena con progresión visual)
- Mano: Foto real CC0 con piel cálida + overlays Cairo animados
- Conceptos: Investigación automática Openverse CC0 (mano, quiromancia, energía, etc.)

---

## Stack Tecnológico

| Componente | Tecnología | Estado |
|------------|-----------|--------|
| LLM | Ollama (CPU mode) | ✅ Funcional |
| TTS | VoiceStudio v0.5.2 (GPU) | ✅ Funcional |
| RAG | Supabase Cloud + pgvector | ✅ Funcional |
| Imágenes | Cairo (overlay) + Pillow (composición) + Openverse API | ✅ Funcional |
| Assets mano | Foto CC0 recortada + alfa feathered | ✅ Funcional |
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

## Pipeline E2E (V5)

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
│validate_video│   │ gen_images   │◀───│  generate_tts  │
│ (QA check)  │    │ (V6 hybrid)  │    │ (VoiceStudio)  │
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
7. **generate_tts** — Genera audio WAV por escena (VoiceStudio → SAPI fallback)
8. **sync durations** — Sincroniza duraciones de escena con audio real
9. **generate_images** — **[V6]** Genera multi-frame (7 keyframes/escena):
   - Mano FOTO real CC0 con piel cálida (resized_filled)
   - Overlays Cairo animados (líneas con progresión temporal)
   - Paneles de concepto investigados (fade-in segunda mitad)
   - Auto-calibración de bbox + lado del pulgar
10. **generate_subtitles** — Genera archivos SRT
11. **render_video** — **[V2]** Renderiza video multi-frame:
   - Cada keyframe → segmento con zoompan alternado
   - Concat segmentos por escena (concat demuxer)
   - Mux audio AAC 44100Hz stereo 192kbps
12. **validate_video** — Verifica calidad
13. **generate_short** — Video vertical 9:16 (opcional)

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

### generate_images.py V6
Generador multi-fotograma con mano real + overlays animados.

**Pipeline de composición por keyframe:**
1. Fondo espacial (Cairo, cacheado)
2. Mano foto real con piel cálida (Pillow: resized_filled con dilatación alfa)
3. Overlay Cairo con progreso temporal (líneas, puntos, labels)
4. Panel de concepto investigado (Pillow, fade-in segunda mitad)

**Características clave:**
- **Mano con color**: `resized_filled()` crea silueta opaca de piel (224,182,150) + líneas del dibujo encima
- **Auto-calibración**: detecta bbox y lado del pulgar desde máscara alfa
- **Progresión temporal**: líneas se dibujan gradualmente, puntos aparecen secuencialmente
- **Paneles concepto**: fotos CC0 aparecen en lado derecho con fade-in

**Uso:**
```powershell
python generate_images.py --storyboard storyboard.json --research research.json --frames 7 --width 1920 --height 1080
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

### pipeline.py V5
Orquestador del pipeline completo con step research_images.

**Uso:**
```powershell
python pipeline.py --job-id "mi-video" --topic "linea de la vida" --duration 49 --mode canned --gender female --format test_30s
```

---

## Estructura de Archivos

```
D_OLLAMA_VIDEO/
├── scripts/
│   ├── pipeline.py              # Orquestador principal (V5)
│   ├── extract_pdf.py           # PDF → Markdown
│   ├── topic_extract.py         # Rastreo temático
│   ├── rag_ingest.py            # Ingesta RAG (Supabase)
│   ├── rag_query.py             # Búsqueda semántica
│   ├── generate_script.py       # Generación de guion
│   ├── build_storyboard.py      # Manifest de producción
│   ├── research_images.py       # [NUEVO] Investigación conceptos Openverse
│   ├── generate_tts.py          # Síntesis de voz
│   ├── generate_images.py       # [V6] Multi-frame hybrid (Cairo+Pillow+foto)
│   ├── generate_subtitles.py    # Subtítulos SRT
│   ├── render_video.py          # [V2] Render FFmpeg multi-frame
│   ├── validate_video.py        # QA de video
│   ├── generate_short.py        # Video vertical 9:16
│   ├── monitor.py               # Dashboard web :8001
│   ├── generate_images_v5.py    # [RESERVA] V5 Cairo puro
│   └── start_all.ps1           # Arranque rápido
├── assets/
│   └── hands/
│       ├── hand_base.png        # [CC0] Mano palmistry recortada (alfa feathered)
│       └── candidate_*.jpg/png  # Candidatos originales
├── config/
│   ├── video_profiles.yaml      # Perfiles de render (audio 44100 stereo)
│   └── QwenVideoFactory.Modelfile
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
| **linea-vida-v12** | **linea de la vida** | **49s** | **7/escena** | **44.1kHz stereo** | **8.7MB** | **✅ ÚLTIMO** |

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
**Solución:** Curvas bezier para mano anatómica (V5), luego foto real CC0 (V6).

### 5. Audio inaudible (CRITICAL)
**Problema:** WAV mono 48kHz de VoiceStudio inaudible en reproductores.
**Solución:** Re-encode a AAC stereo 44100Hz 192kbps (integrado en render_video V2).

### 6. Mano sin color de piel
**Problema:** Foto CC0 recortada era solo silueta transparente (líneas sobre fondo oscuro).
**Solución:** `resized_filled()` crea silueta opaca de piel (224,182,150) con dilatación alfa fuerte + líneas del dibujo encima.

### 7. Un solo fotograma por escena
**Problema:** Cada escena = 1 imagen estática con slow zoom.
**Solución:** generate_images V6 genera 7 keyframes por escena con animación secuencial.

### 8. No había research de conceptos
**Problema:** Imágenes siempre iguales sin importar contenido narrativo.
**Solución:** research_images.py extrae conceptos y busca fotos CC0 en Openverse.

### 9. API Openverse no encontraba resultados
**Problema:** Queries en español no devolvían resultados relevantes.
**Solución:** Diccionario ES→EN con queries optimizadas para Openverse.

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
# Las variables de entorno se cargan desde .env (no commitear credenciales)
$py = "C:\Users\mauri\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
& $py -X utf8 -u scripts\pipeline.py --job-id "linea-vida-v12" --topic "linea de la vida" --duration 49 --mode canned --gender female --format test_30s

# 3. Ver resultado
# Video: data/renders/linea-vida-v12.mp4
# Dashboard: http://127.0.0.1:8001
```

### Solo imágenes (desarrollo/debug)
```powershell
$py = "C:\Users\mauri\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"

# Research
& $py -u scripts\research_images.py --storyboard data\jobs\<job>\storyboard.json --topic "tema" --output-dir data\research

# Generar keyframes
& $py -u scripts\generate_images.py --storyboard data\jobs\<job>\storyboard.json --research data\jobs\<job>\research.json --frames 7

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
*Última actualización: Pipeline V5, generate_images V6 (multi-frame + mano con piel), render_video V2 (audio stereo 44.1kHz), linea-vida-v12.mp4*
