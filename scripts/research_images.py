"""
Investigacion automatica de imagenes por concepto - V1.

Extrae conceptos visuales de la narracion/visual_prompt de cada escena,
busca imagenes reales en Openverse (solo licencias CC0/PDM) y las descarga
a un cache local reutilizable.

Si la narracion menciona una manzana -> busca foto de manzana.
Si menciona el cosmos -> nebulosa. Si el simbolo del sol -> sol.
Fallback: conceptos derivados del topic general.

Uso:
  python research_images.py --storyboard <storyboard.json> --topic "..." \
      --output-dir data/research

Escribe research.json:
  {
    "concepts": {"manzana": {"query": ..., "file": ..., "url": ..., "license": ...}},
    "scenes": {"1": ["manzana"], ...}
  }
"""
import sys
import json
import argparse
import unicodedata
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent.parent
UA = "AIMA-VideoFactory/1.0 (educational; local cache)"
MIN_DIM = 500
TIMEOUT = 25

# clave normalizada -> (etiqueta legible, query EN para Openverse)
CONCEPTS = {
    "manzana":       ("Manzana", "red apple fruit"),
    "cosmos":        ("Cosmos", "galaxy nebula stars deep space"),
    "universo":      ("Cosmos", "galaxy nebula stars deep space"),
    "galaxia":       ("Galaxia", "spiral galaxy astronomy"),
    "nebulosa":      ("Nebulosa", "nebula deep space hubble"),
    "estrella":      ("Estrellas", "starry night sky milky way"),
    "estrellas":     ("Estrellas", "starry night sky milky way"),
    "sol":           ("El Sol", "sun solar nasa"),
    "luna":          ("La Luna", "full moon night sky"),
    "planeta":       ("Planetas", "solar system planets nasa"),
    "planetas":      ("Planetas", "solar system planets nasa"),
    "tierra":        ("La Tierra", "earth from space blue planet"),
    "mercurio":      ("Mercurio", "mercury planet space"),
    "venus":         ("Venus", "venus planet space"),
    "marte":         ("Marte", "mars planet red surface"),
    "jupiter":       ("Jupiter", "jupiter planet space"),
    "saturno":       ("Saturno", "saturn planet rings space"),
    "zeus":          ("Zeus", "zeus statue greek god"),
    "dios":          ("Dioses griegos", "greek god statue mythology"),
    "dioses":        ("Dioses griegos", "greek god statue mythology"),
    "mitologia":     ("Mitologia griega", "greek mythology ancient statue"),
    "grecia":        ("Grecia antigua", "ancient greece acropolis temple"),
    "olimpo":        ("Monte Olimpo", "mount olympus greece clouds"),
    "mano":          ("Lectura de manos", "palmistry palm hand reading"),
    "manos":         ("Lectura de manos", "palmistry palm hand reading"),
    "palma":         ("Palma", "palmistry palm hand closeup"),
    "quiromancia":   ("Quiromancia", "palmistry hand reading fortune"),
    "nacimiento":    ("Nacimiento", "newborn baby hand"),
    "corazon":       ("Corazon", "red heart symbol love"),
    "energia":       ("Energia", "light energy abstract glow"),
    "naturaleza":    ("Naturaleza", "forest nature landscape sunlight"),
    "agua":          ("Agua", "water drops river clear"),
    "fuego":         ("Fuego", "flame fire burning"),
    "aire":          ("Aire", "clouds sky wind"),
    "montana":       ("Montana", "mountain landscape peaks"),
    "cerebro":       ("Cerebro", "human brain anatomy"),
    "cuerpo":        ("Cuerpo humano", "human body anatomy"),
    "antiguo":       ("Mundo antiguo", "ancient ruins columns"),
    "egipto":        ("Egipto", "ancient egypt hieroglyph pyramid"),
    "simbolo":       ("Simbolos", "mystic symbols esoteric"),
    "tarot":         ("Tarot", "tarot cards mystic"),
}

MAX_PER_SCENE = 3


def norm(txt: str) -> str:
    txt = unicodedata.normalize("NFD", txt.lower())
    txt = "".join(c for c in txt if unicodedata.category(c) != "Mn")
    return txt


def extract_concepts(texts):
    """Devuelve lista de claves de conceptos en orden de aparicion."""
    found = []
    for text in texts:
        words = norm(text or "").replace("(", " ").replace(")", " ").replace(",", " ").replace(".", " ").split()
        for w in words:
            key = w.strip(":;¡!¿?")
            if key in CONCEPTS and key not in found:
                found.append(key)
            # singulares simples
            elif key.endswith("s") and key[:-1] in CONCEPTS and key[:-1] not in found:
                found.append(key[:-1])
    return found[:MAX_PER_SCENE]


def openverse_search(query: str, limit: int = 6):
    url = (f"https://api.openverse.org/v1/images/?q={urllib.parse.quote(query)}"
           f"&license=cc0,pdm&page_size={limit}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = json.loads(r.read().decode("utf-8"))
        return data.get("results", [])
    except Exception as e:
        print(f"  [openverse] ERROR busqueda '{query}': {e}")
        return []


def download_valid(url: str, dest: Path) -> bool:
    """Descarga y valida con PIL; guarda JPEG RGB normalizado."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read()
        from io import BytesIO
        from PIL import Image
        im = Image.open(BytesIO(raw))
        im.load()
        if min(im.size) < MIN_DIM:
            return False
        im = im.convert("RGB")
        im.save(dest, "JPEG", quality=88)
        return True
    except Exception as e:
        print(f"  [download] ERROR {url[:80]}: {e}")
        return False


def research_concept(key: str, cache_dir: Path) -> dict | None:
    label, query = CONCEPTS[key]
    dest = cache_dir / f"{key}.jpg"
    if dest.exists():
        return {"query": query, "file": str(dest), "url": "cache", "license": "cache"}
    results = openverse_search(query)
    for r in results:
        u = r.get("url") or ""
        if not u.startswith("http"):
            continue
        if download_valid(u, dest):
            return {"query": query, "file": str(dest), "url": u,
                    "license": r.get("license", "?"), "title": r.get("title", "")[:80]}
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--storyboard", required=True)
    p.add_argument("--topic", default="")
    p.add_argument("--output-dir", default=str(SCRIPT_DIR / "data" / "research"))
    a = p.parse_args()

    sb = json.loads(Path(a.storyboard).read_text(encoding="utf-8"))
    cache = Path(a.output_dir)
    cache.mkdir(parents=True, exist_ok=True)

    topic_concepts = extract_concepts([a.topic, sb.get("hook", "")])

    scenes_map = {}
    concepts_db = {}

    for sc in sb.get("scenes", []):
        sid = str(sc["id"])
        texts = [sc.get("narration"), sc.get("base_narration"), sc.get("visual_prompt"),
                 sc.get("on_screen_text"), a.topic]
        keys = extract_concepts(texts)
        if not keys:
            keys = topic_concepts[:2]
        resolved = []
        for k in keys:
            if k not in concepts_db:
                info = research_concept(k, cache)
                if info:
                    concepts_db[k] = {"label": CONCEPTS[k][0], **info}
                    print(f"  concepto '{k}' OK -> {Path(info['file']).name}")
                else:
                    concepts_db[k] = None
            if concepts_db[k]:
                resolved.append(k)
        scenes_map[sid] = resolved
        print(f"Escena {sid}: conceptos {resolved or '(sin panel)'}")

    out = {
        "generated_at": datetime.now().isoformat(),
        "concepts": {k: v for k, v in concepts_db.items() if v},
        "scenes": scenes_map,
    }
    out_path = Path(a.storyboard).parent / "research.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"concepts": len(out["concepts"]), "file": str(out_path)}, indent=2))


if __name__ == "__main__":
    main()
