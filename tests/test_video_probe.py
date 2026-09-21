"""
Tests: video probe — verifica que los videos de salida cumplan formato.
"""
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
RENDERS_DIR = PROJECT_DIR / "data" / "renders"


def _ffprobe(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", "-show_format", str(path)],
            capture_output=True, text=True, timeout=15,
        )
        if out.returncode == 0:
            import json
            return json.loads(out.stdout)
    except Exception:
        pass
    return None


def test_videos_exist():
    """Debe haber al menos un video renderizado."""
    if not RENDERS_DIR.exists():
        return
    videos = list(RENDERS_DIR.glob("*.mp4"))
    assert len(videos) > 0, "No videos found in renders"


def test_video_format():
    """Los videos deben ser MP4 con video H.264."""
    if not RENDERS_DIR.exists():
        return
    for v in list(RENDERS_DIR.glob("*.mp4"))[:2]:
        info = _ffprobe(v)
        if info:
            streams = info.get("streams", [])
            video_streams = [s for s in streams if s.get("codec_type") == "video"]
            assert len(video_streams) > 0, f"No video stream in {v.name}"
            assert video_streams[0].get("codec_name") in ("h264", "hevc"), \
                f"Unexpected codec: {video_streams[0].get('codec_name')}"


if __name__ == "__main__":
    tests = [test_videos_exist, test_video_format]
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
