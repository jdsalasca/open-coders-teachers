"""Valida el mensaje de commit sin dependencias externas.

Uso:
  python tools/commit_msg.py .git/COMMIT_EDITMSG
  echo "feat(api): agrega timeout" | python tools/commit_msg.py -

Reglas:
- primera linea: tipo(scope): resumen  o  tipo: resumen
- tipo en TYPES, resumen en minuscula, sin punto final, 10..72 caracteres
- si hay cuerpo, explica el porque (minimo 20 caracteres)
- prohibido atribuir el cambio a un modelo o asistente (Co-authored-by / Signed-off-by)
- prohibido WIP o mensajes vacios

Sale 0 si el mensaje es valido, 1 si no, 2 si no pudo leer el archivo.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TYPES = (
    "feat",
    "fix",
    "docs",
    "test",
    "refactor",
    "perf",
    "build",
    "ci",
    "chore",
    "revert",
)

HEADER = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[a-z0-9_./-]+)\))?!?: (?P<summary>.+)$")
MIN_SUMMARY = 10
MAX_SUMMARY = 72
MIN_BODY = 20
MODEL_ATTRIBUTION = re.compile(
    r"^(?:co-authored-by|signed-off-by):.*\b(?:gpt|claude|codex|copilot|gemini|llm|"
    r"anthropic|openai|deepseek|assistant|model)\b",
    re.IGNORECASE | re.MULTILINE,
)


def _clean(raw: str) -> str:
    """Quita comentarios de git y normaliza los saltos finales."""
    lines = [line for line in raw.splitlines() if not line.lstrip().startswith("#")]
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines).strip()


def validate(raw: str) -> list[str]:
    """Devuelve la lista de problemas; vacia si el mensaje es valido."""
    message = _clean(raw)
    if not message:
        return ["el mensaje esta vacio"]

    problems: list[str] = []
    header, _, body = message.partition("\n\n")
    header = header.splitlines()[0].strip()
    match = HEADER.match(header)

    if not match:
        problems.append(
            "la primera linea debe ser 'tipo(scope): resumen' o 'tipo: resumen'"
        )
    else:
        kind = match.group("type")
        summary = match.group("summary").strip()
        if kind not in TYPES:
            problems.append(f"tipo '{kind}' no permitido; usa uno de: {', '.join(TYPES)}")
        if summary[:1].isupper():
            problems.append("el resumen debe empezar en minuscula")
        if summary.endswith("."):
            problems.append("el resumen no lleva punto final")
        if not MIN_SUMMARY <= len(summary) <= MAX_SUMMARY:
            problems.append(
                f"el resumen debe tener entre {MIN_SUMMARY} y {MAX_SUMMARY} caracteres "
                f"(tiene {len(summary)})"
            )
        if re.search(r"\bwip\b", summary, re.IGNORECASE):
            problems.append("'WIP' no va en el mensaje; usa un commit que compile")

    body = body.strip()
    if body and len(body) < MIN_BODY:
        problems.append(
            f"si hay cuerpo, explica el porque (minimo {MIN_BODY} caracteres)"
        )

    if MODEL_ATTRIBUTION.search(message):
        problems.append(
            "no atribuyas el cambio a un modelo o asistente (Co-authored-by / Signed-off-by)"
        )

    return problems


def main(argv: list[str]) -> int:
    """Punto de entrada: lee el mensaje y reporta."""
    if len(argv) != 2:
        print("uso: python tools/commit_msg.py <archivo|-|>")
        return 2
    source = argv[1]
    try:
        raw = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    except OSError as error:
        print(f"[X] no pude leer {source}: {error}")
        return 2

    problems = validate(raw)
    if not problems:
        return 0
    print("[X] el mensaje de commit no cumple:")
    for problem in problems:
        print(f"  - {problem}")
    print("\nFormato: tipo(scope): resumen en imperativo")
    print("Ejemplo: feat(api): agrega timeout al cliente de precios")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
