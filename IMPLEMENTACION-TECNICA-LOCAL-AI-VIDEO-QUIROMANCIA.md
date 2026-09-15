# IMPLEMENTACIÓN TÉCNICA — LOCAL AI VIDEO QUIROMANCIA

Documento para la IA agente encargada de construir, configurar, validar y dejar funcional el entorno local.

# 1. OBJETIVO DEL SISTEMA

Construir localmente una aplicación capaz de recibir:

- tema;
- contexto;
- duración;
- estilo;
- plataforma;
- idioma;
- información del contenido de quiromancia;

y producir:

1. guion;
2. storyboard JSON;
3. selección de assets;
4. imágenes consistentes;
5. gráficos de palma;
6. animaciones;
7. voz opcional local;
8. subtítulos;
9. video final MP4.

Ejemplo:

Entrada:

> "Explica la línea del corazón desde una perspectiva terapéutica y no adivinatoria."

Salida:

```text
script.json
storyboard.json
scene_001.png
scene_002.png
scene_003.png
...
audio.wav
subtitles.srt
video_final.mp4
```

---

# 2. ARQUITECTURA

```text
                    ┌──────────────────────┐
                    │      OLLAMA          │
                    │    Qwen 7B/8B        │
                    └──────────┬───────────┘
                               │
                               ▼
                     STORYBOARD JSON
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
    HAND ASSETS           SVG ASSETS          AI IMAGE
    deterministas         deterministas       generación
          │                    │                    │
          │                    │             ┌──────┴──────┐
          │                    │             │ ComfyUI     │
          │                    │             │ SDXL/otros  │
          │                    │             └──────┬──────┘
          │                    │                    │
          └────────────────────┼────────────────────┘
                               ▼
                    COMPOSITOR LOCAL
                  SVG + Pillow + OpenCV
                               │
                               ▼
                         ANIMACIÓN
                               │
                               ▼
                            FFmpeg
                               │
                               ▼
                         VIDEO FINAL
```

---

# 3. SOFTWARE PRINCIPAL

## 3.1 Ollama

Uso:

- LLM local;
- generación de guion;
- estructuración JSON;
- selección de assets;
- generación de prompts;
- validación lógica.

Ollama tiene licencia MIT en su repositorio.

Repositorio:

https://github.com/ollama/ollama

Modelo inicial:

`Qwen/Qwen2.5-7B-Instruct`

La ficha de Hugging Face indica licencia Apache-2.0.

Repositorio/modelo:

https://huggingface.co/Qwen/Qwen2.5-7B-Instruct

Si el proyecto ya utiliza otro Qwen 7B/8B, conservarlo inicialmente y hacer una prueba de compatibilidad.

---

# 4. COMFYUI

Usar ComfyUI como motor local de generación visual.

Repositorio oficial:

https://github.com/Comfy-Org/ComfyUI

Funciones:

- carga de modelos;
- workflows reproducibles;
- ControlNet;
- LoRA;
- image conditioning;
- generación local;
- API local;
- automatización.

No usar API Nodes de servicios cerrados.

Instalar únicamente componentes locales.

## Estructura

```text
comfyui/
├── models/
│   ├── checkpoints/
│   ├── controlnet/
│   ├── clip/
│   ├── vae/
│   ├── loras/
│   ├── ipadapter/
│   └── embeddings/
├── custom_nodes/
├── input/
├── output/
└── workflows/
```

---

# 5. MODELO DE IMAGEN PRINCIPAL

## Primera opción: SDXL Base 1.0

Modelo:

`stabilityai/stable-diffusion-xl-base-1.0`

La ficha oficial muestra licencia OpenRAIL++.

No describir OpenRAIL++ como una licencia OSI "open source" sin matices. En el inventario de licencias debe aparecer como:

`MODEL_LICENSE = OpenRAIL++`

El modelo puede ejecutarse localmente.

Repositorio:

https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0

El archivo de pesos principal es de aproximadamente 6.94 GB en la distribución publicada.

## Política del proyecto

SDXL es aceptable para este proyecto siempre que se respeten sus términos de licencia y las condiciones comerciales vigentes.

No asumir que "gratuito" equivale a "sin restricciones".

---

# 6. MODELO ALTERNATIVO DE BAJO CONSUMO

Si la GPU no permite SDXL adecuadamente:

- usar un checkpoint SD 1.5 compatible con ControlNet;
- preferir modelos con licencia claramente documentada;
- registrar cada checkpoint individual en `licenses/models.csv`.

No descargar checkpoints aleatorios desde páginas no oficiales.

---

# 7. CONTROLNET

ControlNet será una pieza fundamental para conservar estructura.

Repositorio:

https://github.com/lllyasviel/ControlNet

Usos prioritarios:

1. Canny
2. Lineart
3. OpenPose
4. Depth

Para este proyecto:

### Canny

Preserva:

- contorno;
- dedos;
- silueta.

### Lineart

Preserva:

- líneas de dibujo;
- estructura de ilustración.

### OpenPose/hand pose

Preserva:

- posición;
- articulación;
- gesto.

### Depth

Útil para imágenes más realistas.

Para el estilo infográfico se utilizarán primero:

`Lineart + Canny`

---

# 8. IP-ADAPTER

IP-Adapter puede utilizarse para referencia visual.

Repositorio:

https://github.com/tencent-ailab/IP-Adapter

La implementación original declara Apache-2.0.

Sin embargo, cualquier implementación específica de ComfyUI debe revisarse individualmente.

Por ejemplo, `ComfyUI_IPAdapter_plus` actualmente declara GPL-3.0 en su proyecto.

No mezclar licencias sin registrarlas.

Uso:

- conservar estilo;
- referencia visual;
- composición;
- consistencia.

No hacerlo obligatorio en la primera versión.

---

# 9. MEDIAPIPE

Usar MediaPipe para detectar landmarks de manos.

Repositorio:

https://github.com/google-ai-edge/mediapipe

Hand Landmarker:

- 21 landmarks por mano;
- posición;
- geometría;
- seguimiento.

Licencia del código: Apache-2.0.

MediaPipe NO será el generador de la ilustración.

Será el sistema de geometría.

Pipeline:

```text
imagen
  ↓
MediaPipe Hand Landmarker
  ↓
21 landmarks
  ↓
normalización
  ↓
SVG / máscara / guía
```

---

# 10. OPENCV

Usar OpenCV para:

- máscaras;
- contornos;
- detección;
- transformación;
- composición;
- procesamiento de imágenes;
- extracción de lineart;
- postprocesamiento.

Instalar desde PyPI mediante un entorno virtual.

No depender de servicios externos.

---

# 11. PILLOW

Usar Pillow para:

- composición;
- resize;
- overlays;
- conversión de formatos;
- creación de imágenes;
- operaciones simples.

---

# 12. SVG

Los gráficos educativos se deben generar preferentemente en SVG.

Ventajas:

- vectorial;
- escalable;
- texto perfecto;
- líneas perfectas;
- animable;
- determinista.

No generar con IA:

- nombres de líneas;
- flechas;
- números;
- círculos;
- etiquetas;
- iconos.

---

# 13. FFMPEG

Usar FFmpeg para:

- convertir imágenes a video;
- combinar audio;
- subtítulos;
- transiciones;
- concatenación;
- codificación H.264/H.265 cuando corresponda.

FFmpeg utiliza LGPL 2.1+ para la mayor parte del proyecto; algunos componentes opcionales tienen GPL. El build utilizado debe documentarse.

Repositorio:

https://github.com/FFmpeg/FFmpeg

Para evitar problemas de licencia, no activar componentes GPL innecesarios.

---

# 14. REGLA DE LICENCIAS

Crear:

```text
licenses/
├── SOFTWARE.md
├── MODELS.md
├── ASSETS.md
└── THIRD_PARTY.md
```

Ejemplo:

```csv
component,type,license,commercial_use,source,notes
Ollama,software,MIT,YES,https://github.com/ollama/ollama,
Qwen2.5-7B-Instruct,model,Apache-2.0,YES,https://huggingface.co/Qwen/Qwen2.5-7B-Instruct,
MediaPipe,software,Apache-2.0,YES,https://github.com/google-ai-edge/mediapipe,
IP-Adapter,software/model,Apache-2.0,VERIFY,https://github.com/tencent-ailab/IP-Adapter,
SDXL,model,OpenRAIL++,VERIFY,https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0,
FFmpeg,software,LGPL-2.1+,VERIFY,https://ffmpeg.org/,
```

IMPORTANTE:

"commercial_use" debe significar "según la licencia actual y las condiciones del modelo", no una garantía jurídica.

---

# 15. PERFIL DE HARDWARE

El instalador debe detectar:

- sistema operativo;
- CPU;
- RAM;
- GPU;
- VRAM;
- CUDA;
- versión de Python.

Comando conceptual:

```bash
python scripts/system_check.py
```

Salida:

```text
GPU: NVIDIA ...
VRAM: 12 GB
CUDA: ...
RAM: ...
Python: ...
Recommended profile: SDXL_LOW_VRAM
```

---

# 16. PERFILES DE VRAM

## Perfil A: 4–6 GB

Objetivo:

- SD 1.5;
- baja resolución;
- batch 1;
- CPU offload si es necesario;
- ControlNet individual;
- no utilizar varios modelos simultáneos.

## Perfil B: 8 GB

Objetivo:

- SDXL optimizado;
- batch 1;
- resolución 768x1024 o equivalente;
- low-VRAM;
- ControlNet uno por vez.

## Perfil C: 12 GB

Objetivo:

- SDXL;
- ControlNet;
- IP-Adapter opcional;
- buena producción local.

## Perfil D: 16 GB

Objetivo:

- SDXL cómodo;
- múltiples controles según workflow;
- modelos cuantizados más pesados.

## Perfil E: 24 GB+

Objetivo:

- FLUX u otros modelos grandes cuantizados;
- workflows avanzados.

El instalador nunca debe asumir una VRAM concreta.

---

# 17. NO INSTALAR FLUX EN LA PRIMERA FASE

FLUX se deja como módulo opcional.

Motivos:

- mayor consumo;
- mayor tiempo;
- no es necesario para resolver el problema fundamental;
- la consistencia de las manos se resolverá mediante assets + geometría + ControlNet.

Cuando el pipeline SDXL funcione:

```text
SDXL → validar
↓
ControlNet → validar
↓
MediaPipe → validar
↓
SVG → validar
↓
video → validar
↓
FLUX opcional
```

---

# 18. BIBLIOTECA MAESTRA DE MANOS

Crear:

```text
assets/hands/
├── left/
├── right/
├── dorsal/
├── side/
├── palms/
├── poses/
├── fingers/
├── masks/
├── lineart/
├── canny/
├── depth/
└── svg/
```

---

# 19. MANOS MAESTRAS OBLIGATORIAS

Crear inicialmente:

```text
LH-01 left_palm_front
RH-01 right_palm_front

LH-02 left_palm_angled
RH-02 right_palm_angled

LH-03 left_dorsal
RH-03 right_dorsal

LH-04 left_side
RH-04 right_side

HAND-05 semi_closed
HAND-06 fist

PAIR-01 both_palms_front
PAIR-02 both_dorsal
```

Total inicial:

**14 assets maestros.**

---

# 20. FORMATO DE CADA MANO

Cada asset debe tener:

```text
HAND_ID/
├── master.png
├── master.webp
├── lineart.png
├── canny.png
├── mask.png
├── depth.png
├── landmarks.json
├── hand.svg
├── metadata.json
└── LICENSE.txt
```

Ejemplo:

```text
LH-01/
├── master.png
├── lineart.png
├── canny.png
├── mask.png
├── landmarks.json
├── hand.svg
└── metadata.json
```

---

# 21. METADATA DE LA MANO

Ejemplo:

```json
{
  "id": "LH-01",
  "side": "left",
  "view": "palm_front",
  "style": "educational_infographic",
  "canonical": true,
  "source": "generated_or_original",
  "license": "project_owned",
  "landmarks": 21,
  "resolution": [2048, 2048]
}
```

---

# 22. DEDOS

Crear assets independientes:

```text
assets/hands/fingers/
├── thumb/
├── index/
├── middle/
├── ring/
└── little/
```

Cada dedo:

```text
extended
flexed
side
tip
joint
```

No es obligatorio generar todos en la primera prueba.

---

# 23. POSES

Crear:

```text
POSE-01 open_flat
POSE-02 open_relaxed
POSE-03 fingers_extended
POSE-04 fingers_together
POSE-05 fingers_separated
POSE-06 thumb_out
POSE-07 thumb_in
POSE-08 semi_closed
POSE-09 pointing
POSE-10 palm_up
POSE-11 palm_down
POSE-12 diagonal
```

---

# 24. ¿CÓMO CREAR LAS MANOS MAESTRAS?

Preferencia:

### Método 1

Fotografías propias controladas.

### Método 2

Modelo 3D con licencia compatible.

### Método 3

Generación local con SDXL/otro modelo y posterior corrección.

No utilizar fotografías de Internet sin licencia.

La opción más recomendable para una biblioteca profesional:

**modelo anatómico/asset propio + vectorización/render.**

---

# 25. ESTILO VISUAL MAESTRO

Definir un único estilo:

```text
style_id:
therapeutic_infographic_v1
```

Características:

- ilustración educativa;
- no fotorealista;
- líneas limpias;
- anatomía clara;
- fondo neutro;
- colores limitados;
- contraste alto;
- sin texto generado por IA;
- sin estética esotérica exagerada;
- aspecto profesional;
- fácil lectura móvil.

---

# 26. LÍNEAS DE QUIROMANCIA

Crear SVGs:

```text
assets/palm_lines/
├── life_line.svg
├── head_line.svg
├── heart_line.svg
├── fate_line.svg
├── sun_line.svg
├── mercury_line.svg
├── minor_lines.svg
└── custom/
```

IMPORTANTE:

Los nombres y significados exactos deben proceder de la base documental del cliente.

El sistema NO debe inventar doctrinas de quiromancia.

---

# 27. ZONAS

Crear:

```text
assets/zones/
├── venus.svg
├── jupiter.svg
├── saturn.svg
├── apollo.svg
├── mercury.svg
├── moon.svg
├── mars_positive.svg
├── mars_negative.svg
└── custom/
```

Cada zona debe incluir:

```text
zone.svg
zone_mask.png
metadata.json
```

---

# 28. SÍMBOLOS

Crear:

```text
assets/symbols/
├── arrow.svg
├── circle.svg
├── pointer.svg
├── magnifier.svg
├── highlight.svg
├── number.svg
├── check.svg
├── cross.svg
├── info.svg
└── question.svg
```

---

# 29. MOTOR DE STORYBOARD

Qwen debe producir JSON estricto.

Ejemplo:

```json
{
  "video": {
    "topic": "linea_del_corazon",
    "style": "therapeutic_infographic_v1",
    "duration_seconds": 35,
    "aspect_ratio": "9:16"
  },
  "scenes": [
    {
      "id": 1,
      "duration": 5,
      "asset": "LH-01",
      "animation": "slow_zoom"
    },
    {
      "id": 2,
      "duration": 6,
      "asset": "LH-01",
      "overlay": "heart_line",
      "animation": "draw_line"
    },
    {
      "id": 3,
      "duration": 7,
      "asset": "LH-01",
      "overlay": "heart_line",
      "symbol": "arrow",
      "animation": "point"
    }
  ]
}
```

---

# 30. VALIDACIÓN DEL JSON

Nunca ejecutar directamente JSON generado por Qwen.

Pipeline:

```text
Qwen
 ↓
JSON
 ↓
JSON Schema
 ↓
validator
 ↓
sanitizer
 ↓
renderer
```

Si falla:

```text
JSON inválido
 ↓
Qwen recibe error
 ↓
corrige
 ↓
validación
```

Máximo 2 reintentos.

---

# 31. JSON SCHEMA

Crear:

```text
schemas/storyboard.schema.json
```

Debe validar:

- scene.id;
- duration;
- asset;
- overlay;
- animation;
- camera;
- text;
- audio;
- transitions.

No permitir rutas arbitrarias.

---

# 32. SEGURIDAD DE ASSETS

Qwen solamente puede seleccionar IDs existentes.

Ejemplo válido:

```text
LH-01
heart_line
arrow
```

No válido:

```text
../../../../archivo
```

El renderer debe rechazar rutas externas.

---

# 33. COMPOSITOR

Crear:

```text
render/
├── compose_scene.py
├── svg_renderer.py
├── animation.py
├── image_processor.py
└── validation.py
```

Función:

```python
render_scene(scene_json)
```

Entrada:

```text
storyboard.json
```

Salida:

```text
scene_001.png
scene_002.png
...
```

---

# 34. ANIMACIONES DETERMINISTAS

Implementar inicialmente:

```text
fade_in
fade_out
slow_zoom
pan_left
pan_right
draw_line
draw_circle
highlight
pointer
text_reveal
```

No utilizar IA de video para estas animaciones.

Son más rápidas, consistentes y gratuitas.

---

# 35. VIDEO

Usar FFmpeg:

```text
PNG frames
+
audio.wav
+
subtitles.srt
        ↓
FFmpeg
        ↓
video.mp4
```

Formato inicial:

```text
1080x1920
30 FPS
H.264
AAC
```

Si la GPU no soporta encoding hardware, utilizar CPU.

---

# 36. PRIMER MVP

No intentar producir videos completos inicialmente.

Crear este test:

## Test 1

Una mano izquierda abierta.

## Test 2

Agregar línea del corazón.

## Test 3

Animar la línea.

## Test 4

Agregar texto.

## Test 5

Exportar 5 segundos.

## Test 6

Agregar narración.

## Test 7

Exportar video vertical.

Solo después:

## Test 8

Generar automáticamente desde Qwen.

---

# 37. WORKFLOW COMFYUI #1

Nombre:

`01_hand_base.json`

Objetivo:

generar/transformar mano base.

Entrada:

```text
master hand
```

Salida:

```text
hand_styled.png
```

---

# 38. WORKFLOW #2

`02_hand_lineart.json`

Entrada:

```text
master hand
```

Procesamiento:

```text
Lineart
```

Salida:

```text
lineart.png
```

---

# 39. WORKFLOW #3

`03_hand_controlnet.json`

Entrada:

```text
lineart.png
```

Control:

```text
ControlNet Lineart
```

Salida:

```text
consistent_hand.png
```

---

# 40. WORKFLOW #4

`04_hand_reference.json`

Entrada:

```text
master.png
```

Opcional:

```text
IP-Adapter
```

Salida:

```text
style_consistent.png
```

---

# 41. REGLA DE CONSISTENCIA

Cuando la escena solamente necesita explicar una línea:

NO regenerar la mano.

Usar:

```text
same_hand.png
+
different SVG overlays
```

Regenerar únicamente cuando:

- cambia pose;
- cambia vista;
- cambia ambiente;
- cambia composición.

Esto reduce costo computacional y variabilidad.

---

# 42. PIPELINE MEDIA PIPE

Crear:

```text
tools/hand_landmarks.py
```

Entrada:

```text
master.png
```

Salida:

```json
{
  "hand_id": "LH-01",
  "landmarks": [
    {"x": 0.42, "y": 0.51, "z": 0.01}
  ]
}
```

Los 21 landmarks deben almacenarse.

---

# 43. GENERACIÓN DE SVG DE MANO

Crear:

```text
tools/generate_hand_svg.py
```

Pipeline:

```text
landmarks.json
 ↓
bone connections
 ↓
stroke
 ↓
SVG
```

Esto permite generar una mano esquemática sin IA.

---

# 44. VENTAJA

La misma mano:

```text
SVG
PNG
Lineart
Canny
Mask
Depth
```

puede reutilizarse.

---

# 45. MODO DE PRODUCCIÓN

Cada video debe tener su propio directorio:

```text
projects/
└── video_0001/
    ├── input.json
    ├── script.json
    ├── storyboard.json
    ├── scenes/
    ├── audio/
    ├── subtitles/
    ├── intermediate/
    ├── final/
    └── manifest.json
```

---

# 46. MANIFEST

Registrar:

```json
{
  "project": "video_0001",
  "created_at": "...",
  "ollama_model": "...",
  "image_model": "...",
  "workflow": "...",
  "seed": 12345,
  "assets": [
    "LH-01",
    "heart_line",
    "arrow"
  ]
}
```

Esto permite reproducibilidad.

---

# 47. SEMILLAS

Cada escena generativa debe almacenar:

```text
seed
model
sampler
steps
cfg
resolution
controlnet_weight
ipadapter_weight
```

No perder estos valores.

---

# 48. CACHÉ

Crear:

```text
cache/
├── llm/
├── images/
├── controlnet/
├── svg/
├── audio/
└── video/
```

Si una entrada es idéntica:

**no volver a procesar.**

---

# 49. OPTIMIZACIÓN DE VRAM

Reglas:

1. Batch = 1.
2. Liberar modelos entre tareas pesadas.
3. Evitar tener SDXL + ControlNet + otro modelo simultáneamente si no es necesario.
4. Usar resolución moderada durante desarrollo.
5. Generar primero a resolución de trabajo.
6. Upscale solamente al final.
7. Utilizar CPU offload cuando sea necesario.
8. Evitar FLUX hasta que el pipeline SDXL esté validado.

---

# 50. NO GENERAR 1080x1920 DIRECTAMENTE

Durante pruebas:

```text
512–768 px
```

Después:

```text
768–1024
```

Finalmente:

```text
1080x1920
```

El tamaño exacto dependerá del modelo y la VRAM.

---

# 51. ESTRUCTURA DE PROMPT

Qwen debe separar:

```text
subject
style
composition
lighting
background
negative
```

Ejemplo:

```json
{
  "subject": "educational anatomical hand illustration",
  "style": "clean therapeutic infographic",
  "composition": "left palm centered",
  "lighting": "soft neutral",
  "background": "white",
  "negative": [
    "extra fingers",
    "deformed hand",
    "text",
    "watermark",
    "photorealism"
  ]
}
```

---

# 52. NEGATIVE PROMPT PARA MANOS

Base:

```text
extra fingers,
missing fingers,
six fingers,
deformed fingers,
fused fingers,
duplicate hand,
malformed palm,
extra thumb,
missing thumb,
distorted anatomy,
broken joints,
bad proportions,
text,
letters,
watermark,
logo
```

No depender exclusivamente del negative prompt.

La geometría/control es más importante.

---

# 53. GENERACIÓN DE MINIATURAS

Para thumbnails:

usar generación separada.

No reutilizar necesariamente la mano técnica.

Puede utilizar:

- mano;
- lupa;
- fondo;
- contraste;
- elemento gráfico.

El texto debe añadirse posteriormente.

---

# 54. AUDIO LOCAL

El audio es opcional para MVP.

Si se implementa:

- usar un TTS local con licencia compatible;
- mantenerlo modular;
- no depender de servicios cloud.

Crear interfaz:

```text
tts_provider = local
```

El sistema debe poder funcionar sin TTS.

---

# 55. N8N

n8n puede utilizarse como orquestador si ya forma parte del entorno.

No enviar información a nodos cloud.

Flujo:

```text
Webhook/local input
 ↓
Ollama
 ↓
JSON validator
 ↓
Asset selector
 ↓
ComfyUI local API
 ↓
Renderer
 ↓
FFmpeg
 ↓
Output
```

---

# 56. API LOCAL

ComfyUI debe exponerse únicamente en localhost durante el MVP:

```text
127.0.0.1
```

No abrirlo públicamente.

Ollama igualmente:

```text
localhost
```

---

# 57. PRUEBA END-TO-END

Entrada:

```text
Tema:
"Línea del corazón"

Estilo:
"infografía terapéutica"

Duración:
15 segundos

Formato:
9:16
```

Qwen produce:

```text
script
storyboard
```

Renderer selecciona:

```text
LH-01
heart_line
arrow
```

Compositor:

```text
mano
+
línea
+
flecha
+
texto
```

Animación:

```text
fade
zoom
draw_line
arrow
```

FFmpeg:

```text
video_final.mp4
```

---

# 58. CRITERIOS DE ACEPTACIÓN

El MVP se considera correcto si:

- [ ] no utiliza API externa;
- [ ] funciona sin Internet después de instalar modelos;
- [ ] genera una mano válida;
- [ ] conserva cinco dedos;
- [ ] conserva la misma mano en 3 escenas;
- [ ] la línea aparece exactamente donde se definió;
- [ ] el texto se renderiza correctamente;
- [ ] genera MP4;
- [ ] reproduce audio opcional;
- [ ] produce video vertical;
- [ ] puede repetirse con la misma semilla;
- [ ] registra modelos y licencias;
- [ ] no requiere pago.

---

# 59. PRUEBA DE CONSISTENCIA

Generar:

```text
scene_01
scene_02
scene_03
```

Las tres deben utilizar:

```text
LH-01
```

No deben regenerarse tres manos diferentes.

La diferencia visual debe provenir principalmente de:

```text
SVG overlays
animation
camera
background
highlight
```

---

# 60. PRUEBA DE VRAM

Crear:

```text
scripts/benchmark.py
```

Medir:

- VRAM inicial;
- VRAM máxima;
- tiempo de generación;
- resolución;
- steps;
- modelo;
- ControlNet;
- CPU RAM.

Guardar:

```text
benchmarks/results.json
```

---

# 61. MODO FALLBACK

Si no hay GPU:

```text
CPU mode
```

Debe seguir funcionando:

- Qwen CPU;
- SVG;
- MediaPipe CPU;
- OpenCV CPU;
- FFmpeg CPU.

La generación difusiva puede ser deshabilitada o funcionar a baja velocidad.

---

# 62. DETECCIÓN AUTOMÁTICA DE MODELO

Crear:

```text
config/hardware.json
```

Ejemplo:

```json
{
  "vram_gb": 8,
  "profile": "SDXL_LOW_VRAM",
  "image_model": "sdxl",
  "controlnet": true,
  "ip_adapter": false,
  "flux": false
}
```

---

# 63. FASES DE IMPLEMENTACIÓN

## FASE 0 — Auditoría

Comprobar:

- SO;
- GPU;
- VRAM;
- Python;
- Git;
- FFmpeg;
- Ollama;
- Qwen.

Resultado:

`environment_report.json`

---

## FASE 1 — Base Python

Crear:

```text
.venv
requirements.txt
pyproject.toml
```

Instalar:

```text
torch
opencv-python
pillow
numpy
mediapipe
pydantic
jsonschema
requests
```

Versiones deben fijarse después de probar compatibilidad con la GPU.

---

## FASE 2 — ComfyUI

Instalar localmente.

Validar:

```text
ComfyUI abre
workflow básico funciona
API local funciona
```

---

## FASE 3 — SDXL

Descargar únicamente desde fuente oficial.

Validar:

```text
prompt → imagen
```

---

## FASE 4 — ControlNet

Instalar:

```text
Canny
Lineart
```

Validar:

```text
input structure → output structure
```

---

## FASE 5 — MediaPipe

Validar:

```text
hand image → 21 landmarks
```

---

## FASE 6 — Hand Asset Library

Crear:

```text
LH-01
RH-01
LH-02
RH-02
...
```

---

## FASE 7 — SVG

Crear:

```text
hand.svg
heart_line.svg
life_line.svg
head_line.svg
arrow.svg
```

---

## FASE 8 — Compositor

Combinar:

```text
hand
+
line
+
zone
+
arrow
+
text
```

---

## FASE 9 — Animación

Implementar:

```text
zoom
pan
fade
draw_line
highlight
```

---

## FASE 10 — FFmpeg

Crear video.

---

## FASE 11 — Ollama

Qwen produce storyboard.

---

## FASE 12 — Automatización

Integrar:

```text
n8n
→ Ollama
→ ComfyUI
→ renderer
→ FFmpeg
```

---

# 64. CHECKPOINT OBLIGATORIO

Después de cada fase:

```text
PASS
FAIL
```

Si FAIL:

- guardar log;
- no avanzar;
- corregir;
- volver a ejecutar prueba.

Crear:

```text
validation/
├── phase_00.json
├── phase_01.json
├── phase_02.json
...
```

---

# 65. LOGGING

Crear:

```text
logs/
├── system.log
├── comfyui.log
├── renderer.log
├── ollama.log
└── ffmpeg.log
```

No registrar información sensible.

---

# 66. MODO OFFLINE

Una vez descargados:

- repositorios;
- Python packages;
- modelos;
- assets;

el pipeline debe funcionar sin conexión.

Crear:

```text
scripts/offline_test.py
```

El script debe bloquear/avisar cualquier intento accidental de conexión externa.

---

# 67. MANIFEST DE MODELOS

Crear:

```text
models/manifest.json
```

Ejemplo:

```json
{
  "models": [
    {
      "id": "sdxl-base-1.0",
      "source": "official",
      "license": "OpenRAIL++",
      "local_only": true
    }
  ]
}
```

---

# 68. VERSIONADO

Guardar:

```text
model version
workflow version
asset version
prompt version
schema version
```

Un video debe poder reproducirse posteriormente.

---

# 69. NO DEPENDER DE HYPERFRAME

HyperFrame puede investigarse como módulo adicional.

No debe ser dependencia crítica.

El pipeline principal debe funcionar:

```text
Ollama
+
ComfyUI
+
SDXL
+
ControlNet
+
MediaPipe
+
SVG
+
FFmpeg
```

---

# 70. PRINCIPIO ARQUITECTÓNICO CENTRAL

La IA genera:

```text
ideas
prompts
variaciones
fondos
estética
storyboard
```

El software determinista controla:

```text
manos
líneas
zonas
texto
flechas
animaciones
duración
composición
video
```

Esto es lo que permitirá escalar el sistema.

---

# 71. RESULTADO FINAL ESPERADO

El usuario debe poder ejecutar:

```bash
python generate_video.py \
  --topic "linea_del_corazon" \
  --duration 30 \
  --style therapeutic_infographic \
  --format 9:16
```

Y obtener:

```text
output/
└── linea_del_corazon/
    ├── script.json
    ├── storyboard.json
    ├── scenes/
    ├── audio/
    ├── subtitles.srt
    └── final.mp4
```

---

# 72. PRINCIPIO DE COSTO

El sistema no debe generar costo por:

- tokens;
- APIs;
- generación cloud;
- almacenamiento cloud;
- video cloud;
- TTS cloud.

Los únicos costos posibles son los del propio hardware/electricidad/almacenamiento del usuario.

---

# 73. IMPORTANTE SOBRE "GRATUITO"

"Gratis" en este documento significa:

- software descargable;
- ejecución local;
- sin pago por inferencia;
- sin API obligatoria.

No significa que todas las licencias sean idénticas ni que todos los modelos tengan licencia OSI.

El sistema debe respetar la licencia específica de cada componente.

Por eso:

**no descargar modelos adicionales automáticamente sin verificar su licencia.**

---

# 74. PRIMER OBJETIVO REAL

NO intentar generar un video de 60 segundos inmediatamente.

Primero conseguir:

```text
UNA MANO
↓
MISMA MANO
↓
3 ESCENAS
↓
LÍNEA DE QUIROMANCIA
↓
ANIMACIÓN
↓
TEXTO
↓
5–15 SEGUNDOS
```

Cuando esto sea estable:

```text
15 segundos
↓
30 segundos
↓
60 segundos
↓
producción masiva
```

---

# 75. DEFINICIÓN DE "TERMINADO"

La implementación solamente se considera terminada cuando:

1. El entorno puede instalarse desde cero.
2. Todos los modelos están documentados.
3. Las licencias están registradas.
4. No depende de servicios cloud.
5. Qwen genera JSON válido.
6. El JSON selecciona únicamente assets existentes.
7. MediaPipe detecta manos.
8. ControlNet conserva estructura.
9. La misma mano aparece consistentemente.
10. SVG genera líneas y símbolos.
11. El compositor genera escenas.
12. FFmpeg genera MP4.
13. Existe un test end-to-end.
14. Existe un benchmark de VRAM.
15. Existe un modo low-VRAM.
16. Existe un modo offline.
17. Todos los pasos tienen validación.
18. Los errores quedan registrados.
19. Se puede reproducir una escena usando su seed/manifest.
20. No existe una dependencia obligatoria de una API de pago.

---

# 76. ORDEN DE EJECUCIÓN PARA LA IA IMPLEMENTADORA

La IA que reciba este documento debe ejecutar estrictamente:

```text
1. Auditar hardware
2. Auditar software existente
3. Crear entorno Python
4. Validar Ollama
5. Validar Qwen
6. Instalar ComfyUI
7. Validar API local
8. Instalar modelo de imagen
9. Crear workflow básico
10. Instalar ControlNet
11. Validar Canny
12. Validar Lineart
13. Instalar MediaPipe
14. Crear Hand Asset Library
15. Crear landmarks
16. Crear SVG
17. Crear líneas de quiromancia
18. Crear compositor
19. Crear animaciones
20. Instalar/validar FFmpeg
21. Crear video de prueba
22. Crear JSON Schema
23. Conectar Qwen
24. Automatizar storyboard
25. Integrar n8n
26. Ejecutar prueba end-to-end
27. Ejecutar benchmark
28. Ejecutar prueba offline
29. Documentar instalación
30. Entregar entorno funcional
```

**No saltar fases.**

---

# 77. CRITERIO DE DISEÑO FINAL

La solución no debe intentar ser una "IA que hace todo".

Debe ser:

**LLM + generador visual + geometría + gráficos vectoriales + compositor + encoder.**

Esta arquitectura es deliberadamente híbrida porque produce:

- mejor consistencia;
- menor VRAM;
- menor tiempo;
- menor variabilidad;
- mejor calidad;
- texto perfecto;
- manos consistentes;
- mayor reproducibilidad;
- cero costo por generación;
- posibilidad de escalar posteriormente.

---

# 78. FUENTES OFICIALES UTILIZADAS PARA LA ESPECIFICACIÓN

ComfyUI:
https://github.com/Comfy-Org/ComfyUI

Ollama:
https://github.com/ollama/ollama

Qwen2.5-7B-Instruct:
https://huggingface.co/Qwen/Qwen2.5-7B-Instruct

ControlNet:
https://github.com/lllyasviel/ControlNet

MediaPipe:
https://github.com/google-ai-edge/mediapipe

IP-Adapter:
https://github.com/tencent-ailab/IP-Adapter

SDXL:
https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0

FFmpeg:
https://ffmpeg.org/

---

# 79. NOTA DE LICENCIAS

La implementación debe conservar una copia o referencia de las licencias de todos los modelos y componentes utilizados.

Especial atención:

- SDXL utiliza OpenRAIL++;
- FFmpeg utiliza LGPL/GPL según componentes;
- IP-Adapter original declara Apache-2.0;
- MediaPipe declara Apache-2.0;
- Ollama declara MIT;
- Qwen2.5-7B-Instruct declara Apache-2.0.

Antes de uso comercial, revisar las condiciones vigentes de los modelos específicos y de cualquier checkpoint, LoRA, ControlNet o asset adicional.

---

# 80. ENTREGABLE FINAL DEL AGENTE IMPLEMENTADOR

Al terminar debe entregar:

```text
LOCAL-AI-VIDEO/
│
├── README.md
├── INSTALL.md
├── ARCHITECTURE.md
├── TROUBLESHOOTING.md
├── LICENSES.md
│
├── scripts/
├── src/
├── schemas/
├── assets/
├── workflows/
├── models/
├── licenses/
├── tests/
├── benchmarks/
├── logs/
├── projects/
└── output/
```

Debe incluir:

```text
README
+
instalador
+
validador
+
benchmark
+
workflow ComfyUI
+
assets de prueba
+
ejemplo end-to-end
```

FIN DEL DOCUMENTO.


