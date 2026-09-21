# Arquitectura V7

```mermaid
flowchart TD
  A[Manual PDF] --> B[Extractor por página y figura]
  B --> C[RAG temático: léxico + vectorial + relaciones]
  C --> D[Paquete de evidencia]
  U[Solicitud] --> E[Qwen 3.5 4B en CPU]
  D --> E
  E --> F[Guion JSON]
  F --> G[Storyboard JSON]
  G --> H[Validador y política comercial]
  H --> I[Selector por asset_id]
  I --> J[Mano maestra aprobada]
  I --> K[Líneas, montes y signos SVG]
  I --> L[Historia, mitología y fondos aprobados]
  J --> M[Compositor Pillow + Cairo]
  K --> M
  L --> M
  M --> N[Animaciones deterministas]
  G --> O[TTS comercial verificado]
  O --> P[Sincronización y subtítulos]
  N --> Q[FFmpeg por bloques]
  P --> Q
  Q --> R[QA técnico, editorial y de licencias]
  R --> S[Paquete de publicación]
```

## Ejecución en GTX 1050 4 GB
- Ollama en CPU como baseline estable.
- GPU para un solo consumidor pesado a la vez.
- ComfyUI opcional, aislado, SD 1.5, 512 px, batch 1.
- Nada de SDXL o FLUX como dependencia base.
- VoiceStudio solo con modelo comercial verificado.
- Composición, SVG, MediaPipe y FFmpeg pueden operar en CPU.

## Modos
- `legacy_v6`: reproducción y regresión.
- `v7_deterministic`: mano + SVG + assets aprobados.
- `v7_hybrid`: V7 determinista con generación opcional de fondos.
- `offline_production`: prohíbe red y assets no aprobados.
