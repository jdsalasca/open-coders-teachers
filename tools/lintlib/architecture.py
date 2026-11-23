"""Reglas de capas portables para Python, Go, Rust y TypeScript."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from lintlib import quality, solid

LAYERS = (
    "domain",
    "application",
    "infrastructure",
    "web",
    "api",
    "adapters",
    "repo",
    "services",
    "model",
    "view",
    "controller",
    "viewmodel",
    "pages",
    "components",
    "lib",
    "hooks",
)

FORBIDDEN = {
    "domain": {
        "application",
        "infrastructure",
        "web",
        "api",
        "adapters",
        "repo",
        "services",
    },
    "application": {"infrastructure", "web", "api", "adapters", "repo"},
    "services": {"infrastructure", "web", "api", "adapters", "repo"},
    "web": {"infrastructure", "adapters", "repo"},
    "api": {"infrastructure", "adapters", "repo"},
    "model": {"view", "controller", "viewmodel", "pages", "components", "hooks"},
    "view": {"controller"},
    "viewmodel": {"view"},
    "lib": {"pages", "components"},
    "components": {"pages"},
}

COMPOSITION = {"main.py", "main.go", "main.rs", "main.ts", "main.tsx", "App.tsx"}

ALIASES = {
    "repositories": "repo",
    "repository": "repo",
    "persistence": "repo",
    "repos": "repo",
    "infra": "infrastructure",
    "handlers": "web",
    "controllers": "controller",
    "views": "view",
    "models": "model",
}

FRAMEWORKS = {
    "python": ("sqlalchemy", "django", "fastapi", "flask", "pydantic", "starlette"),
    "go": (
        "gorm.io",
        "github.com/gin-gonic",
        "github.com/labstack",
        "github.com/go-chi",
        "github.com/gorilla",
        "database/sql",
    ),
    "rust": (
        "serde",
        "serde_json",
        "axum",
        "actix",
        "tokio",
        "sqlx",
        "diesel",
        "rocket",
        "warp",
    ),
}

IMPORT_PY = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.MULTILINE)
IMPORT_GO = re.compile(r"import\s*\((.*?)\)", re.DOTALL)
IMPORT_GO_ONE = re.compile(r'import\s+"([^"]+)"')
IMPORT_RUST = re.compile(r"^\s*use\s+([\w:]+)", re.MULTILINE)
IMPORT_TS = re.compile(r"from\s+[\"']([^\"']+)[\"']")

SKIP_PARTS = {
    "node_modules",
    ".git",
    "dist",
    "build",
    "target",
    "vendor",
    ".venv",
    "venv",
    "tests",
    "__pycache__",
    "coverage",
}


@dataclass(frozen=True)
class Source:
    """Fuente con su capa y sus imports locales."""

    relative: str
    layer: str
    imports: tuple[tuple[str, int], ...]
    dto: bool


def _line(text: str, position: int) -> int:
    """Linea 1-based de una posicion."""
    return text.count("\n", 0, position) + 1


def _kind(value: str) -> str:
    """Capa por segmentos de paquete, modulo o ruta."""
    parts = re.split(r"[.:/\\]", value)
    for layer in LAYERS:
        if layer in parts:
            return layer
    for alias, layer in ALIASES.items():
        if alias in parts:
            return layer
    if "app" in parts:
        return "application"
    return "other"


def _is_dto(relative: str) -> bool:
    """True si la ruta pertenece a DTOs o esquemas."""
    parts = set(Path(relative).parts)
    return bool(parts & {"dto", "dtos", "schemas", "serializers"})


def _skip(relative: str) -> bool:
    """True si la ruta es generada, de test o de dependencias."""
    parts = set(Path(relative).parts)
    name = Path(relative).name
    return (
        bool(parts & SKIP_PARTS)
        or name.startswith("test_")
        or name.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx", "_test.go", ".d.ts"))
    )


def _violation(source: Source, line: int, rule: str, message: str) -> quality.Violation:
    """Violacion de arquitectura relativa a la raiz del proyecto."""
    return quality.Violation(
        source.relative, line, 1, "capas", rule, message, "architecture", False
    )


def _layer_violations(source: Source, frameworks: tuple[str, ...]) -> list[quality.Violation]:
    """Direccion de capas, frameworks en dominio y DTOs acoplados."""
    if Path(source.relative).name in COMPOSITION:
        return []
    out: list[quality.Violation] = []
    for imported, line in source.imports:
        target = _kind(imported)
        message = ""
        if source.layer == "domain" and imported.startswith(frameworks):
            message = f"el dominio importa {imported}; el dominio no conoce frameworks"
            out.append(_violation(source, line, "dominio-framework", message))
        if target in FORBIDDEN.get(source.layer, set()):
            message = f"{source.layer} importa {imported}; depende hacia {target}"
            out.append(_violation(source, line, "capa-dependencia", message))
        if source.dto and target == "domain":
            message = f"DTO importa {imported}; no expongas el dominio"
            out.append(_violation(source, line, "dto-dominio", message))
    return out


def python_sources(root: Path) -> list[Source]:
    """Fuentes Python de produccion."""
    out: list[Source] = []
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        if _skip(relative):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        imports = tuple(
            (match.group(1) or match.group(2), _line(text, match.start()))
            for match in IMPORT_PY.finditer(text)
        )
        out.append(Source(relative, _kind(relative), imports, _is_dto(relative)))
    return out


def go_sources(root: Path) -> list[Source]:
    """Fuentes Go de produccion."""
    out: list[Source] = []
    for path in sorted(root.rglob("*.go")):
        relative = path.relative_to(root).as_posix()
        if _skip(relative):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        imports: list[tuple[str, int]] = []
        for block in IMPORT_GO.finditer(text):
            imports.extend(
                (item.group(1), _line(text, block.start(1) + item.start()))
                for item in re.finditer(r'"([^"]+)"', block.group(1))
            )
        imports.extend(
            (item.group(1), _line(text, item.start())) for item in IMPORT_GO_ONE.finditer(text)
        )
        out.append(Source(relative, _kind(relative), tuple(imports), _is_dto(relative)))
    return out


def rust_sources(root: Path) -> list[Source]:
    """Fuentes Rust de produccion."""
    out: list[Source] = []
    for path in sorted(root.rglob("*.rs")):
        relative = path.relative_to(root).as_posix()
        if _skip(relative) or relative.startswith("tests/"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        imports = tuple(
            (match.group(1), _line(text, match.start())) for match in IMPORT_RUST.finditer(text)
        )
        out.append(Source(relative, _kind(relative), imports, _is_dto(relative)))
    return out


def ts_sources(root: Path) -> list[Source]:
    """Fuentes TypeScript/React de produccion."""
    out: list[Source] = []
    for path in sorted(root.rglob("*")):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        relative = path.relative_to(root).as_posix()
        if _skip(relative) or relative.endswith((".config.ts", ".config.tsx")):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        imports = tuple(
            (match.group(1), _line(text, match.start()))
            for match in IMPORT_TS.finditer(text)
            if match.group(1).startswith((".", "/"))
        )
        out.append(Source(relative, _kind(relative), imports, _is_dto(relative)))
    return out


def analyze(root: Path, language: str) -> list[quality.Violation]:
    """Analiza capas de un proyecto externo segun su lenguaje."""
    builders = {
        "python": python_sources,
        "go": go_sources,
        "rust": rust_sources,
        "typescript": ts_sources,
    }
    builder = builders.get(language)
    if builder is None:
        return []
    frameworks = FRAMEWORKS.get(language, ())
    out: list[quality.Violation] = []
    units: list[solid.Unit] = []
    for source in builder(root):
        out.extend(_layer_violations(source, frameworks))
        path = root / source.relative
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            text = ""
        units.append(solid.Unit(source.relative, text, source.imports))
    out.extend(solid.analyze(units, language))
    return quality.dedupe(out)
