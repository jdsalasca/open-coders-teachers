"""Verifica que los enlaces locales de los .md apunten a algo existente."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
SKIP_SCHEMES = ("http://", "https://", "mailto:", "tel:", "data:")


def slug(heading: str) -> str:
    """Aproxima el ancla que genera GitHub para un titulo."""
    text = heading.strip().lower().lstrip("#").strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"\s+", "-", text)


def anchors(path: Path) -> set[str]:
    """Anclas disponibles en un markdown."""
    found: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("#"):
            found.add(slug(line))
    return found


def markdown_files(targets: list[str]) -> list[Path]:
    """Archivos .md pedidos o todos los del repo."""
    if targets:
        return [Path(t) for t in targets]
    return [
        p
        for p in ROOT.rglob("*.md")
        if "node_modules" not in p.parts and ".opencode" not in p.parts
    ]


def check_file(path: Path) -> list[str]:
    """Devuelve los enlaces rotos de un archivo."""
    problems: list[str] = []
    base = path.parent
    for number, line in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
    ):
        for raw in LINK.findall(line):
            target = unquote(raw)
            if target.startswith(SKIP_SCHEMES):
                continue
            file_part, _, anchor = target.partition("#")
            candidate = (base / file_part).resolve() if file_part else path.resolve()
            if not candidate.exists():
                problems.append(f"{path.as_posix()}:{number}: enlace roto -> {target}")
                continue
            if anchor and candidate.suffix == ".md" and anchor not in anchors(candidate):
                problems.append(f"{path.as_posix()}:{number}: ancla inexistente -> {target}")
    return problems


def main() -> int:
    """Corre la revision sobre los archivos indicados."""
    files = markdown_files(sys.argv[1:])
    problems: list[str] = []
    for path in files:
        if not path.exists():
            problems.append(f"{path.as_posix()}: no existe")
            continue
        problems.extend(check_file(path))
    if problems:
        print("\n".join(problems))
        return 1
    print(f"  {len(files)} archivo(s) sin enlaces rotos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
