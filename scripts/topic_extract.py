"""
Extracción temática de un documento Markdown (proveniente de PDF).

Dado un tema (ej. "línea de la vida"), recorre el documento completo y:
  1. Detecta la estructura de secciones/encabezados (patrón "N." / "N.N.").
  2. Encuentra todos los pasajes que mencionan el tema.
  3. Los ordena cronológicamente (según su posición en el libro).
  4. Genera un resumen estructurado con la sección de origen de cada pasaje.

Salida: JSON con:
  - tema
  - total_menciones
  - secciones: [{seccion, subsecciones, pasajes}]
  - contexto_completo (texto concatenado en orden cronológico, para el LLM)

Uso:
  python topic_extract.py <doc.md> --topic "línea de la vida" [--output x.json]
"""
import sys
import json
import re
import argparse
from pathlib import Path


# Patrón de encabezado: "4. La Línea de la Vida" o "4.1. Interpretación..."
_HEADER_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){0,2})[.)]?\s+(.+)$")


def clean_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    return text


# Líneas de ruido a descartar de los pasajes
_NOISE_LINES = {
    "CURSO PROFESIONAL DE QUIROMANCIA",
    "CURSO PROFESIONAL DE",
    "SUMARIO",
}


def _is_noise(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if s in _NOISE_LINES:
        return True
    # números de página sueltos
    if re.fullmatch(r"\d{1,3}", s):
        return True
    # marcadores de página <!-- página N -->
    if re.fullmatch(r"<!--\s*página\s+\d+\s*-->", s):
        return True
    # líneas que son solo puntos de índice (muchos '...')
    if s.count(".") > 10 and len(s) < 90:
        return True
    return False


def build_sections(lines: list) -> list:
    """Recorre el documento y agrupa las líneas por encabezado de sección."""
    sections = []          # lista de {number, title, start, end}
    current = None
    for i, raw in enumerate(lines):
        line = raw.strip()
        m = _HEADER_RE.match(line)
        if m and len(line) < 90:
            number = m.group(1)
            title = m.group(2).strip()
            # evita falsos positivos como números de página sueltos
            if number.count(".") >= 0 and re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]", title):
                if current:
                    current["end"] = i
                    sections.append(current)
                current = {"number": number, "title": title, "start": i, "end": None}
    if current:
        current["end"] = len(lines)
        sections.append(current)
    return sections


def find_mentions(lines: list, topic: str) -> list:
    """Devuelve índices de líneas que mencionan el tema (sin acentos, case-insensitive)."""
    def norm(s):
        s = s.lower()
        for a, b in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")]:
            s = s.replace(a, b)
        return s
    topic_norm = norm(topic)
    idxs = []
    for i, line in enumerate(lines):
        if topic_norm in norm(line):
            idxs.append(i)
    return idxs


def section_for_index(sections: list, idx: int) -> dict | None:
    for s in sections:
        if s["start"] <= idx < s["end"]:
            return s
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("doc", help="Ruta del documento Markdown")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    doc_path = Path(args.doc)
    if not doc_path.exists():
        print(f"ERROR: documento no encontrado: {doc_path}")
        sys.exit(1)

    text = clean_text(doc_path.read_text(encoding="utf-8"))
    lines = text.split("\n")

    sections = build_sections(lines)
    mention_idx = find_mentions(lines, args.topic)

    if not mention_idx:
        print(json.dumps({"tema": args.topic, "total_menciones": 0, "secciones": []}, ensure_ascii=False))
        print(f"Sin menciones del tema '{args.topic}'")
        sys.exit(0)

    # Agrupar menciones por sección, en orden cronológico (ya están ordenadas)
    by_section = {}
    order = []
    for idx in mention_idx:
        sec = section_for_index(sections, idx)
        key = sec["number"] if sec else "¿?"
        title = sec["title"] if sec else "(sin sección)"
        if key not in by_section:
            by_section[key] = {"seccion": title, "numero": key, "pasajes": []}
            order.append(key)
        # pasaje: línea + contexto de 2 líneas alrededor, filtrando ruido
        ctx_start = max(0, idx - 1)
        ctx_end = min(len(lines), idx + 3)
        pasaje_lines = [ln for ln in lines[ctx_start:ctx_end] if not _is_noise(ln)]
        pasaje = " ".join(pasaje_lines).strip()
        # evitar duplicar el mismo pasaje en la misma sección
        if pasaje and pasaje not in by_section[key]["pasajes"]:
            by_section[key]["pasajes"].append(pasaje)

    secciones = [by_section[k] for k in order]

    # Contexto completo en orden cronológico (para el LLM)
    contexto = []
    for s in secciones:
        contexto.append(f"## {s['numero']}. {s['seccion']}")
        for p in s["pasajes"]:
            contexto.append(p)
        contexto.append("")
    contexto_completo = "\n".join(contexto)

    result = {
        "tema": args.topic,
        "total_menciones": len(mention_idx),
        "total_secciones": len(secciones),
        "secciones": secciones,
        "contexto_completo": contexto_completo,
    }

    out_path = Path(args.output) if args.output else doc_path.with_suffix(".topic.json")
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({
        "tema": args.topic,
        "total_menciones": len(mention_idx),
        "total_secciones": len(secciones),
        "secciones_detectadas": [f"{s['numero']}. {s['seccion']}" for s in secciones],
    }, indent=2, ensure_ascii=False))
    print(f"Contexto guardado en {out_path}")


if __name__ == "__main__":
    main()
