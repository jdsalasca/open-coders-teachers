"""Documentacion JSDoc para exports TypeScript/React externos."""

from __future__ import annotations

import re
from pathlib import Path

from lintlib import quality

SKIP = {
    "node_modules",
    ".git",
    "dist",
    "build",
    "coverage",
    "target",
    ".venv",
    "venv",
}

EXPORT_FUNCTION = re.compile(
    r"^\s*export\s+(?:default\s+)?(?:async\s+)?function\s+(\w+)", re.MULTILINE
)
EXPORT_CLASS = re.compile(r"^\s*export\s+(?:default\s+)?class\s+(\w+)", re.MULTILINE)
EXPORT_CONST = re.compile(
    r"^\s*export\s+const\s+(\w+)\s*=\s*(?:async\s*)?(?:\(|function)", re.MULTILINE
)


def _skip(relative: str) -> bool:
    """True si la ruta es generada, test o de dependencias."""
    name = Path(relative).name
    return (
        bool(set(Path(relative).parts) & SKIP)
        or name.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx", ".d.ts"))
        or name.endswith((".config.ts", ".config.tsx"))
    )


def _line(text: str, position: int) -> int:
    """Linea 1-based de una posicion."""
    return text.count("\n", 0, position) + 1


def _has_jsdoc(lines: list[str], line: int) -> bool:
    """True si la declaracion tiene un bloque JSDoc inmediato."""
    start = max(0, line - 8)
    return any("/**" in item for item in lines[start : line - 1])


def _file_violations(path: Path, root: Path) -> list[quality.Violation]:
    """Exports publicos sin JSDoc."""
    relative = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    out: list[quality.Violation] = []
    patterns = (EXPORT_FUNCTION, EXPORT_CLASS, EXPORT_CONST)
    for pattern in patterns:
        for match in pattern.finditer(text):
            line = _line(text, match.start())
            if _has_jsdoc(lines, line):
                continue
            name = match.group(1)
            message = f"export {name} sin JSDoc; documenta su contrato"
            out.append(
                quality.Violation(
                    relative,
                    line,
                    1,
                    "calidad",
                    "jsdoc-export",
                    message,
                    "ts-quality",
                    False,
                )
            )
    return out


def analyze(root: Path) -> list[quality.Violation]:
    """Analiza exports TypeScript/React sin documentacion."""
    out: list[quality.Violation] = []
    for path in sorted(root.rglob("*")):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        relative = path.relative_to(root).as_posix()
        if _skip(relative):
            continue
        out.extend(_file_violations(path, root))
    return quality.dedupe(out)
