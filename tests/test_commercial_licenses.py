"""
Tests: commercial licenses — verifica que todos los componentes tengan licencia comercial.
"""
import csv
import sys
from pathlib import Path

LICENSES_DIR = Path(__file__).resolve().parent.parent / "licenses"


def test_software_licenses():
    csv_path = LICENSES_DIR / "SOFTWARE.csv"
    assert csv_path.exists(), "SOFTWARE.csv not found"
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            assert row.get("commercial_use", "").upper() == "YES", \
                f"Non-commercial software: {row.get('name')}"


def test_model_licenses():
    csv_path = LICENSES_DIR / "MODELS.csv"
    assert csv_path.exists(), "MODELS.csv not found"
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            assert row.get("commercial_use", "").upper() == "YES", \
                f"Non-commercial model: {row.get('name')}"


def test_voice_licenses():
    csv_path = LICENSES_DIR / "VOICES.csv"
    assert csv_path.exists(), "VOICES.csv not found"
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status", "").upper() != "BLOCKED":
                assert row.get("commercial_use", "").upper() == "YES", \
                    f"Non-commercial voice: {row.get('name')}"


if __name__ == "__main__":
    tests = [test_software_licenses, test_model_licenses, test_voice_licenses]
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
