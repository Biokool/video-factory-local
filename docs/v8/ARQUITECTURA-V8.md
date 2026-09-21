# Arquitectura V8 — Video Factory local (quiromancia terapéutica)

Esta es la arquitectura vigente del proyecto. Sustituye al motor visual V6
(raster + foto de mano dilatada) por un **motor vectorial determinista** y
homologa los contratos V7 del paquete de revisión.

## Principio rector

El sistema produce manos, líneas, montes, etiquetas y animaciones mediante
**assets aprobados y capas deterministas**. Las imágenes generadas por IA
solo se usan para fondos, historia, mitología y decoración; **nunca** para
la mano ni para texto (el texto se renderiza con Cairo, jamás dentro de un
raster).

## Flujo end-to-end

```
extract_pdf -> topic_extract/rag_ingest -> generate_script -> build_storyboard
   -> research_images -> generate_tts -> policy_gate -> compositor(V8)
   -> generate_subtitles -> render_video -> validate_video -> generate_short
```

Orquestado por `scripts/pipeline.py` y monitorizado por `scripts/monitor.py`.

## Motor visual V8 (`scripts/v8/`)

| Módulo | Responsabilidad |
|---|---|
| `hand_geometry.py` | Mano paramétrica determinista (palma + 5 dedos cápsula + muñeca) en viewBox 1024². Define landmarks y anclas de líneas/montes en el mismo espacio. Emite SVG maestro y espejo derecho declarado. |
| `svg_render.py` | Tokenizador mínimo SVG→Cairo (M/L/H/V/C/S/Z, `<g>`, círculos/elipses/rects). Sin `cairosvg`. Rasteriza a máscara para QA. |
| `compositor.py` | Compositor por capas. Reemplaza a `generate_images.py`. |
| `asset_registry.py` | Resolución segura de `asset_id` → ruta (confina a `assets/`), máquina de estados y detección de huérfanos. |
| `policy_gate.py` | Puerta comercial fail-closed (voz, licencias, estado de assets). |

### Orden de capas (docs/v7/03)

`background → hand → natural_creases → palm_lines → zones → markers →
guides → labels → captions → effects`

El compositor dibuja mano y overlays en el **mismo espacio de coordenadas**
(1024²) y los mapea a la caja destino, de modo que la alineación queda
garantizada por construcción (desaparecen los números mágicos `PALM`/`MONTES`).

### Mano: por qué vectorial

El fallo del V6 era `HandPhoto.resized_filled()` en `generate_images.py`:
`MaxFilter(7)+MaxFilter(5)+GaussianBlur(2)` dilataba el alfa de un dibujo de
línea fina y lo fundía en una masa amorfa sin dedos. La solución no es otra
foto (ningún raster del proyecto es una silueta sólida), sino **construir la
geometría**. La mano se compone de primitivas (palma elíptica, muñeca y 5
dedos cápsula) con contorno exterior continuo por construcción: una capa de
contorno expandida y encima la capa de piel que cubre los trazos internos.

QA automática: `python scripts/v8/hand_geometry.py --selftest` exige
exactamente **5 tramos de dedo** en la banda superior de la máscara.

## Contratos

- `schemas/storyboard.schema.json` es el contrato completo: incluye el
  bloque `video{topic,language,commercial_mode}` y, por escena,
  `concept_ids`, `source_refs`, `asset_ids` y `animation`, además de los
  campos de render que usa el pipeline. `build_storyboard.py` valida el
  schema **dentro del pipeline** (no solo a mano).
- `assets/v7/registry/assets.jsonl` es la fuente de rutas: el storyboard
  aporta `asset_id`, el registro traduce a ruta. Se rechazan `../`, `C:\`,
  `\\`, `http(s)://`.
- Estados de asset: `PENDING → GENERATING → VALIDATING → APPROVED → FROZEN`.

## Puerta comercial (fail-closed)

`config/v7/commercial_policy.yaml` exige `fail_closed: true`,
`allow_unknown_license: false`, `blocked_models: [OmniVoice]` y assets en
`APPROVED` con licencia `VERIFIED`. `policy_gate.py` lee la política, el
registro y `licenses/COMMERCIAL-INVENTORY.csv`. La voz se registra con
`voice_model`, `voice_id` y `license_status`; **SAPI y OmniVoice bloquean
la publicación monetizada** (OmniVoice es CC-BY-NC). Para producción se
debe seleccionar e instalar un TTS con licencia comercial verificada.

## Configuración

- `config/v7/`: política comercial, perfiles de hardware/visuales, recetas
  de animación y prompts de manos.
- `config/v8/render_profiles.yaml`: consolidado del render V8 (orden de
  capas, fuente, assets de mano, animaciones).

## Requisitos de entorno

- Windows + FFmpeg en PATH.
- Python con: `pycairo`, `Pillow`, `numpy`, `PyYAML`, `jsonschema`,
  `scipy`, `matplotlib`, `psycopg2`, `faster-whisper` (opcional),
  `python-dotenv`.
- Ollama en CPU (`OLLAMA_LLM_LIBRARY=cpu`) para LLM/embeddings.
- El intérprete se resuelve dinámicamente: se prefiere `.venv` del proyecto
  solo si tiene las dependencias; si está vacío, usa `sys.executable`.
