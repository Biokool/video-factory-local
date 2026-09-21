"""
Ingesta de un documento Markdown en Supabase/pgvector.
- Lee el archivo .md
- Divide en chunks semánticos
- Genera embeddings con Ollama/nomic-embed-text (768 dims)
- Inserta en public.documents y public.document_chunks
"""
import sys
import os
import json
import hashlib
import re
import urllib.request
import psycopg2
from pathlib import Path

# Cargar variables de entorno desde .env (proyecto raíz)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

OLLAMA_URL = "http://127.0.0.1:11434"
DB_URL = os.environ.get(
    "SUPABASE_DB_URL",
    "postgresql://postgres:postgres@127.0.0.1:54322/video_factory"
)


def get_embedding(text: str, model: str = "nomic-embed-text") -> list:
    payload = json.dumps({"model": model, "input": text}).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["embeddings"][0]


def chunk_text(text: str, max_chars: int = 1500, overlap_chars: int = 200) -> list:
    """Divide en chunks y conserva el rango (inicio, fin) en el texto normalizado."""
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    paragraphs = []
    pos = 0
    for raw in text.split("\n\n"):
        p = raw.strip()
        if not p:
            pos += len(raw) + 2
            continue
        start = text.find(p, pos)
        if start < 0:
            start = pos
        paragraphs.append((p, start, start + len(p)))
        pos = start + len(p)
    chunks = []
    cur_text = ""
    cur_start = cur_end = 0
    for p, s, e in paragraphs:
        if len(cur_text) + len(p) + 2 <= max_chars:
            if not cur_text:
                cur_start = s
            cur_text = (cur_text + "\n\n" + p).strip() if cur_text else p
            cur_end = e
        else:
            if cur_text:
                chunks.append((cur_text, cur_start, cur_end))
                tail = cur_text[-overlap_chars:]
                cur_text = (tail + "\n\n" + p).strip()
                cur_start = max(cur_start, e - len(cur_text))
                cur_end = e
            else:
                cur_text = p
                cur_start, cur_end = s, e
    if cur_text:
        chunks.append((cur_text, cur_start, cur_end))
    return chunks


def chunk_strings(text: str, max_chars: int = 1500, overlap_chars: int = 200) -> list:
    return [c[0] for c in chunk_text(text, max_chars, overlap_chars)]


def file_checksum(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


# Taxonomía de quiromancia para categorizar fragmentos automáticamente
_CATEGORIAS = [
    ("linea_vida", ["línea de la vida", "linea de la vida", "línea de vida"]),
    ("linea_corazon", ["línea del corazón", "linea del corazón", "línea del corazon"]),
    ("linea_cabeza", ["línea de la cabeza", "linea de la cabeza"]),
    ("linea_mercurio", ["línea de mercurio", "linea de mercurio"]),
    ("linea_marte", ["línea de marte", "linea de marte"]),
    ("monte_venus", ["monte de venus"]),
    ("monte_jupiter", ["monte de júpiter", "monte de jupiter"]),
    ("monte_marte", ["monte de marte"]),
    ("monte_mercurio", ["monte de mercurio"]),
    ("monte_apolo", ["monte de apolo"]),
    ("dedo_pulgar", ["dedo pulgar", "dedo de venus"]),
    ("dedo_indice", ["dedo índice", "dedo indice", "dedo de júpiter", "dedo de jupiter"]),
    ("dedo_medio", ["dedo medio", "dedo de saturno"]),
    ("dedo_anular", ["dedo anular", "dedo de apolo"]),
    ("dedo_menique", ["dedo meñique", "dedo menique", "dedo de mercurio"]),
    ("quiromagia", ["quiromagia", "quiro", "psicomagia"]),
]


def infer_category(text: str, fallback: str = None) -> str:
    low = text.lower()
    for cat, terms in _CATEGORIAS:
        for t in terms:
            if t in low:
                return cat
    return fallback or "general"


_HEADER_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){0,2})[.)]?\s+(.+)$")


def extract_sections(content: str) -> list:
    """Extrae (numero, titulo, contenido, inicio, fin) de las secciones.

    Detecta encabezados tipo '4. La Línea de la Vida' y devuelve el rango
    de caracteres en el texto normalizado para poder vincular chunks.
    """
    lines = content.split("\n")
    sections = []
    current = None
    offset = 0
    for ln in lines:
        s = ln.strip()
        m = _HEADER_RE.match(s)
        if m and len(s) < 90 and re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]", m.group(2)):
            if current:
                current["fin"] = offset
                sections.append(current)
            current = {"numero": m.group(1), "titulo": m.group(2).strip(),
                       "contenido": [], "inicio": offset}
        elif current is not None:
            current["contenido"].append(ln)
        offset += len(ln) + 1
    if current:
        current["fin"] = offset
        sections.append(current)
    return [(s["numero"], s["titulo"], "\n".join(s["contenido"]).strip(),
             s["inicio"], s["fin"]) for s in sections]


def nearest_section_index(sections: list, chunk_start: int, chunk_end: int) -> int:
    """Asocia un chunk a la sección con mayor solapamiento de rango.

    sections: lista de tuplas (numero, titulo, contenido, inicio, fin).
    Devuelve el índice de la sección o None si no hay solapamiento.
    """
    best_idx = None
    best_overlap = 0
    for i, sec in enumerate(sections):
        if len(sec) < 5:
            continue
        s_start, s_end = sec[3], sec[4]
        overlap = max(0, min(chunk_end, s_end) - max(chunk_start, s_start))
        if overlap > best_overlap:
            best_overlap = overlap
            best_idx = i
    if best_idx is None:
        # fallback: sección cuyo inicio es el mayor que no supera al chunk
        for i, sec in enumerate(sections):
            if len(sec) >= 5 and sec[3] <= chunk_start:
                best_idx = i
    if best_idx is None and sections:
        # ultimo recurso: la sección de inicio más cercano (evita huérfanos)
        best_idx = min(
            range(len(sections)),
            key=lambda i: abs(sections[i][3] - chunk_start) if len(sections[i]) >= 5 else 1 << 30)
    return best_idx


def main():
    if len(sys.argv) < 2:
        print("Uso: python rag_ingest.py <ruta_md> [--category X]")
        sys.exit(1)
    md_path = Path(sys.argv[1])
    category = None
    if "--category" in sys.argv:
        idx = sys.argv.index("--category")
        category = sys.argv[idx + 1]

    if not md_path.exists():
        print(f"ERROR: archivo no encontrado: {md_path}")
        sys.exit(1)

    content = md_path.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1) if title_match else md_path.stem

    chunks = chunk_text(content)
    checksum = file_checksum(md_path)
    print(f"Documento: {md_path.name}")
    print(f"  Title: {title}")
    print(f"  Chunks: {len(chunks)}")
    print(f"  Checksum: {checksum[:16]}...")

    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()

    # Eliminar documento previo (por source_path) y reingestar
    cur.execute("DELETE FROM public.documentos WHERE source_path = %s", (str(md_path),))
    cur.execute(
        """
        INSERT INTO public.documentos (source_path, source_name, categoria, titulo, contenido, checksum_sha256, metadatos)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (str(md_path), md_path.name, category, title, content, checksum,
         json.dumps({"categoria": category} if category else {}))
    )
    document_id = cur.fetchone()[0]
    print(f"  Document ID: {document_id}")

    # Extraer secciones (índice estructural) para storytelling cronológico
    sections = extract_sections(content)
    section_id_map = {}
    print(f"  Secciones detectadas: {len(sections)}")
    for i, sec in enumerate(sections):
        numero, sec_titulo, sec_content = sec[0], sec[1], sec[2]
        cur.execute(
            """
            INSERT INTO public.secciones (documento_id, numero, titulo, orden, contenido)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (document_id, numero, sec_titulo, i, sec_content)
        )
        section_id_map[i] = cur.fetchone()[0]

    embeddings_count = 0
    orphan_count = 0
    for i, (chunk, c_start, c_end) in enumerate(chunks):
        try:
            emb = get_embedding(chunk)
            chunk_category = infer_category(chunk, category)
            sec_idx = nearest_section_index(sections, c_start, c_end)
            seccion_id = section_id_map.get(sec_idx, None)
            if seccion_id is None:
                orphan_count += 1
            cur.execute(
                """
                INSERT INTO public.fragmentos
                  (documento_id, seccion_id, chunk_index, contenido, token_count, categoria, metadatos, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector)
                """,
                (document_id, seccion_id, i, chunk, len(chunk.split()),
                 chunk_category,
                 json.dumps({"categoria": category, "rango": [c_start, c_end]} if category
                            else {"rango": [c_start, c_end]}),
                 "[" + ",".join(f"{x}" for x in emb) + "]")
            )
            embeddings_count += 1
            print(f"    Chunk {i+1}/{len(chunks)} OK ({len(chunk.split())} tokens) "
                  f"[{chunk_category}] seccion={sec_idx}")
        except Exception as e:
            print(f"    Chunk {i+1} ERROR: {e}")

    conn.commit()
    cur.close()
    conn.close()

    print(json.dumps({
        "document_id": str(document_id),
        "chunks_inserted": embeddings_count,
        "embeddings_generated": embeddings_count,
        "secciones": len(sections),
        "orphans": orphan_count,
        "checksum": checksum,
    }, indent=2))


if __name__ == "__main__":
    main()
