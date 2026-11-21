"""Calidad de tests portable para Python, Go, Rust y TypeScript."""

from __future__ import annotations

import re
from pathlib import Path

from lintlib import quality

SKIP = {
    "node_modules",
    ".git",
    "dist",
    "build",
    "target",
    "vendor",
    ".venv",
    "venv",
    "__pycache__",
    "coverage",
}

TEST_PATTERNS = {
    "python": re.compile(r"^\s*(?:async\s+)?def test_", re.MULTILINE),
    "go": re.compile(r"^func (?:Test|Benchmark|Example)", re.MULTILINE),
    "rust": re.compile(r"#\[(?:[\w:]+::)?test\]"),
    "typescript": re.compile(r"\b(?:it|test)\s*\("),
}

ASSERTIONS = {
    "python": re.compile(r"\bassert\b|pytest\.raises|assert_that"),
    "go": re.compile(r"t\.(?:Error|Fatal|Fail|Errorf|Fatalf)|(?:assert|require)\."),
    "rust": re.compile(r"assert!|assert_eq!|assert_ne!|expect\(|unwrap\("),
    "typescript": re.compile(r"expect\(|assert\(|toThrow|toBe|toEqual"),
}


def _skip(relative: str) -> bool:
    """True si la ruta es generada o de dependencias."""
    return bool(set(Path(relative).parts) & SKIP)


def _is_test(language: str, path: Path) -> bool:
    """True si el archivo es un test del lenguaje."""
    name = path.name
    if language == "python":
        return name.startswith("test_") or name.endswith("_test.py")
    if language == "go":
        return name.endswith("_test.go")
    if language == "rust":
        return name.endswith(".rs") and (
            "tests" in path.parts or "#[test]" in path.read_text(encoding="utf-8", errors="replace")
        )
    if language == "typescript":
        return name.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx"))
    return False


def _files(root: Path, language: str) -> list[Path]:
    """Archivos de test del lenguaje."""
    found: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or _skip(path.relative_to(root).as_posix()):
            continue
        if _is_test(language, path):
            found.append(path)
    return sorted(found)


def _violation(relative: str, rule: str, message: str) -> quality.Violation:
    """Violacion de tests relativa a la raiz del proyecto."""
    return quality.Violation(relative, 1, 1, "tests", rule, message, "test-quality", False)


def _file_violations(path: Path, root: Path, language: str) -> list[quality.Violation]:
    """Tamano, cantidad y aserciones de un archivo de test."""
    relative = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8", errors="replace")
    out: list[quality.Violation] = []
    lines = text.count("\n") + 1
    if lines > 400:
        out.append(_violation(relative, "test-largo", f"test de {lines} lineas; divide por caso"))
    tests = len(TEST_PATTERNS[language].findall(text))
    if tests > 15:
        out.append(
            _violation(
                relative,
                "test-gigante",
                f"test con {tests} casos; divide por responsabilidad",
            )
        )
    if tests and not ASSERTIONS[language].search(text):
        out.append(_violation(relative, "test-sin-assert", "test sin aserciones"))
    return out


def analyze(root: Path, language: str) -> list[quality.Violation]:
    """Analiza la calidad de los tests de un proyecto externo."""
    if language not in TEST_PATTERNS:
        return []
    files = _files(root, language)
    if not files:
        return [_violation("tests", "sin-tests", "no encontre tests")]
    out: list[quality.Violation] = []
    for path in files:
        out.extend(_file_violations(path, root, language))
    return quality.dedupe(out)
