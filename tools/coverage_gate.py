"""Falla si un archivo queda por debajo de su minimo de cobertura."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THRESHOLDS = {
    "typescript": 80,
    "react": 80,
    "python": 60,
    "java": 60,
    "rust": 60,
    "go": 50,
}


def parse_cobetura(path: Path) -> dict[str, float]:
    """Line-rate por archivo de un XML de coverage.py."""
    result: dict[str, float] = {}
    for cls in ET.parse(path).getroot().iter("class"):  # noqa: S314 - reporte propio
        filename = cls.attrib.get("filename", "")
        rate = cls.attrib.get("line-rate")
        if filename and rate is not None:
            result[filename] = float(rate) * 100
    return result


def parse_jacoco(path: Path) -> dict[str, float]:
    """Line-rate por clase de un XML de JaCoCo."""
    result: dict[str, float] = {}
    for cls in ET.parse(path).getroot().iter("class"):  # noqa: S314 - reporte propio
        name = cls.attrib.get("name", "")
        counter = cls.find("./counter[@type='LINE']")
        if not name or counter is None:
            continue
        missed = int(counter.attrib.get("missed", "0"))
        covered = int(counter.attrib.get("covered", "0"))
        total = missed + covered
        if total:
            result[f"{name}.java"] = covered * 100 / total
    return result


def parse_lcov(path: Path) -> dict[str, float]:
    """Line-rate por archivo de un LCOV."""
    result: dict[str, float] = {}
    name = ""
    found_lines = 0
    hit_lines = 0
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if raw.startswith("SF:"):
            name = raw[3:]
        elif raw.startswith("LF:"):
            found_lines = int(raw[3:])
        elif raw.startswith("LH:"):
            hit_lines = int(raw[3:])
        elif raw == "end_of_record":
            if name and found_lines:
                result[name] = hit_lines * 100 / found_lines
            name = ""
            found_lines = 0
            hit_lines = 0
    return result


def parse_go(path: Path) -> dict[str, float]:
    """Line-rate por archivo de un coverage.out de Go."""
    blocks: dict[tuple[str, str], tuple[int, bool]] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if raw.startswith("mode:"):
            continue
        parts = raw.rsplit(" ", 2)
        if len(parts) != 3:
            continue
        file_part, statements, count = parts
        name, block = file_part.rsplit(":", 1)
        key = (name, block)
        previous = blocks.get(key, (0, False))
        blocks[key] = (int(statements), previous[1] or int(count) > 0)
    total: dict[str, int] = {}
    covered: dict[str, int] = {}
    for (name, _), (block_statements, hit) in blocks.items():
        total[name] = total.get(name, 0) + block_statements
        if hit:
            covered[name] = covered.get(name, 0) + block_statements
    return {name: covered.get(name, 0) * 100 / count for name, count in total.items() if count}


Parser = Callable[[Path], dict[str, float]]
CHECKS: tuple[tuple[str, Path, Parser], ...] = (
    ("python", ROOT / "python-teacher" / "coverage.xml", parse_cobetura),
    (
        "java",
        ROOT / "Java-teacher" / "target" / "site" / "jacoco" / "jacoco.xml",
        parse_jacoco,
    ),
    ("typescript", ROOT / "typescript-teacher" / "coverage" / "lcov.info", parse_lcov),
    ("react", ROOT / "React-teacher" / "coverage" / "lcov.info", parse_lcov),
    ("rust", ROOT / "Rust-teacher" / "target" / "lcov.info", parse_lcov),
    ("go", ROOT / "go-teacher" / "coverage.out", parse_go),
)


def excluded(language: str, name: str) -> bool:
    """Composition roots y tests no cuentan para el minimo por archivo."""
    normalized = name.replace("\\", "/")
    base = Path(normalized).name
    if language == "python":
        return base in {"main.py", "__init__.py"} or "/tests/" in normalized
    if language == "java":
        return base == "Main.java" or base.endswith("Test.java")
    if language == "go":
        return "/cmd/" in normalized or "/testutil/" in normalized or base.endswith("_test.go")
    if language == "rust":
        return base == "main.rs" or "/tests/" in normalized
    return base in {"main.ts", "main.tsx"} or ".test." in base or ".spec." in base


def main() -> int:
    """Revisa cada reporte y devuelve 1 si algun archivo baja del minimo."""
    status = 0
    for language, path, parser in CHECKS:
        if not path.exists():
            print(f"[X] {language}: falta {path.relative_to(ROOT).as_posix()}")
            status = 2
            continue
        rates = parser(path)
        checked = 0
        for name, rate in sorted(rates.items()):
            if excluded(language, name):
                continue
            checked += 1
            minimum = THRESHOLDS[language]
            if rate < minimum:
                print(f"  [X] {language}: {name} {rate:.1f}% < {minimum}%")
                status = 1
        print(f"  ok: {language} ({checked} archivo(s), minimo {THRESHOLDS[language]}%)")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
