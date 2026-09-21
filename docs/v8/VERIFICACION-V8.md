# Verificación V8/V9 — resultados medidos

Todos los comandos se ejecutan desde la raíz del proyecto con el intérprete
con dependencias. Resultados obtenidos en la máquina de producción.

## 1. Mano sólida PNG (V9.1 fix)

```
python scripts/v8/hand_render.py
L: assets/v8/hands/mano_izquierda_solid.png
R: assets/v8/hands/mano_derecha_solid.png
```

Verificación de píxeles:
```
Tamaño: 1024×1024 RGBA
Píxeles opacos: 156658/1048576 (14.9%)
Color palma (512,590): RGBA=(250, 222, 201, 255) = #FADDC9 ✓
```

La mano se renderiza con **Cairo directo** (fill + stroke), no con
svg_render (que solo dibujaba strokes → wireframe). El compositor
carga el PNG pre-renderizado via `cairo.ImageSurface.create_from_png()`.

### Geometría (V9 hand_geometry)
```
python scripts/v8/hand_geometry.py --selftest
{
  "side": "L",
  "ok": true,
  "outline_points": 76,
  "finger_tips_above_palm": 4,
  "finger_spread_px": 220,
  "finger_tips_y": [190, 160, 195, 245],
  "finger_tips_x": [407, 482, 557, 627]
}
```

## 2. Registro de assets

```
python scripts/v7/validate_asset_registry.py   -> passed: true, orphans: []
python scripts/v8/asset_registry.py --validate -> passed: true, orphans: []
```

6 SVG registrados (2 manos + 4 líneas). El validador recorre el disco y
detecta SVG sin registrar (huérfanos).

## 3. Contrato del storyboard

```
python scripts/build_storyboard.py --script ... --output-dir ... --topic "..."
Schema storyboard: PASS
```

`build_storyboard.py` emite `video{topic,language,commercial_mode}` y por
escena `concept_ids`, `source_refs`, `asset_ids`, `animation`, y valida el
schema dentro del pipeline.

## 4. Puerta comercial fail-closed

```
python scripts/v8/policy_gate.py --selftest
  sapi            -> BLOCK  (SAPI no verificado para monetización)
  assets_ok       -> ALLOW  (HAND_L ... APPROVED + licencia VERIFIED)
  assets_unknown  -> BLOCK  (asset no registrado)
```

Con la voz real de un job (`voice.json`, SAPI): `decision: BLOCK`.

## 5. RAG temático — 0 huérfanos

```
python -c "... chunk_text/extract_sections/nearest_section_index ..."
chunks 384  secciones 735  orphans 0
```

El vínculo chunk↔sección se resuelve por **solapamiento de rangos**
(`inicio,fin` en el texto normalizado), no por índice de chunk.

## 6. Pipeline E2E (canned, 15 s, voz VoiceStudio)

```
python scripts/pipeline.py --job-id demo-v8-voicestudio --topic "linea de la vida" \
    --duration 15 --mode canned --engine voicestudio --format test_30s
{"status": "done", "video": ".../demo-v8-voicestudio.mp4", "short": ".../demo-v8-voicestudio_short.mp4"}
```

Estados de los pasos: todos `done`, salvo `extract_pdf/rag_ingest: skipped`.
Voz: VoiceStudio OmniVoice (femenina, 24 kHz mono → 44100 estéreo en mux).
Archivos de ejemplo en `examples/` para validación externa.

## 7. Audio y encuadre de ambos formatos

```
ffprobe 16:9  -> 1920x1080, aac 44100 Hz 2 canales
ffprobe 9:16  -> 1080x1920, aac 44100 Hz 2 canales
```

El short 9:16 se compone y renderiza **nativo** (no es un recorte del 16:9),
así la mano nunca queda cortada. El compositor encuadra la mano por su
`content_bbox()` para que llene el alto del cuadro.

## 8. Auditoría V7

```
python scripts/v7/audit_v7.py
```

Sin rutas absolutas (salvo la nota de sesión `validación_claude.md`, no
versionada). Los avisos de "posible secreto DB" son `postgres:postgres@
127.0.0.1` (localhost) y los de ortografía del propio `audit_v7.py` y
`validate_spanish_text.py` son cadenas literales de su tabla de detección
(falsos positivos conocidos).

## Limitación conocida

La duración real del video resultante la fija el audio TTS. VoiceStudio
narra el guion completo (~47 s) aunque se pida `--duration 15`. El pipeline
sincroniza las duraciones de escena al audio real. Para clips exactos
hace falta narración cortada o un TTS con control de duración.

La mano vectorial tiene buena forma y 5 dedos, pero el usuario reporta
que la proporción/pulgar no es perfecta. Se sigue iterando.
