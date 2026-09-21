# Ejemplos para validación

Archivos de ejemplo del pipeline V9 con mano anatómica, voz VoiceStudio
y textos legibles.

## Contenido

| Archivo | Formato | Descripción |
|---------|---------|-------------|
| `demo_16x9.mp4` | 1920×1080 | Video completo 16:9 (~10 MB, ~18s) |
| `demo_short_9x16.mp4` | 1080×1920 | Short 9:16 nativo (~11 MB) |
| `frame_01.jpg` - `frame_08.jpg` | 1920×1080 | Frames del video (cada ~2.5s) |

## Qué validar

### Mano (diseño V9 anatómico)
- La mano debe tener **5 dedos visibles** con punta redondeada
- Los dedos deben estar **claramente separados** (con gaps visibles)
- La palma debe ser **ancha y proporcional** (no un blob)
- El pulgar debe estar en el **lado izquierdo** (vista palmar)
- Las líneas deben ser **gruesas, coloridas y con guiones**
- Los montes deben ser **círculos de color** visibles
- Las etiquetas deben ser **grandes y legibles** en 1080p

### Audio (voz humana)
- Narración **pausada** con énfasis en palabras clave
- Voz femenina natural (VoiceStudio OmniVoice)
- Español de México

### Encuadre
- En 16:9: mano centrada y completa
- En 9:16: mano completa (no cortada)
- Títulos y labels **legibles** en ambos formatos

## Motor de voz

VoiceStudio (OmniVoice, TTS natural en GPU). Comparar con SAPI:
```powershell
python scripts/pipeline.py --job-id demo-sapi --topic "linea de la vida" --duration 60 --mode canned --engine sapi
```

## Licencia

VoiceStudio/OmniVoice: **BLOCKED** para uso comercial.
Solo validación interna.
