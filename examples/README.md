# Ejemplos para validación — Video Factory V9.1

Archivos de ejemplo del pipeline V9.1 con mano sólida PNG Cairo,
voz VoiceStudio y textos legibles.

## Archivos

### Videos
| Archivo | Formato | Tamaño | Descripción |
|---------|---------|--------|-------------|
| `demo_16x9.mp4` | 1920×1080 | ~8.5 MB | Video completo 16:9 |
| `demo_short_9x16.mp4` | 1080×1920 | ~8.7 MB | Short 9:16 nativo |

### Frames (1920×1080, ~120-177 KB c/u)
| Archivo | Escena | Contenido |
|---------|--------|-----------|
| `frame_01.jpg` | Escena 1 - frame 0 | Mano con líneas animándose |
| `frame_02.jpg` | Escena 1 - frame 75 | Líneas visibles |
| `frame_03.jpg` | Escena 1 - frame 150 | Líneas + montes apareciendo |
| `frame_04.jpg` | Escena 2 - frame 225 | Puntos de partida |
| `frame_05.jpg` | Escena 2 - frame 300 | Etiquetas visibles |
| `frame_06.jpg` | Escena 3 - frame 375 | Curva amplia vs estrecha (2 manos) |
| `frame_07.jpg` | Escena 3 - frame 450 | Comparación |
| `frame_08.jpg` | Escena 4 - frame 525 | Profundidad y vitalidad |
| `frame_09.jpg` | Escena 4 - frame 600 | Línea destacada |
| `frame_10.jpg` | Escena 4 - frame 675 | Cierre |

### Mano PNG (1024×1024, RGBA)
| Archivo | Descripción |
|---------|-------------|
| `hand_L_solid.png` | Mano izquierda sólida (Cairo fill+stroke) |
| `hand_R_solid.png` | Mano derecha sólida (espejo) |

## Qué validar para otra IA

### Mano
- ¿Tiene **5 dedos visibles** con punta redondeada?
- ¿Los dedos están **claramente separados**?
- ¿La palma es **sólida** (no wireframe/outline)?
- ¿Tiene **color de piel** relleno (no transparente)?
- ¿Las líneas son **gruesas y coloridas**?
- ¿Los montes son **círculos de color** visibles?

### Textos
- ¿Los títulos son **legibles** en 1080p?
- ¿Las etiquetas de líneas/montes son **grandes** (30px)?
- ¿El pie de página es visible pero no intrusivo?

### Audio
- ¿La narración suena **natural** (no robótica)?
- ¿Es **pausada** con énfasis en palabras clave?

### Encuadre
- En 16:9: ¿la mano está **centrada y completa**?
- En 9:16: ¿la mano está **completa** (no cortada)?

## Motor de voz

VoiceStudio (OmniVoice, TTS natural en GPU).
Licencia BLOCKED — solo validación interna.
