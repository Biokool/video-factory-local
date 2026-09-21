from pathlib import Path
import re, json, sys
ROOT=Path(__file__).resolve().parents[2]
issues=[]
for p in ROOT.rglob('*'):
    if not p.is_file() or any(x in p.parts for x in ('.git','.venv','venv')): continue
    if p.suffix.lower() not in {'.py','.ps1','.md','.yaml','.yml','.json','.env','.txt'}: continue
    try: s=p.read_text(encoding='utf-8',errors='ignore')
    except Exception: continue
    if re.search(r'postgresql://[^:\s]+:[^@\s]+@',s) and p.name!='.env.example': issues.append([str(p.relative_to(ROOT)),'posible secreto DB'])
    for bad in ['La Linea','Linea de la','Monte de Jupiter','QUIROMANCIA TERAPEUTICA']:
        if bad in s: issues.append([str(p.relative_to(ROOT)),f'ortografía: {bad}'])
    if 'C:\\Users\\mauri' in s or 'F:\\__AGENCIA_AIMA' in s: issues.append([str(p.relative_to(ROOT)),'ruta absoluta'])
print(json.dumps({'passed':not issues,'issues':issues},ensure_ascii=False,indent=2))
sys.exit(0 if not issues else 1)
