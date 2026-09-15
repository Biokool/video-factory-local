"""
Genera embeddings de un texto usando Ollama (nomic-embed-text, 768 dimensiones).
"""
import sys
import json
import urllib.request

OLLAMA_URL = "http://127.0.0.1:11434"


def get_embedding(text: str, model: str = "nomic-embed-text") -> list:
    payload = json.dumps({"model": model, "input": text}).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["embeddings"][0]


def main():
    if len(sys.argv) < 2:
        print("Uso: python generate_embeddings.py 'texto'")
        sys.exit(1)
    text = " ".join(sys.argv[1:])
    emb = get_embedding(text)
    print(json.dumps({
        "model": "nomic-embed-text",
        "dimensions": len(emb),
        "first_values": emb[:5],
        "last_values": emb[-5:],
    }, indent=2))


if __name__ == "__main__":
    main()
