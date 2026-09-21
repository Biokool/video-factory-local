# Ejemplos para validación

Archivos de ejemplo del pipeline V8.1 con voz VoiceStudio (OmniVoice).

## Contenido

| Archivo | Formato | Descripción |
|---------|---------|-------------|
| `demo_16x9.mp4` | 1920×1080 | Video completo 16:9 (~6.7 MB, ~17s) |
| `demo_short_9x16.mp4` | 1080×1920 | Short 9:16 nativo (~7 MB) |
| `frame_01.jpg` - `frame_08.jpg` | 1920×1080 | Frames del video (cada ~2.5s) |

## Qué validar

### Mano (diseño vectorial)
- La mano debe tener **5 dedos visibles** con puntas redondeadas
- La palma debe ser proporcional (no gigante)
- La línea de la vida y otros trazos deben ser **legibles** (no blobs)
- Los montes (Júpiter, Saturno, Sol, Venus, Mercurio) deben tener **puntos de color** visibles
- Las etiquetas de texto deben ser **legibles** dentro del encuadre

### Audio (voz humana)
- La narración debe sonar **natural** (no robótica)
- El idioma es español de México
- La voz es femenina (VoiceStudio OmniVoice)

### Encuadre
- En 16:9: la mano debe estar centrada y completa
- En 9:16: la mano debe estar completa (no cortada a la mitad)
- Los textos/captions deben ser legibles en ambos formatos

## Motor de voz

Este demo usa **VoiceStudio** (OmniVoice, TTS natural en GPU). Para comparar con SAPI:
```powershell
python scripts/pipeline.py --job-id demo-sapi --topic "linea de la vida" --duration 15 --mode canned --engine sapi
```

## Nota de licencia

VoiceStudio/OmniVoice tiene licencia **BLOCKED** para uso comercial.
Este demo es solo para validación interna.
