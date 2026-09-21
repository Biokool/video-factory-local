"""
SVG Sanitizer — elimina elementos peligrosos de SVGs antes de renderizar.

Cumple §20 de la especificación maestra: elimina scripts, foreignObject,
enlaces externos, eventos JS, URLs remotas, entidades XML.
"""
import re
from pathlib import Path

# Patrones peligrosos
_DANGEROUS_TAGS = re.compile(
    r'<(script|foreignObject|iframe|object|embed|applet|form|input|button|'
    r'select|textarea|link|meta|base)\b[^>]*>.*?</\1>',
    re.IGNORECASE | re.DOTALL,
)
_DANGEROUS_SELF_CLOSING = re.compile(
    r'<(script|foreignObject|iframe|object|embed|applet|link|meta|base)\b[^>]*/?>',
    re.IGNORECASE,
)
_DANGEROUS_ATTRS = re.compile(
    r'\s+(on\w+|xlink:href|href|src|action|formaction|data|codebase|dynsrc|lowsrc)\s*=\s*["\'][^"\']*["\']',
    re.IGNORECASE,
)
_DANGEROUS_URLS = re.compile(
    r'url\s*\(\s*["\']?\s*(https?://|ftp://|file://)',
    re.IGNORECASE,
)
_XML_ENTITIES = re.compile(r'<!ENTITY\b[^>]*>', re.IGNORECASE)
_EXTERNAL_REFS = re.compile(
    r'(\bhref\s*=\s*["\'])(https?://|ftp://|file://|//)',
    re.IGNORECASE,
)


def sanitize_svg(svg_text: str) -> tuple[str, list[str]]:
    """
    Limpia un SVG de elementos peligrosos.
    Retorna (svg_limpio, lista_de_amenazas_detectadas).
    """
    threats = []
    cleaned = svg_text

    # Eliminar tags peligrosos completos
    for match in _DANGEROUS_TAGS.finditer(cleaned):
        threats.append(f"TAG: {match.group(1)}")
    cleaned = _DANGEROUS_TAGS.sub("", cleaned)

    # Eliminar self-closing peligrosos
    for match in _DANGEROUS_SELF_CLOSING.finditer(cleaned):
        threats.append(f"TAG: {match.group(1)}")
    cleaned = _DANGEROUS_SELF_CLOSING.sub("", cleaned)

    # Eliminar atributos peligrosos (event handlers, etc.)
    for match in _DANGEROUS_ATTRS.finditer(cleaned):
        attr_name = match.group(1).split("=")[0].strip()
        threats.append(f"ATTR: {attr_name}")
    cleaned = _DANGEROUS_ATTRS.sub("", cleaned)

    # Eliminar URLs externas en CSS
    for match in _DANGEROUS_URLS.finditer(cleaned):
        threats.append(f"URL: {match.group(1)[:50]}")
    cleaned = _DANGEROUS_URLS.sub("url(data:)", cleaned)

    # Eliminar entidades XML
    for match in _XML_ENTITIES.finditer(cleaned):
        threats.append("ENTITY")
    cleaned = _XML_ENTITIES.sub("", cleaned)

    # Eliminar referencias externas en href
    for match in _EXTERNAL_REFS.finditer(cleaned):
        threats.append(f"HREF: {match.group(2)[:30]}")
    cleaned = _EXTERNAL_REFS.sub(r"\1", cleaned)

    return cleaned, threats


def sanitize_svg_file(input_path: Path, output_path: Path | None = None) -> dict:
    """
    Sanitiza un archivo SVG y guarda el resultado.
    Retorna reporte de sanitización.
    """
    svg_text = input_path.read_text(encoding="utf-8")
    cleaned, threats = sanitize_svg(svg_text)

    if output_path is None:
        output_path = input_path

    output_path.write_text(cleaned, encoding="utf-8")

    return {
        "input": str(input_path),
        "output": str(output_path),
        " threats_detected": len(threats),
        "threats": threats,
        "safe": len(threats) == 0,
        "original_size": len(svg_text),
        "cleaned_size": len(cleaned),
    }


def validate_svg_structure(svg_text: str) -> dict:
    """
    Valida que un SVG tenga la estructura requerida por la spec (§8).
    """
    issues = []

    # Verificar viewBox 2048x2048
    vb_match = re.search(r'viewBox\s*=\s*["\']([^"\']+)["\']', svg_text)
    if vb_match:
        parts = vb_match.group(1).split()
        if len(parts) == 4:
            w, h = float(parts[2]), float(parts[3])
            if w != 2048 or h != 2048:
                issues.append(f"viewBox={w}x{h}, requerido 2048x2048")
    else:
        issues.append("Sin viewBox definido")

    # Verificar IDs de dedos requeridos
    required_ids = ["hand-base", "palm-silhouette", "thumb", "index-finger",
                    "middle-finger", "ring-finger", "little-finger", "wrist"]
    for rid in required_ids:
        if f'id="{rid}"' not in svg_text:
            issues.append(f"Falta id='{rid}'")

    # Verificar que no tenga texto (el compositor lo añade)
    if re.search(r'<text\b', svg_text, re.IGNORECASE):
        issues.append("Contiene <text> (debe renderizar el compositor)")

    # Verificar que no tenga montes (el compositor los dibuja)
    if re.search(r'Monte|mount|jupiter|saturn|venus', svg_text, re.IGNORECASE):
        issues.append("Contiene montes (debe añadir el compositor)")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
    }


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Uso: python svg_sanitizer.py <archivo.svg> [--validate-only]")
        sys.exit(1)

    svg_path = Path(sys.argv[1])
    validate_only = "--validate-only" in sys.argv

    if not svg_path.exists():
        print(f"Error: {svg_path} no existe")
        sys.exit(1)

    svg_text = svg_path.read_text(encoding="utf-8")

    if validate_only:
        result = validate_svg_structure(svg_text)
    else:
        result = sanitize_svg_file(svg_path)

    print(json.dumps(result, indent=2, ensure_ascii=False))
