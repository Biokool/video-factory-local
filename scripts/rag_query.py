"""
Búsqueda semántica en Supabase/pgvector.
Genera embedding de la consulta con Ollama y llama a la función RPC match_document_chunks.
"""
import sys
import os
import json
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


def main():
    if len(sys.argv) < 2:
        print("Uso: python rag_query.py 'pregunta' [--top-k N] [--category X]")
        sys.exit(1)
    query = sys.argv[1]
    top_k = 6
    category = None
    if "--top-k" in sys.argv:
        idx = sys.argv.index("--top-k")
        top_k = int(sys.argv[idx + 1])
    if "--category" in sys.argv:
        idx = sys.argv.index("--category")
        category = sys.argv[idx + 1]

    emb = get_embedding(query)
    print(f"Embedding generado: {len(emb)} dimensiones")

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    emb_str = "[" + ",".join(f"{x}" for x in emb) + "]"

    cur.execute(
        """
        SELECT id, documento_id, seccion_id, contenido, categoria, metadatos, similitud
        FROM public.buscar_fragmentos(%s::vector, %s, %s)
        """,
        (emb_str, top_k, category)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    results = []
    for row in rows:
        results.append({
            "id": row[0],
            "document_id": str(row[1]),
            "seccion_id": row[2],
            "content": row[3],
            "categoria": row[4],
            "metadata": row[5],
            "similarity": float(row[6]),
        })

    print(json.dumps({
        "query": query,
        "top_k": top_k,
        "results": results,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
