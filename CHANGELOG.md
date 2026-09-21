# Changelog

## [V8.1] — Mano de alta calidad y encuadre

### Corregido
- **Mano deforme:** el motor V8.0 unía cápsulas de ancho constante, lo que
  producía un blob con dedos cortos y palma desplazada. Ahora
  `hand_geometry.py` construye primitivas anatómicas (palma trapezoidal, 4
  dedos afinados con punta redonda, pulgar y muñeca) y **traza el contorno
  exterior a un único path Bézier cerrado** (marching squares → Douglas-
  Peucker → Catmull-Rom). Línea exterior continua, sin trazos internos.
- **Mano pequeña:** el compositor escalaba por el viewBox completo, pero la
  mano ocupa una franja. Ahora usa `content_bbox()` y la encuadra por su
  contenido real (llena el alto, centrada).
- **Short cortado a la mitad:** el short se recortaba del 16:9 y cortaba la
  mano. Ahora se **compone y renderiza nativo 1080×1920**.
- **Fotos de concepto feas sobre la mano:** se retiran del compositor
  (el diseño V8 usa imágenes solo para fondos/historia/mitología).
- Líneas y montes más gruesos y con brillo; etiquetas dentro del cuadro.

### Añadido
- QA robusta de dedos por componentes conectados (resta la palma y exige 5
  componentes con punta por encima). Verificado en izquierda y derecha.
- `content_bbox()` en `hand_geometry.py`.

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
