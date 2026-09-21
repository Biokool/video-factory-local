# Directrices de Marca — Video Factory

Guía visual y editorial para generar contenido con el motor V8.
Aplicable a **cualquier disciplina**: quiromancia, astrología, tarot,
numerología, etc.

---

## 1. Identidad visual

### Paleta base
| Elemento | Color | Uso |
|----------|-------|-----|
| Fondo | `#0a0e17` → `#1a2332` gradiente radial | Siempre oscuro (espacio/cosmos) |
| Texto principal | `#F1F5F9` (blanco suave) | Títulos, subtítulos |
| Texto secundario | `#94A3B8` (gris azulado) | Pie de página, metadata |
| Acento primario | `#3B82F6` (azul) | Botones, highlights |
| Acento secundario | `#A78BFA` (púrpura) | Subtítulos, decoración |

### Gradientes de fondo
- **Espacial**: estrellas punteadas sobre gradiente oscuro (ya implementado)
- **Luna**: gradiente azul-gris con textura sutil
- **Fuego**: gradiente naranja-rojizo con partículas
- **Agua**: gradiente azul-verde con ondulaciones

### Tipografía
| Elemento | Tamaño mínimo | Fuente |
|----------|--------------|--------|
| Título principal | 60px (1920×1080) | Segoe UI Bold |
| Subtítulo | 28px | Segoe UI |
| Etiquetas de features | 28-30px | Segoe UI Bold |
| Pie de página | 22px | Segoe UI |
| Subtítulos (SRT) | 38px | Arial Bold |

**Regla de oro**: Todo texto debe ser legible en un teléfono (1080p).
Si no se lee a 480p, es demasiado pequeño.

---

## 2. Mano (Quiromancia)

### Geometría
- **ViewBox**: 1024×1024
- **Palma**: ancha (380px), centrada en (512, 590)
- **Dedos**: 4 superiores + pulgar lateral, con punta redondeada
- **Dedos claramente separados** (gap mínimo 6px en base)
- **Pulgar**: origina desde la palma baja, ángulo ~35° hacia afuera
- **Muñeca**: base ancha que conecta con la palma

### Proporciones de dedos (relativo a palma)
| Dedo | Largo | Ancho base | Ancho punta |
|------|-------|-----------|-------------|
| Índice | 250px | 54px | 36px |
| Medio | 280px | 54px | 36px |
| Anular | 245px | 50px | 34px |
| Meñique | 195px | 44px | 30px |
| Pulgar | 210px | 56px | 38px |

### Estilo
- Relleno: gradiente radial `#FADEC9` → `#E8B88A` (piel suave)
- Borde: `#D4A574`, 4px, `stroke-linejoin: round`
- **Sin sombras duras** — usar `filter: glow` sutil

---

## 3. Líneas (Quiromancia)

### Estilo de línea
- **Grosor**: 8-13px (13px para la línea destacada de la escena)
- **Patrón**: guiones (dasharray `[16, 8]` o `[14, 8]`)
- **Brillo**: glow sutil (gaussian blur 3px + merge)
- **Color**: único por línea, consistente entre escenas

### Colores de líneas
| Línea | Color | Código |
|-------|-------|--------|
| Vida | Cian | `#00D4FF` |
| Corazón | Rosa | `#FF6B9D` |
| Cabeza | Naranja | `#FFA500` |
| Destino | Amarillo | `#FFD93D` |

### Animación
- Las líneas se dibujan progresivamente (no aparecen de golpe)
- Cada línea tiene su propio timing (0.06-0.70 del progreso)
- La línea destacada de la escena se dibuja primero y más gruesa

---

## 4. Montes (Quiromancia)

### Estilo
- **Círculos sólidos** con borde blanco sutil
- **Radio**: 18-35px (Venus es el más grande)
- **Opacidad**: 0.9 (sólido) + halo 0.3 (brillo exterior)

### Colores de montes
| Monte | Color | Radio |
|-------|-------|-------|
| Júpiter | `#FF6B6B` (rojo) | 22px |
| Saturno | `#FFD93D` (amarillo) | 22px |
| Sol | `#6BCB77` (verde) | 20px |
| Mercurio | `#4D96FF` (azul) | 18px |
| Venus | `#FFFFFF` (blanco) | 35px |

---

## 5. Etiquetas y rótulos

### Formato
- **Fondo**: semitransparente oscuro `rgba(0,0,0,0.85)`
- **Borde**: 1px sutil `rgba(1,1,1,0.25)`
- **Radio de esquina**: 6px
- **Padding**: 10px horizontal
- **Línea conectora**: guiones finos `rgba(0.7,0.7,0.85,0.6)` desde el centro del texto al punto objetivo
- **Punto objetivo**: doble círculo (blanco 5px + color 3px)

### Posicionamiento
- Izquierda de la mano: para líneas de la palma
- Derecha de la mano: para montes
- **Nunca** encima de la mano
- Separación mínima: 40px del borde del viewBox

---

## 6. Narrativa y audio

### Estilo de guion
- **Tono**: educativo, terapéutico, respetuoso
- **Idioma**: español de México
- **Ritmo**: pausado, con énfasis en palabras clave
- **Estructura**: afirmación → explicación → cierre

### Motor de voz
1. **Preferido**: VoiceStudio (OmniVoice) — natural, GPU
2. **Fallback**: SAPI con voz Sabina es-MX
3. **Parámetros SAPI**: rate=-1 (más lento), pitch=+1 (más claro)

### Timing
- 4-5 escenas por video de 60s
- Cada escena: 10-15s de narración
- Pausa de 0.5s entre escenas (silence padding)

---

## 7. Formatos de video

### 16:9 (horizontal)
- Resolución: 1920×1080
- Mano centrada, ocupa ~70% del alto
- Títulos arriba, labels a los lados

### 9:16 (vertical/short)
- Resolución: 1080×1920
- **Nativo** (no recorte del 16:9)
- Mano escalada para llenar el alto
- Labels reposicionados para el formato vertical

### Perfiles de render
Ver `config/v8/render_profiles.yaml`:
- `test_30s`: 1920×1080, 30fps, CRF 28
- `long`: 1920×1080, 30fps, CRF 23
- `short`: 1080×1920, 30fps, CRF 23

---

## 8. Adaptación a otras disciplinas

### Astrología
- Reemplazar mano por **carta natal** (círculo con signos)
- Líneas → **tránsitos** (arcos coloridos)
- Montes → **casas** (sectores numerados)
- Fondo: cosmos con constelaciones

### Tarot
- Reemplazar mano por **carta** (formato 2:3)
- Líneas → **caminos** (líneas entre sephiroth si es Kabbalah)
- Montes → **arcanos** (iconos dentro de círculos)
- Fondo: textura de pergamino

### Numerología
- Reemplazar mano por **números** grandes (centro)
- Líneas → **ciclos** (espirales concéntricas)
- Montes → **posiciones** (números en círculos)
- Fondo: patrones geométricos

### Para implementar una nueva disciplina:
1. Crear `config/disciplines/<nombre>.yaml` con paleta, elementos, reglas
2. Crear `scripts/disciplines/<nombre>_geometry.py` con la geometría específica
3. Adaptar el compositor para usar la nueva geometría
4. Actualizar el storyboard schema con los campos específicos

---

## 9. Quality Assurance

### Checklist por frame
- [ ] Mano tiene 5 dedos visibles y separados
- [ ] Líneas son legibles (grosor suficiente, color correcto)
- [ ] Labels son legibles en 1080p
- [ ] Texto no se sale del encuadre
- [ ] Montes tienen colores distintivos
- [ ] Fondo no distrae del contenido principal
- [ ] Pie de página visible pero no intrusivo

### Métricas automáticas
- `hand_geometry --selftest`: 5 dedos, spread > 200px
- `validate_video`: resolución, bitrate, FPS, duración
- `policy_gate`: licencias, assets aprobados

---

## 10. Changelog de directrices

| Fecha | Versión | Cambio |
|-------|---------|--------|
| 2026-09-21 | 1.0 | Versión inicial con quiromancia V8.1 |
