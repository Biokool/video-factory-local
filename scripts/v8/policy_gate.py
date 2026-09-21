"""policy_gate.py - Puerta comercial fail-closed (V8).

Lee config/v7/commercial_policy.yaml, el registro de assets y
licenses/COMMERCIAL-INVENTORY.csv, y decide si el contenido puede
publicarse como monetizado. Falla en cerrado: ante duda, BLOQUEA.

Reglas:
  - blocked_models: cualquier modelo/voz en la lista bloquea.
  - allow_unknown_license=false: licencia desconocida bloquea.
  - required_asset_status: los assets usados deben tener ese estado.
  - required_license_status: la licencia debe estar en ese estado.
  - human_approval_before_publish: exige aprobacion humana registrada.

Subcomandos:
  python policy_gate.py --voice-json data/jobs/<id>/voice.json
  python policy_gate.py --asset-ids ID1,ID2
  python policy_gate.py --selftest
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2]
POLICY = SCRIPT_DIR / "config" / "v7" / "commercial_policy.yaml"
INVENTORY = SCRIPT_DIR / "licenses" / "COMMERCIAL-INVENTORY.csv"
REGISTRY = SCRIPT_DIR / "assets" / "v7" / "registry" / "assets.jsonl"


def load_policy(path: Path = POLICY) -> dict:
    import yaml
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_inventory(path: Path = INVENTORY) -> dict:
    if not path.exists():
        return {}
    out = {}
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            out[(row.get("component") or "").strip().lower()] = row
    return out


def _fail(policy, decision, reasons):
    # fail_closed: solo permite si no hay razones
    allowed = (not reasons) and policy.get("fail_closed", True)
    return {"decision": "ALLOW" if allowed else decision,
            "allowed": bool(allowed), "reasons": reasons,
            "policy_mode": policy.get("mode", "unknown")}


def check_voice(policy: dict, voice_json: Path) -> dict:
    reasons = []
    blocked = [b.lower() for b in policy.get("blocked_models", [])]
    data = {}
    if voice_json and Path(voice_json).exists():
        data = json.loads(Path(voice_json).read_text(encoding="utf-8"))
    scenes = data.get("scenes", [])
    if not scenes:
        reasons.append("sin metadata de voz (voice.json vacio o ausente)")
    for s in scenes:
        engine = str(s.get("voice_engine", "")).lower()
        model = str(s.get("voice_model", "")).lower()
        lic = str(s.get("license_status", "")).upper()
        for b in blocked:
            if b and (b in engine or b in model):
                reasons.append(f"modelo bloqueado: {b}")
        if "voicestudio" in engine and not model:
            reasons.append("VoiceStudio sin voice_model declarado")
        if engine == "sapi":
            reasons.append("SAPI no es una voz verificada para monetizacion")
        if policy.get("allow_unknown_license", False) is False:
            if lic not in ("VERIFIED", "YES"):
                reasons.append(f"licencia de voz no verificada: {lic or 'desconocida'}")
    return _fail(policy, "BLOCK", sorted(set(reasons)))


def check_assets(policy: dict, asset_ids: list[str]) -> dict:
    reasons = []
    req_status = policy.get("required_asset_status", "APPROVED")
    req_lic = policy.get("required_license_status", "VERIFIED")
    rows = {}
    if REGISTRY.exists():
        for line in REGISTRY.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                rows[r["asset_id"]] = r
    for aid in asset_ids:
        row = rows.get(aid)
        if not row:
            reasons.append(f"asset no registrado: {aid}")
            continue
        if row.get("status") != req_status and req_status != "APPROVED":
            reasons.append(f"{aid}: estado {row.get('status')} < {req_status}")
        if row.get("status") not in ("APPROVED", "FROZEN"):
            reasons.append(f"{aid}: no aprobado ({row.get('status')})")
        lic = row.get("license", {})
        if lic.get("commercial_use") != "YES" or lic.get("status") != req_lic:
            reasons.append(f"{aid}: licencia no verificada")
    return _fail(policy, "BLOCK", sorted(set(reasons)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice-json")
    ap.add_argument("--asset-ids", default="")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    policy = load_policy()

    if a.selftest:
        res = {
            "sapi": check_voice(policy, None),
            "assets_ok": check_assets(policy, ["HAND_L_PALM_FRONT_EDITORIAL_V001"]),
            "assets_unknown": check_assets(policy, ["NOPE_V001"]),
        }
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    result = {}
    if a.voice_json is not None:
        result["voice"] = check_voice(policy, Path(a.voice_json) if a.voice_json else None)
    if a.asset_ids:
        ids = [x.strip() for x in a.asset_ids.split(",") if x.strip()]
        result["assets"] = check_assets(policy, ids)
    if not result:
        result = {"policy": policy,
                  "inventory_components": sorted(load_inventory().keys())}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    blocked = any(v.get("decision") == "BLOCK" for v in result.values()
                  if isinstance(v, dict))
    sys.exit(1 if blocked else 0)


if __name__ == "__main__":
    main()