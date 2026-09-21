"""
Validate Licenses — verifica que todos los componentes tengan licencia comercial válida.
"""
import csv
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
LICENSES_DIR = PROJECT_DIR / "licenses"

REQUIRED_CSVS = ["SOFTWARE.csv", "MODELS.csv", "VOICES.csv", "ASSETS.csv"]


def validate(commercial=True):
    issues = []

    for csv_name in REQUIRED_CSVS:
        csv_path = LICENSES_DIR / csv_name
        if not csv_path.exists():
            issues.append(f"Missing license file: {csv_name}")
            continue

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if commercial and row.get("commercial_use", "").upper() != "YES":
                    issues.append(f"Non-commercial in {csv_name}: {row.get('name', '?')}")
                if row.get("status", "").upper() not in ("VERIFIED", "BUNDLED", "FROZEN"):
                    issues.append(f"Unverified in {csv_name}: {row.get('name', '?')}")

    return issues


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--commercial", action="store_true")
    args = parser.parse_args()

    issues = validate(commercial=args.commercial)
    if issues:
        print(f"FAIL: {len(issues)} issues")
        for i in issues[:20]:
            print(f"  - {i}")
        sys.exit(1)
    else:
        print("PASS: All licenses valid")
        sys.exit(0)
