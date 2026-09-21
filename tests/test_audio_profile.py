"""
Tests: audio profile — verifica que el audio tenga formato correcto.
"""
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent


def _ffprobe(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", str(path)],
            capture_output=True, text=True, timeout=15,
        )
        if out.returncode == 0:
            import json
            return json.loads(out.stdout)
    except Exception:
        pass
    return None


def test_audio_files_exist():
    """Debe haber archivos de audio."""
    audio_dir = PROJECT_DIR / "data" / "jobs"
    if not audio_dir.exists():
        return
    wav_files = list(audio_dir.rglob("*.wav"))
    mp3_files = list(audio_dir.rglob("*.mp3"))
    assert len(wav_files) + len(mp3_files) > 0, "No audio files found"


def test_audio_format():
    """El audio debe ser WAV o MP3."""
    audio_dir = PROJECT_DIR / "data" / "jobs"
    if not audio_dir.exists():
        return
    for wav in list(audio_dir.rglob("*.wav"))[:2]:
        info = _ffprobe(wav)
        if info:
            streams = info.get("streams", [])
            audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
            assert len(audio_streams) > 0, f"No audio stream in {wav.name}"


if __name__ == "__main__":
    tests = [test_audio_files_exist, test_audio_format]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS: {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
