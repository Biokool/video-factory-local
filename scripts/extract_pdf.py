"""
Extrae texto de un archivo PDF y lo convierte en Markdown para ingesta RAG.

Uso:
  python extract_pdf.py <ruta.pdf> [--output <ruta.md>]

El texto se limpia (líneas en blanco, encabezados) y se guarda como .md.
"""
import sys
import re
import argparse
from pathlib import Path


def extract_pdf_text(pdf_path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append(f"<!-- página {i + 1} -->\n\n{text}")
    return "\n\n".join(pages)


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [ln.rstrip() for ln in text.split("\n")]
    return "\n".join(lines).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", help="Ruta del archivo PDF")
    parser.add_argument("--output", default=None, help="Ruta de salida .md")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"ERROR: PDF no encontrado: {pdf_path}")
        sys.exit(1)

    raw = extract_pdf_text(pdf_path)
    cleaned = clean_text(raw)

    if not cleaned.strip():
        print("ERROR: no se pudo extraer texto (¿PDF escaneado sin OCR?)")
        sys.exit(1)

    out_path = Path(args.output) if args.output else pdf_path.with_suffix(".md")
    out_path.write_text(cleaned, encoding="utf-8")

    print(json_result := __import__("json").dumps({
        "source": str(pdf_path),
        "output": str(out_path),
        "chars": len(cleaned),
        "lines": len(cleaned.split("\n")),
    }, indent=2, ensure_ascii=False))
    print(f"Texto extraído: {len(cleaned)} caracteres -> {out_path}")


if __name__ == "__main__":
    main()
