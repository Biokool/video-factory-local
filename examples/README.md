# Ejemplos para validación

Archivos de ejemplo del pipeline V9 con mano anatómica sólida (PNG Cairo),
voz VoiceStudio y textos legibles.

## Contenido

| Archivo | Formato | Descripción |
|---------|---------|-------------|
| `demo_16x9.mp4` | 1920×1080 | Video completo 16:9 (~8.5 MB) |
| `demo_short_9x16.mp4` | 1080×1920 | Short 9:16 nativo (~8.7 MB) |
| `frame_01.jpg` - `frame_08.jpg` | 1920×1080 | Frames del video |

## Qué validar

### Mano (PNG sólido Cairo)
- La mano debe ser una **forma sólida** (no un wireframe/outline)
- Debe tener **color de piel** relleno (#FADEC9 → #E8B88A)
- **5 dedos visibles** con punta redondeada
- Dedos **claramente separados**
- Líneas de la palma **gruesas y coloridas** (cyan, rosa, naranja, amarillo)
- Montes como **círculos de color** (rojo, amarillo, verde, azul, blanco)
- Borde suave alrededor de la mano

### Audio
- Narración pausada con VoiceStudio (humana)

### Textos
- Títulos grandes (60px), labels legibles (30px)
