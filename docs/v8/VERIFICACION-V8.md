# Verificación V8 — resultados medidos

Todos los comandos se ejecutan desde la raíz del proyecto con el intérprete
con dependencias. Resultados obtenidos en la máquina de producción.

## 1. Mano vectorial — 5 dedos (V8.1)

```
python scripts/v8/hand_geometry.py --selftest
{"side": "L", "digits": 5, "ok": true, "path_points": 67}
# espejo derecho:
{'side': 'R', 'digits': 5, 'ok': True, 'path_points': 67}
```

La mano se construye por primitivas anatómicas y se traza a un único path
Bézier cerrado (línea exterior continua, sin trazos internos). QA: 5
componentes con punta por encima de la palma, en ambas lateralidades.

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

## 6. Pipeline E2E (canned, 15 s)

```
python scripts/pipeline.py --job-id demo-v8-final --topic "linea de la vida" \
    --duration 15 --mode canned --format test_30s
{"status": "done", "video": ".../demo-v8-final.mp4", "short": ".../demo-v8-final_short.mp4"}
```

Estados de los pasos: todos `done`, salvo `policy_gate: warn` (BLOCK por
SAPI, correcto) y `extract_pdf/rag_ingest: skipped` (sin PDF nuevo).

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

La duración real del video resultante la fija el audio TTS: SAPI narra el
guion completo (~50 s) aunque se pida `--duration 15`. El pipeline
sincroniza las duraciones de escena al audio real. Para clips de 15 s
exactos hace falta narración corta o un TTS verificado comercialmente.
