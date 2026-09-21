"""
Genera archivos de narración WAV por escena usando síntesis de voz TTS.

Cadena de motores (orden de prioridad):
  1. VoiceStudio (local, API compatible con OpenAI en localhost:3900) — voz
     natural en GPU. Soporta selector de género femenino/masculino.
  2. Windows SAPI (fallback integrado en Windows, sin dependencias).

Parámetros:
  --storyboard <ruta_json>
  --output-dir <carpeta_salida>
  --engine auto|voicestudio|sapi
  --gender female|male      (solo VoiceStudio)
  --voicestudio-url <url>   (default: http://127.0.0.1:3900)
  --voice-name <nombre_voz_sapi>
"""
import sys
import os
import json
import argparse
import subprocess
import wave
import struct
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent.parent

# Procedencia de las voces (para la puerta comercial fail-closed).
VOICE_PROVENANCE = {
    "voicestudio": {
        "voice_model": "OmniVoice",
        "voice_id": "alloy",
        "license_status": "BLOCKED",   # CC-BY-NC, no monetizable
        "commercial_use": "NO",
    },
    "sapi": {
        "voice_model": "Microsoft SAPI",
        "voice_id": "system-default",
        "license_status": "UNVERIFIED",
        "commercial_use": "UNVERIFIED",
    },
}

VOICESTUDIO_HEALTH_PATH = "/.well-known/voicestudio-speech"
VOICESTUDIO_SPEECH_PATH = "/v1/audio/speech"


def voicestudio_available(base_url: str, timeout: float = 3.0) -> bool:
    """Health check ligero de VoiceStudio (timeout corto, sin bloquear el E2E)."""
    try:
        with urllib.request.urlopen(
            base_url.rstrip("/") + VOICESTUDIO_HEALTH_PATH, timeout=timeout
        ) as resp:
            return resp.status == 200
    except Exception:
        return False


def generate_voicestudio_wav(
    text: str, output_path: Path, base_url: str, gender: str = "female",
    voice: str = "alloy", timeout: float = 180.0,
) -> bool:
    """
    Genera WAV vía la API local de VoiceStudio (POST /v1/audio/speech).
    El parámetro `instruct` controla el género de la voz.
    """
    payload = {
        "model": "tts-1",
        "input": text,
        "voice": voice,
        "response_format": "wav",
        "language": "es",
        "instruct": gender,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + VOICESTUDIO_SPEECH_PATH,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            wav_bytes = resp.read()
        if not wav_bytes or len(wav_bytes) < 44:
            return False
        output_path.write_bytes(wav_bytes)
        return output_path.exists() and output_path.stat().st_size > 0
    except Exception as e:
        print(f"  VoiceStudio error: {e}")
        return False


def detect_spanish_sapi_voice() -> str:
    """Devuelve la primera voz SAPI en español instalada (p. ej. Sabina es-MX)."""
    ps = ('Add-Type -AssemblyName System.Speech;'
          '$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;'
          '($s.GetInstalledVoices()|Where-Object {$_.VoiceInfo.Culture.Name -like "es*"}'
          '|Select-Object -First 1).VoiceInfo.Name')
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, encoding="utf-8", timeout=30)
        name = (r.stdout or "").strip()
        return name or ""
    except Exception:
        return ""


def generate_sapi_wav(text: str, output_path: Path, voice_name: str = None,
                      rate: int = 0) -> bool:
    """
    Genera un WAV usando PowerShell + System.Speech.Synthesis.

    Si no se indica voz, elige la primera voz en español instalada (es-MX)
    para no leer texto español con una voz en inglés. `rate` va de -10 a 10.
    """
    if not voice_name:
        voice_name = detect_spanish_sapi_voice()
    safe_text = text.replace('"', "'").replace("`", "'").replace("$", "")
    ps_script = '''
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
'''
    if voice_name:
        ps_script += f'''
try {{
    $synth.SelectVoice("{voice_name}")
}} catch {{
    Write-Warning "Voz {voice_name} no encontrada, usando default"
}}
'''
    ps_script += f'''
$synth.Rate = {int(rate)}
$synth.SetOutputToWaveFile("{output_path}")
$synth.Speak("{safe_text}")
$synth.Dispose()
Write-Host "OK"
'''
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, encoding="utf-8", timeout=120
        )
        if result.returncode == 0 and output_path.exists():
            return True
        print(f"  SAPI stderr: {result.stderr[:200] if result.stderr else 'none'}")
        return False
    except Exception as e:
        print(f"  SAPI exception: {e}")
        return False


def get_wav_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate) if rate > 0 else 0
    except Exception:
        return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--storyboard", default=str(SCRIPT_DIR / "data" / "jobs" / "default" / "storyboard.json"))
    parser.add_argument("--output-dir", default=str(SCRIPT_DIR / "data" / "audio"))
    parser.add_argument("--engine", default="auto", choices=["auto", "voicestudio", "sapi"],
                        help="Motor TTS: auto (VoiceStudio con fallback a SAPI), voicestudio, sapi")
    parser.add_argument("--gender", default=os.environ.get("VOICESTUDIO_GENDER", "female"),
                        choices=["female", "male"], help="Género de la voz (solo VoiceStudio)")
    parser.add_argument("--voicestudio-url", default=os.environ.get("VOICESTUDIO_BASE_URL", "http://127.0.0.1:3900"))
    parser.add_argument("--voicestudio-voice", default=os.environ.get("VOICESTUDIO_VOICE", "alloy"))
    parser.add_argument("--voice", default=None, help="Nombre de voz SAPI (ej: 'Microsoft Sabina Desktop')")
    parser.add_argument("--rate", type=int, default=0, help="Ritmo SAPI (-10..10)")
    args = parser.parse_args()

    sb_path = Path(args.storyboard)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sb = json.loads(sb_path.read_text(encoding="utf-8"))
    scenes = sb["scenes"]

    use_voicestudio = args.engine in ("auto", "voicestudio")
    if use_voicestudio and args.engine == "auto" and not voicestudio_available(args.voicestudio_url):
        print("VoiceStudio no responde; usando fallback Windows SAPI.")
        use_voicestudio = False

    voice_meta = []
    for scene in scenes:
        scene_id = scene["id"]
        text = scene["narration"]
        out_path = out_dir / f"scene_{scene_id:03d}.wav"
        engine_used = "sapi"
        try:
            ok = False
            if use_voicestudio:
                ok = generate_voicestudio_wav(
                    text, out_path, args.voicestudio_url,
                    gender=args.gender, voice=args.voicestudio_voice,
                )
                if ok:
                    engine_used = "voicestudio"
            if not ok:
                ok = generate_sapi_wav(text, out_path, args.voice, rate=args.rate)
                engine_used = "sapi"
            if not ok:
                print(f"  Scene {scene_id} FAILED")
                continue
        except Exception as e:
            print(f"  Scene {scene_id} ERROR: {e}")
            continue

        duration = get_wav_duration(out_path)
        size = out_path.stat().st_size
        prov = dict(VOICE_PROVENANCE.get(engine_used, {}))
        if engine_used == "voicestudio":
            prov["voice_id"] = args.voicestudio_voice
            prov["voice_model"] = os.environ.get("VOICESTUDIO_MODEL", prov.get("voice_model", "OmniVoice"))
        elif engine_used == "sapi":
            prov["voice_id"] = args.voice or detect_spanish_sapi_voice() or "system-default"
        print(f"  Scene {scene_id}: {out_path.name} ({duration:.1f}s, {size:,} bytes) [{engine_used}]")
        voice_meta.append({
            "scene_id": scene_id,
            "narration": text,
            "file": out_path.name,
            "duration_sec": duration,
            "size_bytes": size,
            "voice_engine": engine_used,
            "gender": args.gender if engine_used == "voicestudio" else None,
            "voice_model": prov.get("voice_model"),
            "voice_id": prov.get("voice_id"),
            "license_status": prov.get("license_status"),
            "commercial_use": prov.get("commercial_use"),
            "created_at": datetime.now().isoformat()
        })

    voice_meta_path = SCRIPT_DIR / "data" / "jobs" / sb_path.parent.name / "voice.json"
    voice_meta_path.write_text(json.dumps({"scenes": voice_meta, "total_duration": sum(v["duration_sec"] for v in voice_meta)}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Metadata guardada en {voice_meta_path}")


if __name__ == "__main__":
    main()
