# Especificación de Diseño: Voz Natural con VoiceStudio + SAPI

- **Fecha:** 2026-09-12 (rev. 3 — implementación verificada)
- **Proyecto:** F:\__AGENCIA_AIMA\D_OLLAMA_VIDEO
- **Estado:** Implementado y verificado

---

## 1. Contexto y Objetivos

El sistema actual cuenta con un pipeline E2E funcional que utiliza Windows SAPI para generar archivos `.wav` de narración por escena. Aunque Windows SAPI permite validar la cadena de renderizado, su calidad de voz robótica no se alinean con los requisitos de producción (español de México, entonación natural).

**Objetivo (implementado):**
Narración **natural** en español mediante una **cadena de motores TTS con degradación controlada**:

```
1. VoiceStudio API local (localhost:3900)   ← voz natural es-MX, selector femenino/masculino (GPU)
2. Windows SAPI                              ← fallback (último recurso)
```

**Resultado verificado en hardware real (GTX 1050 4 GB, driver 546.29):**
- VoiceStudio v0.5.2 instalado, backend en `localhost:3900`, modelo OmniVoice descargado.
- **GPU activa:** PyTorch 2.8.0+cu128 soporta `sm_61` (Pascal). El modelo carga en VRAM (~2.7 GB) y sintetiza en **~15 s por escena** (vs >2 min en CPU).
- Selector de género `female|male` funcionando vía campo `instruct`.
- **Clonación de voz descartada en esta máquina:** requiere ~6 GB de VRAM (tokenizador de audio + modelo), OOM en 4 GB. Se documenta como pendiente para hardware con más VRAM.

---

## 2. Arquitectura de Componentes

### 2.0 VoiceStudio (motor principal — voz natural)
- **Instalación:** MSI x64 current-user desde https://github.com/debpalash/VoiceStudio/releases/latest (instalado en `C:\Users\mauri\AppData\Local\VoiceStudio (Current User)`).
- **API local:** backend FastAPI en `http://localhost:3900` (solo loopback, sin API key en localhost).
- **Endpoint de síntesis:** `POST /v1/audio/speech`
  ```json
  {
    "model": "tts-1",
    "voice": "alloy",
    "input": "<texto de narración>",
    "response_format": "wav",
    "language": "es",
    "instruct": "female | male"
  }
  ```
- **Selector de género:** el campo `instruct` acepta `female` o `male` (taxonomía del motor). Verificado: ambas voces se generan en GPU.
- **Licencias (importante):** el motor por defecto **OmniVoice usa pesos CC-BY-NC (no comercial)**. Para producción comercial de AIMA hay que instalar **CosyVoice 3 (Apache-2.0)** o **PocketTTS (CC-BY-4.0)** desde el Model Catalogue. Esto queda pendiente (requiere descargas adicionales).
- **Health check:** `GET http://localhost:3900/.well-known/voicestudio-speech`.

### 2.1 Dependencias (SAPI, fallback)
- Windows SAPI está incluido en Windows 10/11 — no requiere instalación.
- El pipeline actual **no** usa Piper (se omitió: VoiceStudio cubre el caso principal y SAPI el fallback).

### 2.2 Motor de Síntesis en `scripts/generate_tts.py`
- Argumentos CLI:
  - `--engine auto|voicestudio|sapi` (por defecto `auto`).
  - `--gender female|male` (solo VoiceStudio; por defecto `female`, o `VOICESTUDIO_GENDER`).
  - `--voicestudio-url` (por defecto `http://127.0.0.1:3900`, o `VOICESTUDIO_BASE_URL`).
  - `--voicestudio-voice` (por defecto `alloy`, o `VOICESTUDIO_VOICE`).
- Comportamiento `auto`:
  1. Health check de VoiceStudio (timeout 3s). Si responde, síntesis vía `POST /v1/audio/speech`.
  2. Si falla, fallback a `generate_sapi_wav`.
- `voice.json` registra por escena `"voice_engine": "voicestudio" | "sapi"` y `"gender"`.

### 2.3 Formato y Compatibilidad de Audio
- VoiceStudio API devuelve WAV (PCM s16le, 24 kHz, mono).
- `generate_subtitles.py` (faster-whisper) y `render_video.py` (FFmpeg) ya aceptan WAV genérico; FFmpeg normaliza a AAC 48 kHz en el render final.

---

## 3. Manejo de Errores y Seguridad

- **VoiceStudio como proceso independiente:** gestiona su propia VRAM; el pipeline solo consume su API HTTP. Si la app no corre, el health check falla rápido (3s) y degrada a SAPI sin bloquear el E2E.
- **Recuperación de OOM:** si una clonación fallida contamina el contexto CUDA, reiniciar VoiceStudio (el backend recupera la VRAM). Documentado en el flujo de operación.
- **Sanitización de texto** y **validación de salida** (WAV > 0 bytes) por escena.
- **Licencias:** OmniVoice por defecto es CC-BY-NC (no comercial). Para producción comercial, instalar CosyVoice 3 o PocketTTS desde el Model Catalogue.

---

## 4. Verificación (resultados reales)

1. ✅ VoiceStudio v0.5.2 instalado; backend en `:3900` responde.
2. ✅ Modelo `k2-fsa/OmniVoice` descargado (2.4 GB).
3. ✅ GPU activa: PyTorch detecta CUDA sm_61; síntesis ~15 s/escena.
4. ✅ Muestras `demo_femenina.wav` y `demo_masculina.wav` generadas en `data/audio/voicestudio_test/`.
5. ✅ `generate_tts.py --engine auto --gender female|male` genera las 5 escenas con `voice_engine: voicestudio`.
6. ✅ Cadena de fallback: con VoiceStudio caído usa SAPI automáticamente.
7. ✅ `scripts/start_all.ps1` (arranque rápido) y `scripts/monitor.py` (dashboard :8001) funcionando.
8. ⚠️ Clonación de voz personalizada: OOM en 4 GB VRAM — pendiente para hardware con ≥6 GB.
