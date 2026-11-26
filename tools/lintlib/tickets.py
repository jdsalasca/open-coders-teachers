"""Claves de ticket dentro de comentarios del codigo.

Una clave de seguimiento (`LETRAS-NUMERO`) solo tiene sentido para quien tiene acceso a
esa herramienta. En el codigo no aporta: el comentario debe explicar el motivo
tecnico, y la clave vive en la rama, el PR o el commit.

Se revisan **comentarios**, no strings ni identificadores: ahi esta el ruido que
nadie limpia y el que mas se copia de un archivo a otro.

La regla es accionable, no bloqueante: algunos repos usan pares `ABC-123` como
codigo de negocio y ahi seria un falso positivo.
"""

from __future__ import annotations

import re

from lintlib import quality
from lintlib.solid import Unit

# Claves tipo LETRAS-NUMERO. Se excluyen siglas tecnicas conocidas.
TICKET_KEY = re.compile(
    r"\b(?!UTF|ISO|SHA|MD5|HTTP|RFC|TLS|SSL|AES|RSA|JWT|OAUTH|CVE|GH|PR)"
    r"([A-Z][A-Z0-9]{1,9})-(\d{1,6})\b"
)

# Comentarios por familia de sintaxis. `#` solo en los lenguajes que lo usan.
HASH_COMMENT = re.compile(r"(?m)#[^\n]*")
SLASH_COMMENT = re.compile(r"(?m)//[^\n]*")
BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)

HASH_LANGUAGES = {"python"}
SLASH_LANGUAGES = {"go", "java", "rust", "typescript", "react", "javascript"}


def _line(text: str, position: int) -> int:
    """Linea 1-based de una posicion."""
    return text.count("\n", 0, position) + 1


def _comment_spans(text: str, language: str) -> list[tuple[int, int]]:
    """Rangos de comentario del archivo, como (inicio, fin)."""
    spans: list[tuple[int, int]] = []
    if language in HASH_LANGUAGES:
        spans += [(m.start(), m.end()) for m in HASH_COMMENT.finditer(text)]
    if language in SLASH_LANGUAGES:
        spans += [(m.start(), m.end()) for m in SLASH_COMMENT.finditer(text)]
        spans += [(m.start(), m.end()) for m in BLOCK_COMMENT.finditer(text)]
    return spans


def violations(units: list[Unit], language: str) -> list[quality.Violation]:
    """Claves de ticket dentro de comentarios."""
    out: list[quality.Violation] = []
    for unit in units:
        for start, end in _comment_spans(unit.text, language):
            comment = unit.text[start:end]
            for key in TICKET_KEY.finditer(comment):
                out.append(
                    quality.Violation(
                        unit.relative,
                        _line(unit.text, start + key.start()),
                        1,
                        "calidad",
                        "clave-en-comentario",
                        "la clave de seguimiento no va en el codigo; el comentario explica el motivo",
                        "tickets",
                        False,
                    )
                )
    return quality.dedupe(out)


def analyze(units: list[Unit], language: str) -> list[quality.Violation]:
    """Punto de entrada portable."""
    return violations(units, language)
