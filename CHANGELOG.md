# Changelog

## [V9.1] — Mano sólida PNG Cairo (fix wireframe)

### Corregido
- **Mano wireframe/sin relleno:** `svg_render` solo dibujaba strokes,
  nunca fills. La mano salía como un outline transparente.
  Solución: `hand_render.py` renderiza la mano con **Cairo directo**
  (fill + stroke) a PNG 1024×1024 RGBA. El compositor carga el PNG
  pre-renderizado en vez de usar svg_render.
- PNGs: `mano_izquierda_solid.png`, `mano_derecha_solid.png`
- Gradiente piel `#FADEC9` → `#E8B88A`, borde `#D4A574`
- Líneas gruesas coloridas + montes sólidos con halo

## [V9.0] — Mano anatómica, textos legibles, narración pausada

### Corregido
- **Mano deforme (blob):** reescritura completa de `hand_geometry.py`
  con contorno Bézier Catmull-Rom (76 puntos). Palma ancha 380px,
  4 dedos separados con punta redondeada, pulgar lateral.
- **Textos ilegibles:** títulos 60px, labels 30px, footer 22px, SRT 38px.
- **Narración robótica:** guion canned con pausas (...) y frases cortas.
  VoiceStudio OmniVoice como motor principal.
- **Líneas delgadas:** grosor 8-13px con glow.

### Añadido
- `hand_render.py`: renderizador PNG con Cairo (fill + stroke)
- `content_bbox()` para encuadre correcto de la mano
- Short 9:16 nativo (no recorte)
- `docs/BRAND_GUIDELINES.md` para quiromancia, astrología, tarot
- Monitor rediseñado con historial, engine selector, GPU bars

## [V8.1] — Mano de alta calidad y encuadre

### Corregido
- **Mano deforme (blob):** se reescribió `hand_geometry.py` completo con
  contorno anatómico suave usando Bézier Catmull-Rom. Palma ancha (380px),
  4 dedos claramente separados con punta redondeada, pulgar lateral, muñeca.
- **Textos ilegibles:** títulos放大 a 60px, subtítulos a 28px, labels a
  30px, pie de página a 22px, subtítulos SRT a 38px. Todo legible en 1080p.
- **Mano pequeña:** compositor ahora usa `content_bbox()` que incluye dedos
  + pulgar para encuadrar correctamente.
- **Short cortado:** short 9:16 nativo (no recorte del 16:9).
- **Fotos de concepto:** retiradas del compositor.
- **Líneas delgadas:** grosor aumentado a 8-13px con glow.

### Añadido
- **Narración pausada:** guion canned reescrito con pausas (...), frases
  cortas y énfasis en palabras clave. Duraciones 12s por escena.
- **Directrices de marca:** `docs/BRAND_GUIDELINES.md` completa para
  quiromancia, astrología, tarot, numerología. Incluye reglas de color,
  tipografía, animación, y guía para nuevas disciplinas.
- Motor de voz VoiceStudio (OmniVoice) como principal.
- Monitor rediseñado con historial de jobs, engine selector, GPU bars.
- `examples/` con frames + videos para validación externa.

## [V8] — Motor visual vectorial y homologación V7

### Añadido
- `scripts/v8/hand_geometry.py`: mano paramétrica determinista (palma + 5
  dedos cápsula + muñeca) en viewBox 1024², landmarks y anclas de
  líneas/montes en el mismo espacio. Emite SVG maestro izquierdo y espejo
  derecho declarado. Autotest de 5 dedos.
- `scripts/v8/svg_render.py`: tokenizador SVG→Cairo sin dependencias nuevas
  (`cairosvg` no se usa).
- `scripts/v8/compositor.py`: compositor por capas que reemplaza a
  `generate_images.py`.
- `scripts/v8/asset_registry.py`: resolución segura `asset_id`→ruta,
  máquina de estados `PENDING→GENERATING→VALIDATING→APPROVED→FROZEN` y
  detección de huérfanos.
- `scripts/v8/policy_gate.py`: puerta comercial fail-closed.
- `config/v8/render_profiles.yaml`: configuración consolidada del render.
- `docs/v8/ARQUITECTURA-V8.md`, `docs/v8/VERIFICACION-V8.md`.
- Paquete V7 homologado: `config/v7/`, `config/prompts/`, `assets/v7/`,
  `schemas/`, `scripts/v7/`, `licenses/`, `docs/v7/`.

### Cambiado
- `schemas/storyboard.schema.json` alineado con `build_storyboard.py`; el
  schema se valida dentro del pipeline.
- `build_storyboard.py` emite `video{topic,language,commercial_mode}` y por
  escena `concept_ids`, `source_refs`, `asset_ids`, `animation`.
- `generate_short.py` lee el perfil de `config/video_profiles.yaml`:
  corrige el short a `aac 44100 Hz 2 canales` (antes `48000 Hz 1 canal`).
- `render_video.py`: `resolve_path()` confina al proyecto (bloquea
  absolutas/UNC/URL), concat con rutas absolutas y sin `shell=True`.
- `generate_tts.py` registra `voice_model`, `voice_id` y `license_status`.
- `rag_ingest.py`: vínculo chunk↔sección por solapamiento de rangos →
  0 huérfanos (antes 387/387).
- `generate_script.py`: `--mode canned` respeta `--duration`.
- `pipeline.py`/`monitor.py`/`.ps1`: sin rutas absolutas; intérprete
  resuelto dinámicamente; pipeline usa el compositor V8 y ejecuta la puerta
  comercial.
- `scripts/v7/validate_asset_registry.py`: detecta SVG sin registrar.
- `scripts/v7/validate_spanish_text.py`: valida las fuentes V8 vigentes.

### Eliminado
- `scripts/generate_images.py` y `scripts/generate_images_v6.py`: motor
  raster V6 (causa del fallo de imágenes). Reemplazados por el compositor V8.
- `assets/hands/hand_base.png`, `hand_base_cut.png` y candidatos: manos
  raster rotas (contorno hueco, sin silueta sólida). Sustituidas por la mano
  vectorial. Recuperables desde el tag `v6-baseline`.

### Corregido
- La mano ya no se funde en una masa amorfa: el fallo estaba en
  `HandPhoto.resized_filled()` (dilatación morfológica sobre un dibujo de
  línea fina).
- El short recupera audio audible (44100 Hz estéreo).
- El RAG vincula todos los fragmentos a su sección.
- La publicación monetizada queda bloqueada si la voz/assets no están
  verificados (fail-closed).

## [V6] — Baseline
- Pipeline E2E funcional (guion → TTS → imágenes → subtítulos → render →
  short) con motor visual raster. Tag `v6-baseline`.
