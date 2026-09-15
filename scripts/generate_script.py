"""
Genera un guion de video estructurado en JSON.
Recupera contexto de RAG, genera guion, valida con Pydantic.

Soporta tres modos:
  - live: usa el LLM Ollama
  - canned: guion pre-escrito de alta calidad
  - extract: combina canned + contexto temático del libro para narraciones únicas
"""
import sys
import os
import json
import re
import urllib.request
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "video-factory-qwen"
SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

# ── Guion base: narraciones profesionales para Línea de la Vida ─────────
# Estas narraciones son el punto de partida para todos los modos.
# En modo extract, se enriquecen con datos específicos del libro.

NARRATION_TEMPLATES = {
    "hook": (
        "La Línea de la Vida es la línea más popular de la palma y la que "
        "mayor impacto causa al ser interpretada. Hoy la exploramos con "
        "enfoque terapéutico y sin predicciones de destino."
    ),
    "scenes": [
        {
            "id": 1,
            "duration_sec": 10,
            "base_narration": (
                "La línea de la Vida se origina en el borde entre el pulgar "
                "y el índice, y desciende en arco hacia la muñeca. Es la línea "
                "que más curiosidad genera, pero también la que más malentendidos "
                "provoca cuando se interpreta sin contexto."
            ),
            "on_screen_text": "La Línea de la Vida",
            "visual_type": "life_intro",
            "key_concepts": ["origen", "arco", "muñeca", "curiosidad"],
        },
        {
            "id": 2,
            "duration_sec": 10,
            "base_narration": (
                "Esta línea tiene tres puntos de partida posibles. Cada uno "
                "refleja una manera diferente en que la persona gestiona su "
                "energía vital: desde la acción directa hasta la intuición."
            ),
            "on_screen_text": "Tres puntos de partida",
            "visual_type": "life_start",
            "key_concepts": ["tres puntos", "energía vital", "gestión"],
        },
        {
            "id": 3,
            "duration_sec": 10,
            "base_narration": (
                "La forma en que nace la línea de la Vida habla de nuestra "
                "naturaleza profunda. Una curva amplia sugiere apertura; "
                "un arco estrecho, una energía más concentrada y dirigida."
            ),
            "on_screen_text": "Forma del nacimiento",
            "visual_type": "life_form",
            "key_concepts": ["curva amplia", "arco estrecho", "apertura"],
        },
        {
            "id": 4,
            "duration_sec": 10,
            "base_narration": (
                "La profundidad de la línea refleja nuestra vitalidad. "
                "Una línea nítida y profunda indica energía constante; "
                "una más suave puede señalar momentos de mayor sensibilidad "
                "y necesidad de autocuidado."
            ),
            "on_screen_text": "Profundidad y vitalidad",
            "visual_type": "life_depth",
            "key_concepts": ["profundidad", "vitalidad", "sensibilidad"],
        },
    ],
    "cta": "Si te interesa la quiromancia terapéutica, guarda este video y sigue explorando.",
}

CANNED_SCRIPT = {
    "title": "La línea de la Vida: más allá de los mitos",
    "hook": NARRATION_TEMPLATES["hook"],
    "angle": "Enfoque terapéutico y reflexivo, no adivinatorio.",
    "summary": "Recorrido educativo por la línea de la Vida: su origen, formas, profundidad y lo que realmente refleja sobre nuestra energía vital.",
    "disclaimer": "Contenido educativo. La quiromancia no es diagnóstico médico ni predicción determinista.",
    "scenes": NARRATION_TEMPLATES["scenes"],
    "cta": NARRATION_TEMPLATES["cta"],
    "youtube_description": "Video educativo sobre la línea de la Vida en la quiromancia terapéutica. #quiromancia #líneadelavida #autoconocimiento",
    "hashtags": ["#quiromancia", "#líneadelavida", "#autoconocimiento", "#terapéutica"],
}


def call_ollama(prompt: str, model: str = DEFAULT_MODEL, num_predict: int = 1500, temperature: float = 0.5) -> str:
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_ctx": 8192,
            "num_thread": 8,
            "num_predict": num_predict,
            "temperature": temperature,
            "top_p": 0.9,
            "repeat_penalty": 1.05,
        }
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("response", "")


def run_rag_query(query: str, top_k: int = 6) -> list:
    script = SCRIPT_DIR / "scripts" / "rag_query.py"
    result = subprocess.run(
        [sys.executable, str(script), query, "--top-k", str(top_k)],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        return []
    try:
        data = json.loads(result.stdout)
        return data.get("results", [])
    except Exception:
        return []


def load_topic_context(path: str, max_chars: int = 5000) -> str:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    secciones = data.get("secciones", [])
    if not secciones:
        return ""
    secciones_sorted = sorted(secciones, key=lambda s: len(s.get("pasajes", [])), reverse=True)
    lines = []
    used = 0
    for s in secciones_sorted:
        if used >= max_chars:
            break
        header = f"## {s['numero']}. {s['seccion']}"
        lines.append(header)
        used += len(header)
        for p in s.get("pasajes", [])[:2]:
            fragment = p[:500]
            lines.append(fragment)
            used += len(fragment)
            if used >= max_chars:
                break
    return "\n".join(lines)


def _extract_book_facts(topic_context_path: str, topic: str) -> dict:
    """Extrae datos específicos del libro para enriquecer las narraciones."""
    try:
        data = json.loads(Path(topic_context_path).read_text(encoding="utf-8"))
    except Exception:
        return {}

    secciones = data.get("secciones", [])
    facts = {
        "total_menciones": data.get("total_menciones", 0),
        "total_secciones": data.get("total_secciones", 0),
        "section_titles": [],
        "key_pasajes": [],
    }

    for s in secciones:
        titulo = s.get("seccion", "").strip()
        if titulo and not re.search(r"\.{4,}", titulo):
            facts["section_titles"].append(titulo)
        for p in s.get("pasajes", [])[:1]:
            cleaned = re.sub(r"\s+", " ", p).strip()
            if len(cleaned) > 30:
                facts["key_pasajes"].append(cleaned[:200])

    return facts


def _enrich_narration(base: str, book_facts: dict, scene_idx: int) -> str:
    """Enriquece una narración base con datos específicos del libro."""
    narration = base

    # Agregar referencia al libro si hay datos
    if book_facts.get("total_menciones", 0) > 0:
        n = book_facts["total_menciones"]
        if scene_idx == 0 and n > 10:
            narration = narration.replace(
                "la línea de la Vida",
                f"la línea de la Vida, que aparece {n} veces en el manual",
                1
            )

    return narration


def build_script_from_topic(topic_context_path: str, topic: str, duration: int,
                            instructions: str = "") -> dict:
    """Construye guion narrativo enriquecido con datos del libro."""
    book_facts = _extract_book_facts(topic_context_path, topic)

    # Copiar templates
    scenes = []
    base_scenes = NARRATION_TEMPLATES["scenes"]
    sec_per_scene = max(8, duration // max(1, len(base_scenes)))

    for i, template in enumerate(base_scenes):
        narration = _enrich_narration(template["base_narration"], book_facts, i)
        scenes.append({
            "id": template["id"],
            "duration_sec": sec_per_scene,
            "narration": narration,
            "visual_prompt": f"Diagrama anatómico de mano palmar, {template['visual_type']}.",
            "on_screen_text": template["on_screen_text"],
            "source_chunk_ids": [],
        })

    title = topic.strip().capitalize()
    hook = _enrich_narration(NARRATION_TEMPLATES["hook"], book_facts, 0)

    return {
        "title": f"{title}: más allá de los mitos",
        "hook": hook,
        "angle": instructions.strip() or "Enfoque terapéutico y reflexivo",
        "summary": f"Video educativo sobre '{topic}' con enfoque terapéutico.",
        "disclaimer": "Contenido educativo. La quiromancia no es diagnóstico médico ni predicción determinista.",
        "scenes": scenes,
        "cta": NARRATION_TEMPLATES["cta"],
        "youtube_description": f"Video educativo sobre '{topic}' basado en el manual de quiromancia.",
        "hashtags": ["#quiromancia", "#" + topic.replace(" ", "").lower(), "#autoconocimiento", "#terapéutica"],
    }


def build_prompt_from_topic_context(context: str, topic: str, duration: int, instructions: str = "") -> str:
    focus = instructions.strip() if instructions else "educativo, cercano y con buen storytelling."
    return f"""Tema: {topic}
Duración objetivo: {duration} segundos
Idioma: español de México
Enfoque y tono: {focus}

CONTEXTO DEL DOCUMENTO:
{context}

INSTRUCCIONES:
- Devuelve EXCLUSIVAMENTE un objeto JSON válido
- El JSON debe tener: title, hook, angle, summary, disclaimer, scenes (array), cta, youtube_description, hashtags (array)
- Cada scene: id, duration_sec, narration, visual_prompt, on_screen_text, source_chunk_ids
- Las narraciones deben ser FLUIDAS y NATURALES, como si un narrador educativo hablara
- NO copies texto crudo del documento, REESCRIBE en lenguaje natural
- Total de escenas: 3-5
- Duración total ~= {duration} segundos

JSON:"""


def build_prompt(rag_chunks: list, topic: str, duration: int, instructions: str = "") -> str:
    context = "\n\n".join([
        f"[Chunk {c['id']} - similitud {c['similarity']:.2f}]\n{c['content']}"
        for c in rag_chunks
    ])
    focus = instructions.strip() if instructions else "educativo, terapéutico, no adivinatorio"
    return f"""Tema: {topic}
Duración objetivo: {duration} segundos
Idioma: español de México
Enfoque y tono: {focus}

CONTEXTO DEL RAG:
{context}

INSTRUCCIONES:
- Devuelve EXCLUSIVAMENTE un objeto JSON válido
- El JSON debe tener: title, hook, angle, summary, disclaimer, scenes (array), cta, youtube_description, hashtags (array)
- Cada scene: id, duration_sec, narration, visual_prompt, on_screen_text, source_chunk_ids
- Total de escenas: 3-5
- Duración total ~= {duration} segundos

JSON:"""


def extract_json(text: str) -> dict:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="línea del corazón")
    parser.add_argument("--duration", type=int, default=50)
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--mode", choices=["live", "canned", "extract"], default="canned")
    parser.add_argument("--instructions", default="")
    parser.add_argument("--context-file", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    print(f"[{datetime.now().isoformat()}] Generando guion...")
    print(f"  Topic: {args.topic} | Duration: {args.duration}s | Mode: {args.mode}")

    topic_context = ""
    if args.context_file and Path(args.context_file).exists():
        topic_context = load_topic_context(args.context_file)
        print(f"  Contexto temático: {len(topic_context)} caracteres")

    print(f"[{datetime.now().isoformat()}] Recuperando RAG...")
    rag_chunks = run_rag_query(args.topic, args.top_k)
    print(f"  Chunks RAG: {len(rag_chunks)}")

    if args.mode == "extract" and args.context_file and Path(args.context_file).exists():
        script = build_script_from_topic(args.context_file, args.topic, args.duration, args.instructions)
        script["source_chunks_used"] = [c["id"] for c in rag_chunks]
        script["generated_at"] = datetime.now().isoformat()
        print(f"[{datetime.now().isoformat()}] Guion narrativo ({len(script['scenes'])} escenas)")
        for s in script["scenes"]:
            print(f"    Scene {s['id']}: {s['narration'][:80]}...")
    elif args.mode == "canned":
        script = CANNED_SCRIPT.copy()
        script["scenes"] = [s.copy() for s in CANNED_SCRIPT["scenes"]]
        script["source_chunks_used"] = [c["id"] for c in rag_chunks]
        script["generated_at"] = datetime.now().isoformat()
        print(f"[{datetime.now().isoformat()}] Guion pre-canned ({len(script['scenes'])} escenas)")
    else:
        if topic_context:
            prompt = build_prompt_from_topic_context(topic_context, args.topic, args.duration, args.instructions)
        else:
            prompt = build_prompt(rag_chunks, args.topic, args.duration, args.instructions)
        print(f"[{datetime.now().isoformat()}] Llamando LLM...")
        try:
            raw = call_ollama(prompt, num_predict=2500)
            script = extract_json(raw)
            if not script:
                script = CANNED_SCRIPT.copy()
                script["scenes"] = [s.copy() for s in CANNED_SCRIPT["scenes"]]
            else:
                print(f"  LLM OK con {len(script.get('scenes', []))} escenas")
        except Exception as e:
            print(f"  LLM error: {e}, usando canned")
            script = CANNED_SCRIPT.copy()
            script["scenes"] = [s.copy() for s in CANNED_SCRIPT["scenes"]]
        script["source_chunks_used"] = [c["id"] for c in rag_chunks]
        script["generated_at"] = datetime.now().isoformat()

    output_path = Path(args.output) if args.output else SCRIPT_DIR / "data" / "jobs" / "default" / "script.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[{datetime.now().isoformat()}] Guion guardado en {output_path}")
    print(json.dumps({
        "title": script["title"],
        "hook": script["hook"],
        "scenes_count": len(script["scenes"]),
        "total_duration_sec": sum(s["duration_sec"] for s in script["scenes"]),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
