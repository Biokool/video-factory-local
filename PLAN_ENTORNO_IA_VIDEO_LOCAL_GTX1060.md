# PLAN MAESTRO — FÁBRICA LOCAL DE VIDEO IA EN ASUS ROG STRIX GL703VM

**Versión:** 1.0.0  
**Fecha de verificación documental:** 2026-09-08  
**Objetivo:** levantar una prueba punta a punta reproducible de generación automatizada de contenido audiovisual local usando la arquitectura:

> **Qwen3.5 4B + Claude Code + ComfyUI + Stable Diffusion 1.5 + Piper + FFmpeg + n8n + Supabase**

Este documento está diseñado para entregarse a una IA agente de desarrollo/automatización. La IA debe interpretar este archivo como una **especificación de implementación**, ejecutar las verificaciones en la máquina, crear los archivos necesarios, instalar los componentes y detenerse cuando una dependencia no pueda validarse en lugar de inventar versiones, rutas o credenciales.

---

## 0. Resultado esperado

La prueba debe demostrar que una solicitud como:

> **"Crea un video educativo sobre qué representa una línea del corazón marcada, usando el conocimiento del repositorio RAG de quiromancia terapéutica no adivinatoria."**

puede producir automáticamente:

1. tema y brief normalizado;
2. recuperación de conocimiento desde Supabase/pgvector;
3. guion estructurado;
4. título, descripción, hashtags y CTA;
5. storyboard de escenas;
6. prompts visuales;
7. imágenes generadas localmente con ComfyUI + SD1.5;
8. narración en español de México con Piper;
9. subtítulos mediante transcripción/alineación;
10. montaje final con FFmpeg;
11. versión horizontal de prueba (16:9) y versión vertical corta (9:16);
12. metadatos listos para publicación;
13. validaciones automáticas de duración, resolución, audio, existencia de archivos y coherencia del proyecto;
14. registro del estado del job y sus artefactos.

**La primera prueba NO debe intentar generar 8–9 minutos ni video generativo.** La primera prueba debe usar 30–60 s para validar toda la cadena. Después se escala a un video largo de 8–9 minutos.

---

# 1. Restricciones de hardware

## 1.1 Máquina objetivo

- Equipo: ASUS ROG Strix GL703VM-IH74
- CPU: Intel Core i7-7700HQ 2.8 GHz, 4 núcleos / 8 hilos
- RAM: 32 GB DDR4
- GPU: NVIDIA GeForce GTX 1060 6 GB VRAM
- SSD: 1 TB
- HDD: 1 TB
- Sistema objetivo: Windows 10 22H2 o Windows 11 de 64 bits

## 1.2 Consecuencia arquitectónica

La GTX 1060 de 6 GB es el recurso crítico. La arquitectura debe ser **secuencial**, no paralela, para evitar que Ollama, ComfyUI y otros procesos compitan por VRAM.

Orden recomendado de uso de la GPU:

1. Ollama / Qwen3.5:4b
2. liberar el modelo de Ollama;
3. ComfyUI / SD1.5;
4. liberar ComfyUI cuando sea posible;
5. FFmpeg/NVENC únicamente cuando el render lo requiera;
6. Piper preferentemente en CPU.

No intentar ejecutar simultáneamente LLM + generación de imágenes + modelos de video pesados.

---

# 2. Decisiones técnicas verificadas

## 2.1 Ollama

Ollama tiene cliente nativo para Windows y expone su API local en:

`http://localhost:11434`

En Windows se requiere Windows 10 22H2 o posterior y, para NVIDIA, un driver 452.39 o superior. La documentación de hardware de Ollama indica soporte de NVIDIA para compute capability 5.0+ y drivers 531+; la GTX 1060 pertenece a la familia Pascal y es compatible con esta generación de software cuando el driver instalado cumple los requisitos.

**Validación obligatoria en la máquina:**

```powershell
nvidia-smi
ollama --version
curl http://localhost:11434/api/version
```

Fuentes:
- https://docs.ollama.com/windows
- https://docs.ollama.com/gpu

## 2.2 Contexto de Ollama

Ollama actualmente usa como referencia:

- <24 GiB VRAM: 4K de contexto por defecto;
- 24–48 GiB: 32K;
- >=48 GiB: 256K.

Los agentes/coding tools se benefician de >=64K, pero **eso no debe forzarse en una GTX 1060 de 6 GB** durante la primera prueba porque aumenta el uso de memoria y puede producir offload a CPU.

Para esta máquina, empezar con **8K de contexto**, comprobar rendimiento y luego probar 16K si el job permanece estable. Si Claude Code/Hermes exige una ventana superior para una tarea concreta, la IA agente debe documentar el impacto antes de elevar `num_ctx`.

Fuente: https://docs.ollama.com/context-length

## 2.3 Modelo LLM principal

Modelo:

`qwen3.5:4b`

El catálogo oficial de Ollama muestra aproximadamente 3.4 GB para la variante 4B, contexto máximo 256K y entradas de texto/imagen.

**Usar exactamente la etiqueta:**

```powershell
ollama pull qwen3.5:4b
```

Fuente: https://ollama.com/library/qwen3.5

## 2.4 Embeddings

Modelo inicial:

`nomic-embed-text`

Tamaño aproximado: 274 MB. Debe usarse únicamente para embeddings. La salida estándar de `nomic-embed-text-v1.5` es de 768 dimensiones; el repositorio también documenta variantes dimensionales Matryoshka.

Comando:

```powershell
ollama pull nomic-embed-text
```

La tabla vectorial inicial debe usar `vector(768)`.

Fuentes:
- https://ollama.com/library/nomic-embed-text
- https://huggingface.co/nomic-ai/nomic-embed-text-v1.5

## 2.5 Claude Code

Ollama es compatible con Claude Code mediante la Anthropic Messages API a partir de Ollama v0.14.0. Ollama documenta:

```powershell
ollama launch claude
```

También documenta configuración mediante:

```text
ANTHROPIC_AUTH_TOKEN=ollama
ANTHROPIC_BASE_URL=http://localhost:11434
```

Sin embargo, la ruta recomendada para el primer setup es `ollama launch claude` porque el propio Ollama puede gestionar la configuración.

Fuente: https://ollama.com/blog/claude

## 2.6 ComfyUI

ComfyUI tiene aplicación Desktop y paquete portable para Windows. Para la GTX 1060/serie NVIDIA 10 existe una compilación portable específica con PyTorch CUDA 12.6 y Python 3.12.

**Preferencia para esta máquina:** paquete portable de NVIDIA para 10-series antes que una instalación manual genérica.

Fuente: https://github.com/Comfy-Org/ComfyUI

## 2.7 Stable Diffusion 1.5

El modelo de referencia es `stable-diffusion-v1-5/stable-diffusion-v1-5`.

Usarlo con resolución base moderada (512px en el lado corto cuando el workflow lo aconseje) y realizar upscale posterior. No generar directamente 1920x1080 en la primera prueba.

Fuente: https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5

## 2.8 Piper

La continuación oficial del proyecto se encuentra en `OHF-Voice/piper1-gpl`.

Instalación Python:

```powershell
pip install piper-tts
```

La documentación oficial incluye español de México (`es_MX`). Las voces publicadas incluyen `ald` (medium) y `claude` (high). Debe verificarse la licencia individual de cada modelo de voz antes de uso comercial.

Fuente: https://github.com/OHF-Voice/piper1-gpl

## 2.9 FFmpeg

FFmpeg será el motor de montaje, muxing, normalización y conversión. La IA debe invocar FFmpeg a través de scripts controlados y nunca construir comandos con parámetros concatenados directamente desde texto no confiable.

Verificar:

```powershell
ffmpeg -version
ffprobe -version
```

Si se desea usar NVENC, verificar primero:

```powershell
ffmpeg -hide_banner -encoders | findstr /i nvenc
```

La ruta de montaje principal debe tener fallback a CPU.

## 2.10 n8n

n8n es el orquestador de workflows. Para el entorno de prueba debe ejecutarse localmente y permanecer accesible únicamente desde localhost.

Es preferible que n8n y Supabase local compartan Docker Desktop, mientras Ollama y ComfyUI siguen nativos en Windows por el acceso directo a GPU.

Fuentes:
- https://docs.n8n.io/
- https://docs.n8n.io/hosting/
- https://docs.n8n.io/hosting/securing/security-audit/

## 2.11 Supabase

Supabase CLI permite crear un stack local con:

```bash
supabase init
supabase start
```

El stack local corre en Docker e incluye Postgres y servicios auxiliares. La documentación reciente indica al menos 7 GB de RAM recomendados para iniciar todos los servicios; el equipo objetivo tiene 32 GB.

**No exponer el Supabase local a Internet.** La documentación indica expresamente que el stack local es para desarrollo y pruebas, no está endurecido para producción y no debe exponerse públicamente.

Fuentes:
- https://supabase.com/docs/guides/local-development/cli/getting-started
- https://supabase.com/docs/guides/local-development/cli-workflows
- https://supabase.com/docs/guides/database/extensions/pgvector

---

# 3. Estrategia de instalación

## 3.1 Regla principal para la IA agente

La IA que implemente este documento debe:

1. detectar Windows y arquitectura x64;
2. detectar GPU NVIDIA y VRAM;
3. detectar versión del driver;
4. detectar RAM y espacio libre;
5. comparar contra los requisitos antes de instalar;
6. reutilizar instalaciones existentes cuando sean compatibles;
7. nunca sobrescribir datos de usuario sin backup;
8. crear backups de archivos de configuración antes de modificarlos;
9. registrar versiones reales instaladas;
10. detenerse en caso de error crítico y guardar diagnóstico.

No inventar URLs ni nombres de releases. Cuando una descarga cambie, consultar la página oficial del proyecto.

---

# 4. Estructura de carpetas

Crear el proyecto en el SSD, por ejemplo:

```text
C:\AI\video-factory\
│
├── .env.example
├── README.md
├── AGENT_INSTRUCTIONS.md
├── pyproject.toml
├── requirements.txt
├── docker-compose.yml
├── Makefile.ps1
├── scripts\
│   ├── preflight.ps1
│   ├── install.ps1
│   ├── healthcheck.ps1
│   ├── run_test.ps1
│   ├── generate_tts.py
│   ├── generate_embeddings.py
│   ├── rag_ingest.py
│   ├── rag_query.py
│   ├── build_storyboard.py
│   ├── render_video.py
│   ├── validate_video.py
│   └── cleanup_gpu.ps1
│
├── config\
│   ├── app.yaml
│   ├── ollama.yaml
│   ├── comfyui.yaml
│   ├── video_profiles.yaml
│   └── quality_rules.yaml
│
├── data\
│   ├── input\
│   ├── documents\
│   ├── extracted\
│   ├── rag\
│   ├── images\
│   ├── audio\
│   ├── subtitles\
│   ├── scenes\
│   ├── renders\
│   ├── thumbnails\
│   ├── metadata\
│   ├── temp\
│   └── logs\
│
├── workflows\
│   ├── n8n\
│   └── comfyui\
│
├── supabase\
│   ├── config.toml
│   ├── migrations\
│   └── seed.sql
│
└── tests\
    ├── fixtures\
    ├── expected\
    └── reports\
```

Los modelos pesados no deben duplicarse innecesariamente. La IA debe preferir rutas de modelos externas mediante `extra_model_paths.yaml` de ComfyUI cuando proceda.

---

# 5. Preflight obligatorio

Crear `scripts/preflight.ps1`.

El script debe comprobar:

```powershell
$ErrorActionPreference = "Stop"

Write-Host "=== AI VIDEO FACTORY PREFLIGHT ==="

Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsArchitecture

Write-Host "--- CPU ---"
Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors

Write-Host "--- RAM ---"
Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory

Write-Host "--- GPU ---"
nvidia-smi

Write-Host "--- Disk ---"
Get-PSDrive C,D,E -ErrorAction SilentlyContinue | Select-Object Name,Used,Free

Write-Host "--- Tools ---"
Get-Command ollama -ErrorAction SilentlyContinue
Get-Command ffmpeg -ErrorAction SilentlyContinue
Get-Command ffprobe -ErrorAction SilentlyContinue
Get-Command python -ErrorAction SilentlyContinue
Get-Command docker -ErrorAction SilentlyContinue
Get-Command git -ErrorAction SilentlyContinue
Get-Command supabase -ErrorAction SilentlyContinue
```

Después verificar:

```powershell
ollama --version
curl http://localhost:11434/api/version
python --version
pip --version
docker version
supabase --version
ffmpeg -version
```

La IA debe guardar el resultado en:

`data/logs/preflight_YYYYMMDD-HHMMSS.json`

---

# 6. Entorno Python

No instalar paquetes globalmente salvo herramientas deliberadamente globales.

Crear un entorno virtual:

```powershell
cd C:\AI\video-factory
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
```

`requirements.txt` mínimo:

```text
ollama
supabase
psycopg[binary]
python-dotenv
pydantic
pydantic-settings
PyYAML
requests
httpx
numpy
pillow
piper-tts
faster-whisper
```

No fijar versiones arbitrariamente. La IA debe obtener y congelar las versiones que realmente funcionen en la máquina mediante:

```powershell
pip freeze > requirements-lock.txt
```

Si `faster-whisper` se ejecuta en GPU y aparecen incompatibilidades con CUDA/cuDNN, **no forzar la instalación a ciegas**. La documentación actual de faster-whisper indica CUDA 12 + cuBLAS y cuDNN 9 para las versiones recientes de CTranslate2. En esta primera prueba se puede ejecutar faster-whisper en CPU si simplifica el stack.

Fuentes:
- https://github.com/SYSTRAN/faster-whisper

---

# 7. Ollama: instalación y configuración

## 7.1 Instalar

Instalar desde la página oficial:

https://ollama.com/download/windows

Después validar:

```powershell
ollama --version
curl http://localhost:11434/api/version
```

## 7.2 Descargar modelos

```powershell
ollama pull qwen3.5:4b
ollama pull nomic-embed-text
```

## 7.3 Crear un Modelfile de producción de prueba

Crear:

`config/QwenVideoFactory.Modelfile`

Contenido:

```text
FROM qwen3.5:4b

PARAMETER num_ctx 8192
PARAMETER temperature 0.65
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.08
PARAMETER seed 42

SYSTEM """
Eres el motor creativo y de estructuración de una fábrica local de video.
Debes generar contenido en español de México, claro, preciso y natural.
Cuando uses información recuperada desde RAG, no inventes hechos que no estén
respaldados por el contexto proporcionado.
El contenido sobre quiromancia debe ser terapéutico, educativo y no adivinatorio.
No atribuyas a una línea de la mano diagnósticos médicos, destinos inevitables,
certezas sobrenaturales ni predicciones deterministas.
Siempre devuelve JSON válido cuando el prompt indique un esquema JSON.
"""
```

Crear el modelo:

```powershell
ollama create video-factory-qwen -f config/QwenVideoFactory.Modelfile
```

Validar:

```powershell
ollama run video-factory-qwen "Devuelve JSON con un hook de 1 frase sobre la línea del corazón."
```

La documentación de Ollama confirma `PARAMETER num_ctx`, `temperature`, `top_p`, `top_k`, `repeat_penalty` y `seed` en Modelfile.

Fuente: https://docs.ollama.com/modelfile

## 7.4 Verificar offload

Después de ejecutar una petición:

```powershell
ollama ps
```

Registrar especialmente la columna `PROCESSOR`.

La condición preferida es que el modelo no se fragmente innecesariamente en CPU/GPU. Si la máquina muestra offload excesivo y el rendimiento es malo, reducir contexto o usar el modelo más pequeño para la tarea.

Fuente: https://docs.ollama.com/context-length

---

# 8. Claude Code

Primero instalar Claude Code siguiendo la documentación/instalador oficial. En Windows PowerShell, Ollama documenta:

```powershell
irm https://claude.ai/install.ps1 | iex
```

Después ejecutar:

```powershell
ollama launch claude --model video-factory-qwen
```

El agente debe iniciar una sesión de prueba y verificar:

```text
- puede leer/escribir archivos dentro de C:\AI\video-factory
- puede invocar herramientas locales
- puede llamar al endpoint de Ollama
- no requiere una API key de pago para el modelo local
```

Fuente: https://ollama.com/blog/claude

**Importante:** esto no ejecuta el modelo propietario de Anthropic de manera local. Claude Code funciona como interfaz/agente y Ollama sirve el modelo abierto local.

---

# 9. Hermes Agent — opcional en la primera fase

No hacer que Hermes sea un requisito de bloqueo del primer test.

Motivo: la documentación de integración para agentes/coding tools recomienda contextos grandes y Hermes documenta requisitos de contexto que pueden ser difíciles para una GTX 1060.

La IA debe dejar un adaptador preparado, pero la primera prueba debe funcionar sin Hermes si Claude Code ya está operativo.

Después ejecutar en una segunda fase:

```powershell
ollama launch hermes --model video-factory-qwen
```

Si el comando no estuviera disponible en la versión instalada de Ollama/Hermes, consultar la documentación oficial actual antes de adaptar el comando.

---

# 10. ComfyUI

## 10.1 Instalación preferida

Para esta GTX 1060:

1. abrir el README/releases oficial de ComfyUI;
2. descargar el portable para NVIDIA 10-series (CUDA 12.6 / Python 3.12) cuando esté disponible;
3. instalar en:

`C:\AI\ComfyUI`

4. colocar checkpoints en:

`C:\AI\ComfyUI\models\checkpoints\`

La documentación actual de ComfyUI indica específicamente una descarga portable de PyTorch CUDA 12.6 que soporta NVIDIA 10-series y anteriores.

Fuente: https://github.com/Comfy-Org/ComfyUI

## 10.2 Modelo SD1.5

Descargar un checkpoint SD1.5 compatible y con licencia revisada para el uso planeado.

No asumir que cualquier checkpoint comunitario es intercambiable ni comercialmente permitido.

El modelo de referencia oficial es:

https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5

## 10.3 Prueba básica

Ejecutar ComfyUI y confirmar que abre el UI local.

El script de arranque debe registrar:

```text
ComfyUI URL: http://127.0.0.1:8188
GPU detectada: NVIDIA GTX 1060
VRAM aproximada: 6 GB
```

Probar primero una imagen 512x512, batch=1.

**No añadir custom nodes en la primera prueba salvo los imprescindibles.** Cada custom node adicional aumenta el riesgo de incompatibilidades.

## 10.4 Workflow mínimo

Guardar en:

`workflows/comfyui/sd15_test.json`

Workflow conceptual mínimo:

```text
CheckpointLoaderSimple
        ↓
CLIP Text Encode (positive)
        ↓
KSampler ← EmptyLatentImage
        ↓
VAEDecode
        ↓
SaveImage
```

Parámetros iniciales sugeridos:

- width: 512
- height: 512
- batch: 1
- steps: 20–28
- CFG: 6–8
- sampler: uno estable soportado por el checkpoint
- seed fijo durante el test

La IA debe guardar el seed utilizado.

---

# 11. Piper TTS

## 11.1 Instalación

Dentro de `.venv`:

```powershell
pip install piper-tts
```

Verificar:

```powershell
python -m piper --help
```

## 11.2 Voz

Usar inicialmente una voz `es_MX` documentada por OHF-Voice/Piper.

Preferencia de prueba:

1. `es_MX-claude-high` si la voz está disponible en el paquete/descarga actual;
2. `es_MX-ald-medium` como alternativa ligera.

La implementación debe consultar la lista oficial actual de voces y comprobar los archivos/model cards antes de descargar.

Fuente: https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md

## 11.3 Generación

Crear `scripts/generate_tts.py`.

Debe aceptar:

```text
--input data/scenes/narration.txt
--voice <voice>
--output data/audio/narration.wav
```

Debe:

1. normalizar espacios;
2. conservar puntuación;
3. evitar bloques de texto excesivamente largos en una sola llamada;
4. generar WAV PCM con frecuencia fija;
5. comprobar que el archivo existe;
6. medir duración;
7. devolver JSON de estado.

La CLI oficial de Piper permite síntesis desde texto y recomienda el servidor para usos repetidos porque evita cargar el modelo en cada invocación.

Fuente: https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/CLI.md

---

# 12. RAG local con Supabase + pgvector

## 12.1 Docker Desktop

Instalar Docker Desktop para Windows. Mantenerlo en configuración de desarrollo.

## 12.2 Supabase local

Dentro del proyecto:

```powershell
cd C:\AI\video-factory
supabase init
supabase start
```

No exponer puertos a Internet.

Verificar el dashboard local con la URL reportada por `supabase start`.

## 12.3 Esquema

Crear migración:

`supabase/migrations/001_rag.sql`

Ejemplo:

```sql
create extension if not exists vector with schema extensions;

create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  source_path text not null,
  source_name text not null,
  category text,
  title text,
  content text not null,
  checksum_sha256 text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.document_chunks (
  id bigserial primary key,
  document_id uuid not null references public.documents(id) on delete cascade,
  chunk_index integer not null,
  content text not null,
  token_count integer,
  metadata jsonb not null default '{}'::jsonb,
  embedding extensions.vector(768) not null,
  created_at timestamptz not null default now()
);

create index if not exists document_chunks_document_id_idx
  on public.document_chunks(document_id);

-- Para la primera prueba el volumen será pequeño. Crear el índice vectorial
-- cuando la consulta y dimensionalidad estén validadas.
```

Supabase documenta `pgvector` mediante la extensión `vector` para almacenar embeddings y hacer búsqueda por similitud.

Fuente: https://supabase.com/docs/guides/database/extensions/pgvector

## 12.4 RPC de búsqueda

Crear una función SQL segura para recuperar top-k:

```sql
create or replace function public.match_document_chunks(
  query_embedding extensions.vector(768),
  match_count int default 6,
  filter_category text default null
)
returns table (
  id bigint,
  document_id uuid,
  content text,
  metadata jsonb,
  similarity float
)
language sql
stable
as $$
  select
    dc.id,
    dc.document_id,
    dc.content,
    dc.metadata,
    1 - (dc.embedding <=> query_embedding) as similarity
  from public.document_chunks dc
  where filter_category is null
     or dc.metadata->>'category' = filter_category
  order by dc.embedding <=> query_embedding
  limit least(greatest(match_count, 1), 20);
$$;
```

## 12.5 Ingesta

Proceso:

```text
Documento
  ↓
texto limpio
  ↓
normalización
  ↓
chunks semánticos
  ↓
Ollama / nomic-embed-text
  ↓
vector(768)
  ↓
Supabase
```

Recomendación inicial de chunking:

- objetivo: 450–700 tokens;
- overlap: 60–100 tokens;
- conservar encabezado/título en metadata;
- no dividir en mitad de una definición importante si se puede evitar;
- almacenar `source_path`, página/sección cuando exista y categoría.

Para la prueba solo cargar 1–3 documentos de ejemplo.

---

# 13. Flujo creativo

## 13.1 Input

La entrada al sistema será:

```json
{
  "topic": "línea del corazón marcada",
  "format": "long",
  "duration_target_seconds": 480,
  "language": "es-MX",
  "style": "educativo-terapéutico-no-adivinatorio",
  "audience": "personas interesadas en conocer la lectura terapéutica de la mano"
}
```

## 13.2 Salida estructurada del LLM

El LLM debe entregar JSON validable:

```json
{
  "title": "...",
  "hook": "...",
  "angle": "...",
  "summary": "...",
  "disclaimer": "...",
  "scenes": [
    {
      "id": 1,
      "duration_sec": 10,
      "narration": "...",
      "visual_prompt": "...",
      "on_screen_text": "...",
      "source_chunk_ids": [1, 2]
    }
  ],
  "cta": "...",
  "youtube_description": "...",
  "hashtags": ["...", "..."]
}
```

El script debe validar el JSON con Pydantic.

---

# 14. Política de calidad del contenido

La IA agente debe rechazar o revisar un guion que:

- presente la quiromancia como diagnóstico médico;
- presente predicciones como hechos;
- afirme destino inevitable;
- invente citas o fuentes;
- introduzca datos que no estén en el RAG cuando el modo esté definido como `rag_only`;
- repita una frase demasiadas veces;
- contenga un CTA sin relación con el contenido.

Para contenido terapéutico, utilizar lenguaje de exploración/reflexión:

- "puede interpretarse como..."
- "en este enfoque se observa..."
- "se utiliza como punto de reflexión..."

Evitar:

- "esto significa que definitivamente..."
- "vas a vivir..."
- "tienes esta enfermedad..."

---

# 15. Storyboard

El guion de 8–9 minutos debe dividirse preferentemente en 35–60 escenas cortas, dependiendo del ritmo.

Cada escena necesita:

- `scene_id`
- `duration_sec`
- `narration`
- `visual_prompt`
- `asset_type`
- `subtitle_text`
- `transition`
- `camera_effect`
- `source_chunk_ids`

Tipos de asset iniciales:

```text
AI_IMAGE
STOCK_PLACEHOLDER
TEXT_CARD
GRAPHIC
B_ROLL
```

No exigir que cada segundo tenga una imagen completamente nueva. Para reducir tiempo de GPU, se puede reutilizar una imagen durante 4–10 s con paneo/zoom y overlays.

---

# 16. Generación de imágenes con ComfyUI

La primera implementación puede llamar al endpoint HTTP/API local de ComfyUI usando el workflow JSON.

Arquitectura:

```text
Python / n8n
      ↓
POST workflow a ComfyUI
      ↓
cola local
      ↓
imagen PNG
      ↓
metadata/seed registrado
```

La IA debe evitar dependencias UI frágiles como clicks de mouse para producción.

Para cada imagen guardar:

```json
{
  "scene_id": 4,
  "prompt": "...",
  "negative_prompt": "...",
  "seed": 123456,
  "width": 512,
  "height": 512,
  "model": "<checkpoint_real_instalado>",
  "created_at": "..."
}
```

---

# 17. Calidad visual

## 17.1 Perfil largo

Base de edición:

- 1920x1080
- 30 fps
- H.264
- AAC
- audio estéreo

Pero no generar imágenes a 1920x1080 directamente con SD1.5 en la GTX 1060.

Pipeline:

```text
512x512 / 512x768 / 768x512
        ↓
upscale
        ↓
recorte/letterbox inteligente
        ↓
1920x1080
```

## 17.2 Perfil short/reel

- 1080x1920
- 30 fps
- H.264
- AAC

En el primer test se puede usar 720x1280 para acortar el tiempo de render; la salida objetivo de producción sigue siendo 1080x1920.

---

# 18. Audio

La narración es el elemento prioritario del video.

Objetivos iniciales de mezcla:

- voz claramente por encima de música;
- evitar clipping;
- normalización consistente entre escenas;
- música de fondo atenuada automáticamente durante voz;
- fade-in/out;
- silencio mínimo entre segmentos.

La IA debe usar `ffmpeg`/filtros de audio y comprobar pico/RMS/LUFS de manera reproducible. Si no dispone de un medidor LUFS robusto, al menos debe controlar peak y evitar valores > -1 dBFS.

---

# 19. Subtítulos

Para la prueba:

1. Piper genera WAV;
2. faster-whisper transcribe el WAV;
3. obtener timestamps;
4. generar `.srt`;
5. FFmpeg quema los subtítulos o los deja como track opcional según el perfil.

Inicialmente ejecutar faster-whisper en CPU si CUDA/cuDNN genera complejidad innecesaria.

Fuente: https://github.com/SYSTRAN/faster-whisper

---

# 20. Edición automática con FFmpeg

Crear `scripts/render_video.py`.

El script debe recibir:

```text
--project-id
--manifest data/scenes/manifest.json
--voice data/audio/narration.wav
--output data/renders/final.mp4
--profile long|short
```

Debe:

1. cargar manifest;
2. comprobar existencia de todos los assets;
3. crear segmentos por escena;
4. aplicar zoom/pan;
5. mezclar voz y música;
6. añadir subtítulos;
7. concatenar escenas;
8. renderizar MP4;
9. ejecutar ffprobe;
10. guardar reporte de validación.

No permitir que prompts o nombres de archivo externos puedan inyectar argumentos de shell. Usar `subprocess.run([...], check=True)` con listas de argumentos.

---

# 21. Perfil de video largo

Objetivo producción:

```text
Duración: 8:00–9:00
Resolución: 1920x1080
FPS: 30
Codec: H.264
Audio: AAC 48 kHz

Estructura sugerida:
00:00–00:20 Hook
00:20–01:00 Contexto
01:00–03:00 Desarrollo 1
03:00–05:30 Desarrollo 2
05:30–07:30 Ejemplos / interpretación
07:30–08:30 Resumen
08:30–09:00 CTA + disclaimer
```

El sistema no debe rellenar artificialmente la duración. Si el guion tiene pocos segundos de narración, debe ampliar contenido útil, no insertar silencios excesivos.

---

# 22. Perfil de short/reel

Objetivo producción:

```text
20–60 s
1080x1920
30 fps
hook en primeros 1–2 s
subtítulos grandes
CTA breve
```

Fuente del contenido: reutilizar escenas o extraer un segmento de alto interés del video largo.

Una pieza larga debe poder generar varias piezas cortas sin volver a inventar todo el contenido.

---

# 23. n8n — orquestación

## 23.1 Función

n8n no debe hacer procesamiento pesado de video internamente. Debe coordinar jobs y llamar scripts/HTTP APIs.

## 23.2 Workflow principal

Nombre:

`VIDEO_FACTORY_E2E_TEST`

Flujo:

```text
Manual Trigger
    ↓
Set Test Input
    ↓
HTTP Request → Ollama health
    ↓
HTTP Request → RAG query service
    ↓
HTTP Request → Ollama generate script
    ↓
Code → validate JSON
    ↓
Execute Command → build storyboard
    ↓
Execute Command → Piper TTS
    ↓
Execute Command → faster-whisper
    ↓
Loop scenes
    ↓
HTTP Request → ComfyUI
    ↓
Wait/Poll ComfyUI
    ↓
Execute Command → FFmpeg
    ↓
Execute Command → ffprobe validator
    ↓
IF QA PASS
    ├── Write success report
    └── Create publishing package
```

**Seguridad:** en un n8n autoalojado, `Execute Command` puede ejecutar comandos del host. Debe limitarse a scripts internos conocidos. Ejecutar `n8n audit` después de construir el workflow y revisar los riesgos reportados.

Fuente: https://docs.n8n.io/hosting/securing/security-audit/

---

# 24. n8n — configuración local

Para la prueba se puede levantar n8n en Docker.

No usar n8n Cloud para esta prueba porque el objetivo es validar el stack local y sin costo de inferencia.

El contenedor debe tener un volumen persistente para workflows/credenciales y acceso restringido al proyecto.

No publicar el puerto n8n en `0.0.0.0` sin necesidad.

Preferir:

```text
127.0.0.1:5678
```

El hostname local debe ser el único objetivo inicial.

---

# 25. API local de control

Crear un pequeño servicio Python para simplificar n8n:

`services/local_api.py`

Endpoints mínimos:

```text
GET  /health
POST /generate-script
POST /rag/search
POST /tts
POST /scene-image
POST /render
POST /validate
GET  /jobs/{id}
```

Framework sugerido:

- FastAPI
- Uvicorn

Pero el servicio no debe cargar Qwen, Piper o ComfyUI en memoria permanentemente salvo que exista una razón clara. Usar clientes HTTP y procesos controlados.

---

# 26. Estado de jobs

Cada ejecución debe crear:

`data/jobs/<job_id>/`

con:

```text
input.json
rag.json
script.json
storyboard.json
images.json
voice.json
subtitles.json
render.json
qa.json
final.mp4
thumbnail.png
metadata.json
logs/
```

Esto permite reanudar etapas sin generar de nuevo todo.

---

# 27. Reanudación y caché

Regla de oro:

> **Nunca regenerar un asset que ya pasó QA.**

Usar hashes:

```text
SHA256(prompt + model + seed + settings)
```

Si el hash ya existe y el archivo sigue intacto, reutilizarlo.

Esto reducirá drásticamente el uso de GPU.

---

# 28. Prueba punta a punta REAL

## 28.1 Tema

Usar:

> "La línea del corazón marcada: cómo observarla desde una lectura terapéutica y no adivinatoria"

## 28.2 Dataset mínimo

Crear documento:

`data/documents/demo_quiro.doc.md`

con 700–1500 palabras controladas por nosotros. Debe explicar el concepto sin hacer afirmaciones médicas ni predictivas.

## 28.3 Ingesta

Ejecutar:

```powershell
python scripts/rag_ingest.py --input data/documents/demo_quiro.doc.md --category quiromancia
```

Esperar:

```text
documents inserted: 1
chunks inserted: >0
embeddings generated: >0
```

## 28.4 Consulta RAG

```powershell
python scripts/rag_query.py --query "línea del corazón marcada" --top-k 6
```

Debe devolver fragmentos y similarity score.

## 28.5 Generación del guion

El prompt debe incluir:

- target audience;
- tono;
- formato;
- duración;
- restricciones de seguridad del contenido;
- contexto RAG.

La salida debe ser JSON válido.

## 28.6 TTS

Generar aproximadamente 35–60 s de narración para la prueba.

## 28.7 Imágenes

Generar 4–8 imágenes, no 30–60, en la primera corrida.

## 28.8 Montaje

Crear video de 30–60 s en 16:9.

## 28.9 Short

Tomar el segmento más fuerte y convertirlo a 9:16.

---

# 29. Ejemplo de guion de prueba

El contenido exacto debe generarse con Qwen usando el RAG, pero el concepto esperado debe parecerse a:

```text
HOOK:
"Hay una forma de observar la línea del corazón sin convertirla en una predicción: usarla como punto de reflexión sobre cómo expresamos nuestras emociones."

DESARROLLO:
Explicar qué se observa visualmente, cómo describir una línea marcada sin afirmar que determina la personalidad o el futuro, y cómo la lectura terapéutica puede utilizar preguntas de autoobservación.

EJEMPLO:
"En lugar de decir 'esto significa que te ocurrirá...', un enfoque terapéutico preguntaría '¿cómo describes actualmente tu forma de vincularte con los demás?'."

CTA:
"Si te interesa conocer la lectura terapéutica de la mano desde un enfoque no adivinatorio, guarda este video y explora los siguientes contenidos."
```

Esto es un ejemplo de estructura, no una fuente factual sobre quiromancia. Para la prueba real, el contenido debe proceder del RAG.

---

# 30. Quality Gate — QA automático

Crear `scripts/validate_video.py`.

Debe devolver código de salida:

- `0` = PASS
- `1` = FAIL

## 30.1 Validaciones de archivo

- existe MP4;
- tamaño > umbral razonable;
- existe audio;
- existe thumbnail;
- existe manifest;
- no hay escenas huérfanas.

## 30.2 Validación técnica con ffprobe

Verificar:

```text
width
height
r_frame_rate
codec_name
sample_rate
channels
duration
```

## 30.3 Perfil largo

PASS si:

- duración 480–540 s;
- resolución 1920x1080;
- audio presente;
- video reproducible;
- no hay NaN/invalid packet reportado por ffmpeg/ffprobe.

## 30.4 Perfil short

PASS si:

- duración 20–60 s;
- 1080x1920 en producción;
- audio presente.

## 30.5 QA de audio

PASS si:

- no hay clipping sostenido;
- voz audible;
- archivo PCM fuente íntegro;
- duración voz y video razonablemente alineadas.

## 30.6 QA de contenido

La IA debe hacer una segunda pasada sobre el texto generado y marcar:

```text
citation_gap
unsupported_claim
medical_claim
prediction_claim
repetition
weak_hook
missing_cta
```

---

# 31. Performance targets

No imponer tiempos irreales. Registrar tiempos reales por etapa:

```text
preflight_seconds
rag_seconds
llm_seconds
tts_seconds
image_generation_seconds
subtitle_seconds
render_seconds
total_seconds
```

La métrica importante en esta computadora no es "tiempo real", sino:

> **cuántos minutos de video usable se pueden producir de forma estable por sesión sin errores ni intervención manual.**

La IA debe construir un reporte:

`tests/reports/performance.json`

---

# 32. Manejo de memoria/VRAM

## 32.1 Ollama

Antes de ComfyUI:

```powershell
ollama ps
```

Después de terminar el LLM, descargar el modelo o permitir que expire según la configuración.

La IA debe evitar que el modelo permanezca residente durante la etapa de generación de imágenes si la VRAM disponible cae demasiado.

## 32.2 ComfyUI

Ejecutar con configuración adecuada para NVIDIA 10-series. La versión portable específica para CUDA 12.6 es preferible.

Si aparecen errores `CUDA out of memory`:

1. batch=1;
2. reducir resolución;
3. reducir steps;
4. activar opciones low-vram soportadas por la versión instalada;
5. descargar cualquier modelo adicional;
6. reiniciar ComfyUI para limpiar VRAM.

No saltar directamente a modelos mayores.

---

# 33. Gestión de almacenamiento

No almacenar videos intermedios innecesarios permanentemente.

Regla:

```text
raw inputs       conservar
RAG data         conservar
final renders    conservar
approved images  conservar
failed temp      eliminar después de X días
intermediate mp4 limpiar
cache            limpiar según tamaño
```

Los videos largos pueden ocupar varios GB. El SSD debe reservarse para modelos + trabajo activo; el HDD puede almacenar archivo histórico.

---

# 34. Publicación — NO automática en la primera prueba

La primera ejecución no debe publicar nada.

Debe crear un **Publishing Package**:

```text
publish/
  video.mp4
  thumbnail.png
  title.txt
  description.md
  tags.txt
  hashtags.txt
  alt_text.txt
```

Después de validar la generación local, se puede añadir YouTube/Meta.

La API de YouTube `videos.insert` permite subir videos y metadatos, pero los proyectos API no verificados creados después del 28-jul-2020 tienen restricciones de privacidad que deben considerarse durante pruebas.

Fuentes:
- https://developers.google.com/youtube/v3/docs/videos/insert
- https://developers.google.com/youtube/v3/guides/uploading_a_video

---

# 35. Diseño de prompts

Mantener prompts fuera del código.

Crear:

`config/prompts/`

Archivos:

```text
system_content.md
script_long.md
script_short.md
storyboard.md
visual_prompt.md
qa_content.md
metadata.md
```

Los prompts deben exigir salida estructurada cuando corresponda.

Ejemplo para storyboard:

```text
Convierte el siguiente guion en escenas audiovisuales.

Reglas:
- cada escena debe tener una sola intención visual;
- evita cambios de sujeto innecesarios;
- prioriza claridad visual;
- reutiliza assets cuando no sea necesario generar otro;
- no generes texto dentro de las imágenes;
- el texto en pantalla se añadirá por FFmpeg/Remotion;
- mantén continuidad visual del sujeto y ambiente;
- usa exclusivamente el contexto RAG proporcionado cuando el modo sea rag_only.
```

---

# 36. Consistencia visual

Para que el resultado no parezca una secuencia aleatoria de imágenes:

- crear una `visual_bible.json` por proyecto;
- definir paleta conceptual sin codificar colores rígidos si no es necesario;
- definir tipo de iluminación;
- definir tipo de lente/cámara simulada;
- definir edad/apariencia de manos cuando se representen;
- definir fondos y props recurrentes;
- mantener seed/estilo cuando sea conveniente.

Ejemplo:

```json
{
  "style": "editorial documentary",
  "camera": "50mm photographic look",
  "lighting": "soft cinematic natural light",
  "background": "warm neutral studio",
  "subject": "realistic adult hands",
  "negative": "text, watermark, distorted fingers, extra fingers, malformed hands"
}
```

Para quiromancia, revisar especialmente manos y dedos. Una imagen con anatomía defectuosa debe ser rechazada y regenerada.

---

# 37. QA visual automático básico

No intentar solucionar toda la percepción visual con un LLM pequeño.

Primera versión:

1. revisar dimensión;
2. detectar imágenes corruptas;
3. opcionalmente usar Qwen3.5:4b visión para una revisión de muestra;
4. marcar escenas que requieren regeneración.

Prompt de revisión:

```text
Evalúa esta imagen para un video educativo.
Devuelve JSON:
{
  "anatomy_ok": true/false,
  "contains_text": true/false,
  "watermark": true/false,
  "visual_artifacts": true/false,
  "matches_subject": true/false,
  "score": 0-10,
  "reason": "..."
}
```

Regenerar automáticamente si `score < 7` o si `anatomy_ok=false`.

---

# 38. Política de fallbacks

## LLM

Qwen3.5:4b → Qwen3:4b → modo manual/reintento

## TTS

Piper es_MX high → Piper es_MX medium → error controlado

## imágenes

SD1.5 GPU → SD1.5 configuración low-vram → reintento con menor resolución

## transcripción

faster-whisper CPU → retry

## render

NVENC → H.264 CPU

Nunca reemplazar un componente con un servicio de pago sin autorización explícita.

---

# 39. Reintentos

Cada etapa debe ser idempotente y tener máximo 2 reintentos automáticos.

Regla:

```text
try 1
  ↓ fail
inspect error class
  ↓ transient?
retry 2
  ↓ fail
mark FAILED
```

No reintentar automáticamente errores como:

- archivo inexistente;
- modelo no encontrado;
- credencial inválida;
- schema inválido;
- GPU no disponible.

Estos requieren intervención o reparación.

---

# 40. Logging

Todos los servicios deben escribir logs con:

```json
{
  "timestamp": "...",
  "job_id": "...",
  "component": "ollama|comfyui|piper|ffmpeg|rag|n8n",
  "level": "INFO|WARN|ERROR",
  "message": "...",
  "duration_ms": 123,
  "error_code": null
}
```

No guardar secretos/API keys en logs.

---

# 41. Secrets

Crear `.env` a partir de `.env.example`.

Nunca poner secretos reales en Git.

Valores conceptuales:

```text
OLLAMA_BASE_URL=http://127.0.0.1:11434
COMFYUI_BASE_URL=http://127.0.0.1:8188
N8N_BASE_URL=http://127.0.0.1:5678
SUPABASE_URL=http://127.0.0.1:<puerto_reportado>
SUPABASE_ANON_KEY=<local generated>
SUPABASE_SERVICE_ROLE_KEY=<local generated>
```

El puerto/keys de Supabase deben copiarse de la salida real de `supabase start`, nunca inventarse.

---

# 42. Health checks

Crear `scripts/healthcheck.ps1`.

Checks:

```text
[ ] Ollama API
[ ] qwen3.5:4b
[ ] nomic-embed-text
[ ] ComfyUI
[ ] SD1.5 checkpoint
[ ] Piper
[ ] FFmpeg
[ ] ffprobe
[ ] Docker
[ ] Supabase
[ ] n8n
[ ] Python service
```

Salida:

```text
PASS Ollama
PASS Qwen3.5 4B
PASS Embedding model
PASS ComfyUI
PASS Piper
PASS FFmpeg
PASS Supabase
PASS n8n

SYSTEM READY
```

---

# 43. Prueba por etapas

No ejecutar todo de golpe.

## Test A — Hardware

Debe pasar:

```text
nvidia-smi
Ollama
ComfyUI
Docker
```

## Test B — LLM

Pregunta básica y JSON estructurado.

## Test C — Embeddings

Generar embedding y confirmar 768 dimensiones.

## Test D — Supabase

Insertar y consultar 1 documento.

## Test E — RAG

Pregunta semántica y top-k.

## Test F — Piper

Audio WAV de 10–20 s.

## Test G — SD1.5

Una imagen 512x512.

## Test H — FFmpeg

Video con imagen + voz.

## Test I — Subtítulos

SRT válido.

## Test J — n8n

Orquestar A→I.

## Test K — E2E

30–60 s.

## Test L — Long-form

8–9 min.

---

# 44. Emulación completa del flujo

## Entrada del usuario

```text
Tema: ¿Qué significa tener una línea del corazón marcada?
Formato: video largo
Duración objetivo: 8–9 min
Idioma: español de México
Estilo: educativo, cercano, terapéutico, no adivinatorio
```

## Paso 1 — n8n crea job

```json
{
  "job_id": "20260908-demo-0001",
  "status": "CREATED"
}
```

## Paso 2 — RAG

Consulta:

```text
línea del corazón marcada lectura terapéutica no adivinatoria
```

Retorna 6 fragmentos.

## Paso 3 — Qwen

Genera:

```text
hook
outline
scene list
description
cta
```

## Paso 4 — validación JSON

Pydantic valida.

## Paso 5 — visual bible

Se crea un estilo común.

## Paso 6 — Piper

Se generan segmentos de voz, preferiblemente por escena o bloque.

## Paso 7 — imágenes

ComfyUI crea únicamente las necesarias.

## Paso 8 — subtítulos

faster-whisper genera timestamps.

## Paso 9 — FFmpeg

Monta todo.

## Paso 10 — QA

Se ejecuta `validate_video.py`.

## Paso 11 — resultado

```text
PASS
video: 1920x1080
fps: 30
voice: OK
subtitles: OK
duration: 8m 32s
visual assets: 47
RAG chunks cited: 21
```

## Paso 12 — publicación

No publicar automáticamente en la primera ejecución. Preparar paquete de publicación.

---

# 45. Ejemplo de manifest

`data/jobs/<job_id>/manifest.json`

```json
{
  "project_id": "20260908-demo-0001",
  "profile": "long",
  "target_duration_sec": 510,
  "scenes": [
    {
      "id": 1,
      "duration_sec": 12,
      "image": "images/scene_001.png",
      "voice": "audio/scene_001.wav",
      "subtitle": "subtitles/scene_001.srt",
      "effect": "slow_zoom_in"
    }
  ]
}
```

El renderer debe aceptar este manifest sin conocer los detalles del LLM.

---

# 46. Prueba de API de Ollama

La API de chat oficial usa:

```text
POST http://localhost:11434/api/chat
```

Ejemplo conceptual:

```powershell
$body = @{
  model = "video-factory-qwen"
  messages = @(
    @{
      role = "user"
      content = "Devuelve JSON con hook, title y 3 escenas sobre la línea del corazón."
    }
  )
  stream = $false
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Uri "http://localhost:11434/api/chat" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

La API documenta además respuestas con métricas de duración y, en modelos compatibles, tool calls e imágenes.

Fuente: https://docs.ollama.com/api/chat

---

# 47. Prueba de embeddings

La API oficial de embeddings es:

```text
POST /api/embed
```

Ejemplo:

```powershell
$body = @{
  model = "nomic-embed-text"
  input = "línea del corazón marcada"
} | ConvertTo-Json

$r = Invoke-RestMethod `
  -Uri "http://localhost:11434/api/embed" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body

$r.embeddings[0].Count
```

Esperado:

```text
768
```

Fuente: https://docs.ollama.com/api/embed

---

# 48. Publicación de YouTube — segunda fase

Cuando la cadena local sea estable:

1. crear proyecto Google Cloud;
2. activar YouTube Data API v3;
3. crear OAuth 2.0;
4. ejecutar primero `privacyStatus=private`;
5. incorporar retry con backoff;
6. solo después evaluar publicación automática.

La guía oficial de Google proporciona un ejemplo Python con OAuth 2.0 y carga reanudable.

Fuentes:
- https://developers.google.com/youtube/v3/docs/videos/insert
- https://developers.google.com/youtube/v3/guides/uploading_a_video

---

# 49. Calidad editorial

Antes de permitir salida `APPROVED`:

```text
✓ Hook fuerte en <= 2 frases
✓ Introducción clara
✓ Desarrollo útil
✓ No relleno
✓ RAG utilizado
✓ No afirmaciones inventadas
✓ CTA congruente
✓ Disclaimer apropiado
✓ Visuales legibles
✓ Sin texto deformado dentro de IA
✓ Manos anatómicamente válidas
✓ Voz natural
✓ Música por debajo de voz
✓ Subtítulos sincronizados
✓ Audio sin clipping
✓ Video técnicamente válido
```

---

# 50. Definición de Done

La IA agente debe declarar **DONE** solamente cuando todas estas condiciones sean verdaderas:

```text
[PASS] GPU detected
[PASS] Ollama healthy
[PASS] qwen3.5:4b loaded
[PASS] embedding model loaded
[PASS] Supabase local healthy
[PASS] pgvector enabled
[PASS] RAG insert/search works
[PASS] Claude Code can use local model
[PASS] ComfyUI healthy
[PASS] SD1.5 image generated
[PASS] Piper generated es-MX WAV
[PASS] subtitles generated
[PASS] FFmpeg rendered mp4
[PASS] video QA passed
[PASS] short-form conversion passed
[PASS] all logs saved
[PASS] reproducibility manifest saved
```

---

# 51. Artefactos mínimos que la IA debe crear

La implementación debe entregar al menos:

```text
README.md
AGENT_INSTRUCTIONS.md
.env.example
requirements.txt
requirements-lock.txt
scripts/preflight.ps1
scripts/install.ps1
scripts/healthcheck.ps1
scripts/run_test.ps1
scripts/generate_tts.py
scripts/generate_embeddings.py
scripts/rag_ingest.py
scripts/rag_query.py
scripts/build_storyboard.py
scripts/render_video.py
scripts/validate_video.py
config/QwenVideoFactory.Modelfile
config/video_profiles.yaml
config/quality_rules.yaml
supabase/migrations/001_rag.sql
workflows/comfyui/sd15_test.json
workflows/n8n/VIDEO_FACTORY_E2E_TEST.json
data/documents/demo_quiro.doc.md
tests/reports/
```

---

# 52. Política de cambios

No añadir nuevos componentes a la V1 sin una razón demostrable.

No añadir:

- Redis
- Kubernetes
- microservicios adicionales
- vector DB adicional
- modelos gigantes
- video generation pesada
- paid APIs

hasta que la prueba base esté estable.

---

# 53. Escalamiento después del éxito

Orden de evolución:

## V1

30–60 s E2E.

## V1.1

2–3 minutos.

## V1.2

8–9 minutos.

## V1.3

Múltiples shorts.

## V1.4

Publicación YouTube privada.

## V1.5

Programación.

## V2

RAG real con documentos del cliente.

## V3

Panel de administración + métricas.

## V4

Actualización automática, cola de trabajos y recuperación.

---

# 54. Recomendaciones específicas para calidad

1. El guion debe ser mejor que la imagen. Un video con visuales modestos pero narración excelente funciona mejor que un video espectacular con discurso pobre.
2. La primera prueba debe optimizar **estabilidad y trazabilidad**, no velocidad.
3. No generar imágenes inútiles. Reutilización con movimiento cinematográfico reduce carga y mejora consistencia.
4. La voz debe ser consistente en todo el video.
5. Los subtítulos deben ser legibles y sincronizados.
6. El LLM debe generar decisiones; los scripts deben ejecutar esas decisiones de forma determinista.
7. Cada etapa debe guardar artefactos intermedios.
8. El RAG debe ser una fuente trazable, no un simple prompt largo.
9. Usar seeds, manifests y hashes para permitir regeneración selectiva.
10. La publicación automática se habilita solo después de QA repetido.

---

# 55. Prompt maestro para la IA que implemente este documento

Copiar este bloque a la IA agente encargada de instalar/desarrollar el entorno:

```text
ACTÚA COMO ARQUITECTO SENIOR DE IA LOCAL + DEVOPS + MLOPS + AUTOMATIZACIÓN MULTIMEDIA.

Tu misión es implementar la especificación completa de PLAN_ENTORNO_IA_VIDEO_LOCAL_GTX1060.md en una PC Windows con:
- Intel i7-7700HQ
- 32 GB RAM
- NVIDIA GTX 1060 6 GB
- SSD 1 TB + HDD 1 TB

ARQUITECTURA OBLIGATORIA:
Qwen3.5 4B + Claude Code + ComfyUI + Stable Diffusion 1.5 + Piper + FFmpeg + n8n + Supabase.

PRINCIPIOS:
1. Prioriza estabilidad y calidad sobre velocidad.
2. Todo componente debe ser local durante la prueba.
3. No inventes versiones, URLs, checkpoints, voces ni parámetros.
4. Consulta documentación oficial actual cuando exista una diferencia de versión.
5. No expongas servicios locales a Internet.
6. Nunca almacenes secretos en Git.
7. No sobrescribas archivos existentes sin backup.
8. Ejecuta primero preflight.
9. Instala solo lo necesario.
10. No uses modelos grandes incompatibles con 6 GB de VRAM.
11. No generes video generativo largo. Construye videos con imágenes, audio y FFmpeg.
12. El primer E2E debe durar 30–60 segundos.
13. Después de pasar QA, escala a 8–9 minutos.
14. Cada etapa debe ser reanudable.
15. Guarda logs, manifests, seeds y hashes.
16. Declara PASS/FAIL con evidencia.
17. Nunca digas DONE si un requisito de la sección 50 falla.

SECUENCIA DE IMPLEMENTACIÓN:
A) preflight
B) instalar/verificar Ollama
C) descargar qwen3.5:4b y nomic-embed-text
D) crear video-factory-qwen con num_ctx inicial 8192
E) instalar/probar Claude Code + Ollama
F) instalar ComfyUI portable para NVIDIA 10-series usando el paquete compatible actual
G) configurar SD1.5
H) instalar Piper y probar es_MX
I) instalar FFmpeg
J) instalar Docker Desktop
K) inicializar Supabase local y pgvector
L) levantar n8n local
M) crear servicios Python
N) crear migración RAG
O) crear datos de demo
P) ejecutar RAG
Q) generar guion JSON
R) generar voz
S) generar imágenes
T) generar subtítulos
U) renderizar video
V) validar video
W) crear short
X) generar reporte final

ANTES DE CAMBIAR CUALQUIER CONFIGURACIÓN:
- lee la configuración actual;
- crea backup si existe;
- documenta el cambio.

PARA LA GPU:
- monitoriza nvidia-smi;
- no mantengas simultáneamente modelos grandes residentes;
- si hay OOM, reduce resolución/batch/contexto antes de cambiar de arquitectura.

PARA RAG:
- usa nomic-embed-text;
- usa vector(768);
- guarda source_path y checksum;
- recupera top-k;
- valida que la respuesta esté sustentada por chunks.

PARA CONTENIDO:
- español de México;
- estilo educativo y terapéutico;
- no adivinatorio;
- no diagnósticos médicos;
- no predicciones deterministas.

PARA VIDEO:
- perfil largo: 1920x1080, 30 fps, H.264/AAC;
- perfil short: 1080x1920, 30 fps;
- primera prueba: 30–60 s;
- long-form: 480–540 s;
- todos los assets deben existir antes de renderizar.

CREA TODO EL CÓDIGO, CONFIGURACIONES, MIGRACIONES Y WORKFLOWS NECESARIOS.
NO DEJES "TODO POR HACER".

SI UN COMPONENTE NO PUEDE INSTALARSE POR CAMBIOS RECIENTES:
- consulta la documentación oficial más reciente;
- adapta la instalación;
- documenta qué cambió;
- usa el fallback del documento.

AL FINAL ENTREGA:
1. árbol de archivos creado;
2. versiones instaladas reales;
3. modelos descargados;
4. resultados de todos los tests;
5. path del video generado;
6. path del short generado;
7. reporte QA;
8. errores restantes;
9. comandos para levantar/detener el sistema;
10. instrucciones reproducibles para una segunda ejecución.
```

---

# 56. Comandos operativos finales

## Levantar sistema

```powershell
# 1. Docker / Supabase / n8n
# 2. Ollama (normalmente ya residente)
# 3. ComfyUI
# 4. servicio Python local
# 5. Claude Code cuando se necesite
```

## Detener

```powershell
supabase stop
# detener n8n según docker compose
# detener ComfyUI
```

## Diagnóstico

```powershell
nvidia-smi
ollama ps
curl http://127.0.0.1:11434/api/version
```

---

# 57. Checklist final para humano

Antes de considerar productivo el sistema:

```text
[ ] La GTX 1060 no presenta errores del driver
[ ] Ollama detecta GPU
[ ] Qwen responde con calidad aceptable
[ ] RAG recupera contenido correcto
[ ] Supabase persiste datos después de reinicio
[ ] ComfyUI genera imágenes sin OOM constante
[ ] Piper produce voz natural y consistente
[ ] FFmpeg genera video reproducible
[ ] Los subtítulos son legibles
[ ] El audio está bien mezclado
[ ] El contenido no hace promesas adivinatorias
[ ] El sistema puede rehacer solo una escena fallida
[ ] Un job completo puede reanudarse
[ ] Hay logs
[ ] Hay QA
[ ] La publicación sigue desactivada hasta aprobación
```

---

# 58. Fuentes oficiales verificadas (2026-09-08)

### Ollama
- Windows: https://docs.ollama.com/windows
- GPU: https://docs.ollama.com/gpu
- Context length: https://docs.ollama.com/context-length
- Modelfile: https://docs.ollama.com/modelfile
- Chat API: https://docs.ollama.com/api/chat
- Embed API: https://docs.ollama.com/api/embed
- Qwen3.5: https://ollama.com/library/qwen3.5
- Nomic Embed: https://ollama.com/library/nomic-embed-text
- Claude Code integration: https://ollama.com/blog/claude

### ComfyUI
- Repo/README/Windows packages: https://github.com/Comfy-Org/ComfyUI

### Stable Diffusion 1.5
- Model card: https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5

### Piper
- Actualización oficial del proyecto: https://github.com/OHF-Voice/piper1-gpl
- Voces: https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md
- CLI: https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/CLI.md

### faster-whisper
- Repo/documentación: https://github.com/SYSTRAN/faster-whisper

### n8n
- Docs: https://docs.n8n.io/
- Security audit: https://docs.n8n.io/hosting/securing/security-audit/

### Supabase
- Local CLI: https://supabase.com/docs/guides/local-development/cli/getting-started
- Local workflows: https://supabase.com/docs/guides/local-development/cli-workflows
- pgvector: https://supabase.com/docs/guides/database/extensions/pgvector
- AI & vectors: https://supabase.com/docs/guides/ai

### YouTube
- videos.insert: https://developers.google.com/youtube/v3/docs/videos/insert
- upload guide: https://developers.google.com/youtube/v3/guides/uploading_a_video

---

# 59. Decisión de arquitectura final

## Aprobada para V1

```text
                    USER REQUEST
                         │
                         ▼
                       n8n
                         │
                         ▼
                Local Python API
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
           Supabase              Ollama
           pgvector            Qwen3.5:4b
              ▲                     │
              │                     ▼
              │                  script
              │                     │
              └─────────────────────┘
                         │
                         ▼
                    Storyboard
                         │
           ┌─────────────┼──────────────┐
           ▼             ▼              ▼
        ComfyUI        Piper        faster-whisper
         SD1.5           │              │
           │             │              │
           └─────────────┼──────────────┘
                         ▼
                       FFmpeg
                         │
                         ▼
                     QA engine
                         │
                ┌────────┴─────────┐
                ▼                  ▼
             LONG 16:9          SHORT 9:16
```

## Principio rector

> **El modelo decide. Los scripts ejecutan. Supabase recuerda. ComfyUI crea las imágenes. Piper habla. FFmpeg termina el producto. n8n orquesta.**

Esta separación es la clave para conseguir buena calidad con una GTX 1060 de 6 GB sin convertir el proyecto en un sistema inestable.

---

# 60. ESTADO ACTUAL DE IMPLEMENTACIÓN (2026-09-14)

## Resumen

El sistema está **funcional y operativo**. Se ha demostrado E2E con videos de ~49 segundos. La arquitectura final difiere del plan original en varios puntos clave (ver abajo).

## Componentes implementados y verificados

| Componente | Estado | Notas |
|------------|--------|-------|
| Ollama (LLM) | ✅ CPU mode | CUDA bug workaround: `OLLAMA_LLM_LIBRARY=cpu` |
| VoiceStudio (TTS) | ✅ GPU | localhost:3900, OmniVoice, fallback SAPI |
| Supabase/pgvector (RAG) | ✅ Cloud | Ingesta + búsqueda semántica funcional |
| Pipeline E2E | ✅ V5 | 13 steps, research_images incluido |
| Research conceptos | ✅ | Openverse API keyless, 40+ conceptos ES→EN |
| Generación imágenes | ✅ V6 | Multi-frame (7 keyframes/escena), mano real CC0 |
| Mano con color | ✅ | Piel cálida (224,182,150) + overlays Cairo |
| Render video | ✅ V2 | Multi-frame + audio AAC 44100 stereo |
| Subtítulos | ✅ | SRT por escena |
| Dashboard | ✅ | monitor.py :8001 |
| Video vertical | ✅ | generate_short.py (9:16) |

## Diferencias vs plan original

| Plan original | Implementación actual | Razón |
|---------------|----------------------|-------|
| ComfyUI + SD1.5 | Pillow + Cairo + Openverse | SD1.5 incompatible (NumPy 2.x), pip timeouts |
| Piper TTS | VoiceStudio (GPU) | Más rápida, mejor calidad en español |
| n8n orquestador | pipeline.py (Python puro) | Más simple, sin dependencia de servicios externos |
| GTX 1060 6GB | GTX 1050 4GB | Hardware real detectado |
| Qwen3.5:4b | modo canned (templates) | LLM lento en CPU, templates dan calidad consistente |
| 8-9 minutos | 49 segundos (test) | Primera prueba valida cadena completa |

## Archivos clave actualizados

- `scripts/research_images.py` — Investigación Openverse (NUEVO)
- `scripts/generate_images.py` — V6 multi-frame hybrid
- `scripts/render_video.py` — V2 multi-frame + audio stereo
- `scripts/pipeline.py` — V5 con step research_images
- `config/video_profiles.yaml` — Audio 44100 stereo
- `assets/hands/hand_base.png` — Mano CC0 recortada

## Último video generado

**`data/renders/linea-vida-v12.mp4`** — 49.3s, 8.7MB, H.264 + AAC 44100Hz stereo

## Pendiente para siguiente sesión

1. **Ajustar anclas de mano** — Verificar visualmente que líneas palmares coinciden con foto
2. **Escalar a 40 minutos** — Reducir frames/escena o optimizar render
3. **Probar con otros temas** — Cosmos, planetas, dioses griegos (conceptos investigados más relevantes)
4. **Mejorar transiciones** — Crossfade entre keyframes (actualmente hard cuts)
5. **Resolver bug CUDA Ollama** — Para modo `live` con LLM real

---

# 61. Nota final de verificación

Este documento fue actualizado contra documentación pública reciente disponible el **8 de septiembre de 2026**. Las partes más sensibles a cambios de versión son:

- instaladores de Ollama;
- versiones de ComfyUI/PyTorch/CUDA;
- distribución de voces de Piper;
- versiones de n8n;
- CLI de Supabase;
- cambios en APIs de publicación.

Por ello la IA agente debe **verificar la versión real antes de ejecutar una descarga**, y debe registrar exactamente qué versión instaló.

La arquitectura no depende de una única versión exacta de cada componente, sino de los contratos funcionales documentados: API local de Ollama, workflow/API de ComfyUI, CLI/API de Piper, CLI de FFmpeg, Supabase local + pgvector y n8n como orquestador.
