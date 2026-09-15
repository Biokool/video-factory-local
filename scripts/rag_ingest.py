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
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""
    for p in paragraphs:
        if len(current) + len(p) + 2 <= max_chars:
            current = (current + "\n\n" + p).strip() if current else p
        else:
            if current:
                chunks.append(current)
                current = current[-overlap_chars:] + "\n\n" + p
            else:
                current = p
    if current:
        chunks.append(current)
    return chunks


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
    """Extrae (numero, titulo, contenido) de las secciones del documento,
    detectando encabezados tipo '4. La Línea de la Vida'."""
    lines = content.split("\n")
    sections = []
    current = None
    for ln in lines:
        s = ln.strip()
        m = _HEADER_RE.match(s)
        if m and len(s) < 90 and re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]", m.group(2)):
            if current:
                sections.append(current)
            current = {"numero": m.group(1), "titulo": m.group(2).strip(), "contenido": []}
        elif current is not None:
            current["contenido"].append(ln)
    if current:
        sections.append(current)
    return [(s["numero"], s["titulo"], "\n".join(s["contenido"]).strip()) for s in sections]


def nearest_section_index(sections: list, chunk_index: int) -> int:
    """Asocia un chunk (por índice) a la sección más cercana (aproximación)."""
    # Como no mapeamos chunks a líneas exactas, devolvemos None; el caller
    # puede asociar por similitud de texto si se requiere. Aquí devolvemos None.
    return None


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
    for i, (numero, sec_titulo, sec_content) in enumerate(sections):
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
    for i, chunk in enumerate(chunks):
        try:
            emb = get_embedding(chunk)
            chunk_category = infer_category(chunk, category)
            seccion_id = section_id_map.get(nearest_section_index(sections, i), None)
            cur.execute(
                """
                INSERT INTO public.fragmentos
                  (documento_id, seccion_id, chunk_index, contenido, token_count, categoria, metadatos, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector)
                """,
                (document_id, seccion_id, i, chunk, len(chunk.split()),
                 chunk_category,
                 json.dumps({"categoria": category} if category else {}),
                 "[" + ",".join(f"{x}" for x in emb) + "]")
            )
            embeddings_count += 1
            print(f"    Chunk {i+1}/{len(chunks)} OK ({len(chunk.split())} tokens) [{chunk_category}]")
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
        "checksum": checksum,
    }, indent=2))


if __name__ == "__main__":
    main()
