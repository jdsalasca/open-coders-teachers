"""Reglas de SOLID y clean code portables para los seis lenguajes.

Complementa ``architecture`` (direccion de capas) y ``abstractions`` (puertos y
DIP) con cinco reglas que ninguna herramienta del set cubre de forma portable:

- ``todo-pendiente``      TODO/FIXME/XXX/HACK que entra al codigo
- ``lsp-no-implementado`` implementacion que rompe el contrato de su interfaz
- ``srp-dependencias``    constructor con demasiadas dependencias inyectadas
- ``dominio-util``        el dominio importa utilidades transversales
- ``capa-ciclo``          dos paquetes que se importan mutuamente

Todas nacen como ``accionable`` salvo ``capa-ciclo``, que es ``capas``: un ciclo
no es estilo, es arquitectura rota.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from lintlib import quality

TODO_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")

# Una implementacion que lanza esto esta diciendo que no cumple su contrato.
LSP_PATTERNS: dict[str, re.Pattern[str]] = {
    "java": re.compile(r"throw\s+new\s+UnsupportedOperationException"),
    "go": re.compile(r"panic\(\s*\"(?:not implemented|TODO|unimplemented)", re.IGNORECASE),
    "python": re.compile(r"raise\s+NotImplementedError"),
    "typescript": re.compile(r"throw\s+new\s+Error\(\s*['\"](?:not implemented|todo)", re.IGNORECASE),
    "rust": re.compile(r"\b(?:unimplemented|todo)!\("),
}

# Tipos que representan una dependencia externa inyectada, no un dato.
DEPENDENCY = re.compile(
    r"\b(\w*(?:Service|Repository|Repo|Client|Port|Adapter|Gateway|Publisher|Producer|Cache|Store|Dao))\b"
)

UTIL_PACKAGES = {"util", "utils", "helpers", "helper", "common", "commons", "shared"}

# Raices de biblioteca estandar: no son utilidades del proyecto.
STDLIB_ROOTS = {
    "java": {"java", "javax", "jakarta", "jdk", "sun"},
    "go": {
        "context", "fmt", "os", "io", "time", "errors", "strings", "strconv", "sync",
        "net", "encoding", "sort", "math", "bytes", "bufio", "log", "regexp",
        "testing", "reflect", "path", "crypto", "database", "embed", "flag", "hash",
        "html", "index", "mime", "plugin", "runtime", "text", "unicode", "unsafe",
        "cmp", "slices", "maps", "container", "archive", "compress", "image", "debug",
    },
    "python": {
        "os", "sys", "re", "json", "typing", "datetime", "pathlib", "collections",
        "itertools", "functools", "dataclasses", "enum", "abc", "math", "time",
        "uuid", "logging", "subprocess", "shutil", "tempfile", "unittest", "pytest",
        "contextlib", "io", "csv", "hashlib", "random", "threading", "asyncio",
    },
    "typescript": {"node", "react", "react-dom", "next", "vitest", "jest"},
    "rust": {"std", "core", "alloc"},
}

MAX_DEPENDENCIES = 4


@dataclass(frozen=True)
class Unit:
    """Fuente ya leida, con su ruta relativa y sus imports locales."""

    relative: str
    text: str
    imports: tuple[tuple[str, int], ...]


def _line(text: str, position: int) -> int:
    """Linea 1-based de una posicion."""
    return text.count("\n", 0, position) + 1


def _violation(
    relative: str, line: int, category: str, rule: str, message: str
) -> quality.Violation:
    return quality.Violation(relative, line, 1, category, rule, message, "solid", False)


def _is_domain(relative: str) -> bool:
    """True si la ruta pertenece a la capa de dominio."""
    return "domain" in Path(relative).parts


def _node_of_path(relative: str) -> str:
    """Nombre del paquete de un archivo: su ultimo directorio."""
    parts = Path(relative.replace("\\", "/")).parts
    return parts[-2] if len(parts) >= 2 else "."


def _node_of_import(imported: str, language: str) -> str:
    """Nombre del paquete destino de un import."""
    raw = imported.replace("\\", "/")
    parts = [part for part in (raw.split("/") if "/" in raw else raw.split(".")) if part]
    if not parts:
        return ""
    if language == "java":
        # El ultimo segmento es la clase; el paquete es el anterior.
        return parts[-2] if len(parts) >= 2 else ""
    return parts[-1]


# ------------------------------------------------------------------ reglas


def todo_violations(units: list[Unit]) -> list[quality.Violation]:
    """TODO/FIXME/XXX/HACK en el codigo bajo analisis."""
    out: list[quality.Violation] = []
    for unit in units:
        for match in TODO_RE.finditer(unit.text):
            line = _line(unit.text, match.start())
            message = f"marca {match.group(1)} pendiente; resuelvela o registrala fuera del codigo"
            out.append(_violation(unit.relative, line, "calidad", "todo-pendiente", message))
    return out


def _is_abstract_scope(text: str, position: int) -> bool:
    """True si la posicion cae en una clase abstracta o interfaz.

    En una base abstracta, ``UnsupportedOperationException`` puede ser legitimo:
    el contrato aun no tiene implementacion.
    """
    head = text[:position]
    starts = [head.rfind(key) for key in ("abstract class ", "interface ")]
    last = max(starts)
    if last < 0:
        return False
    # Si la declaracion abstracta ya cerro, no aplica.
    return head.count("{", last) > head.count("}", last)


def lsp_violations(units: list[Unit], language: str) -> list[quality.Violation]:
    """Metodos que lanzan 'no implementado' fuera de una base abstracta."""
    pattern = LSP_PATTERNS.get(language)
    if pattern is None:
        return []
    out: list[quality.Violation] = []
    for unit in units:
        for match in pattern.finditer(unit.text):
            if _is_abstract_scope(unit.text, match.start()):
                continue
            line = _line(unit.text, match.start())
            message = "la implementacion no cumple el contrato; resuelvelo o separa la interfaz"
            out.append(_violation(unit.relative, line, "calidad", "lsp-no-implementado", message))
    return out


def _count_dependencies(parameters: str) -> list[str]:
    """Dependencias inyectadas dentro de una lista de parametros."""
    found: list[str] = []
    for part in parameters.split(","):
        name = DEPENDENCY.search(part)
        if name:
            found.append(name.group(1))
    return found


def _params_java(text: str) -> list[tuple[str, int]]:
    """Parametros de constructores Java con su linea."""
    out: list[tuple[str, int]] = []
    for match in re.finditer(r"public\s+[A-Z]\w*\s*\(([^)]*)\)", text):
        out.append((match.group(1), _line(text, match.start())))
    return out


def _params_go(text: str) -> list[tuple[str, int]]:
    """Parametros de constructores Go (func New...)."""
    out: list[tuple[str, int]] = []
    for match in re.finditer(r"func\s+New\w*\(([^)]*)\)", text):
        out.append((match.group(1), _line(text, match.start())))
    return out


def _params_python(text: str) -> list[tuple[str, int]]:
    """Parametros de __init__ en Python, con sus anotaciones."""
    out: list[tuple[str, int]] = []
    for match in re.finditer(r"def\s+__init__\s*\((.*?)\)\s*(?:->[^:]+)?:", text, re.DOTALL):
        out.append((match.group(1), _line(text, match.start())))
    return out


def _params_typescript(text: str) -> list[tuple[str, int]]:
    """Parametros de constructor en TypeScript."""
    out: list[tuple[str, int]] = []
    for match in re.finditer(r"constructor\s*\(([^)]*)\)", text):
        out.append((match.group(1), _line(text, match.start())))
    return out


PARAM_BUILDERS = {
    "java": _params_java,
    "go": _params_go,
    "python": _params_python,
    "typescript": _params_typescript,
}


def srp_violations(units: list[Unit], language: str) -> list[quality.Violation]:
    """Constructor con demasiadas dependencias inyectadas."""
    builder = PARAM_BUILDERS.get(language)
    if builder is None:
        return []
    out: list[quality.Violation] = []
    for unit in units:
        for parameters, line in builder(unit.text):
            dependencies = _count_dependencies(parameters)
            if len(dependencies) <= MAX_DEPENDENCIES:
                continue
            names = ", ".join(dependencies[:3])
            message = (
                f"{len(dependencies)} dependencias inyectadas ({names}...); "
                "la clase probablemente tenga mas de una responsabilidad"
            )
            out.append(_violation(unit.relative, line, "srp", "srp-dependencias", message))
    return out


def util_violations(units: list[Unit], language: str) -> list[quality.Violation]:
    """El dominio importa utilidades transversales del proyecto."""
    stdlib = STDLIB_ROOTS.get(language, set())
    out: list[quality.Violation] = []
    for unit in units:
        if not _is_domain(unit.relative):
            continue
        for imported, line in unit.imports:
            parts = [part for part in re.split(r"[.:/\\]", imported) if part]
            if parts and parts[0] in stdlib:
                continue
            hit = set(parts) & UTIL_PACKAGES
            if not hit:
                continue
            message = (
                f"el dominio importa {imported}; las utilidades transversales "
                "arrastran dependencias que el dominio no debe conocer"
            )
            out.append(_violation(unit.relative, line, "capas", "dominio-util", message))
    return out


def cycle_violations(units: list[Unit], language: str) -> list[quality.Violation]:
    """Dos paquetes que se importan mutuamente.

    Detecta el ciclo mutuo (A->B y B->A), que es el caso frecuente y el que
    rompe la direccion de capas sin que ninguna herramienta lo vea.
    """
    stdlib = STDLIB_ROOTS.get(language, set())
    edges: dict[str, set[str]] = {}
    origin: dict[str, tuple[str, int]] = {}
    for unit in units:
        source = _node_of_path(unit.relative)
        for imported, line in unit.imports:
            parts = [part for part in re.split(r"[.:/\\]", imported) if part]
            if parts and parts[0] in stdlib:
                continue
            target = _node_of_import(imported, language)
            if not target or target == source:
                continue
            edges.setdefault(source, set()).add(target)
            origin.setdefault(f"{source}->{target}", (unit.relative, line))

    out: list[quality.Violation] = []
    seen: set[tuple[str, str]] = set()
    for source, targets in edges.items():
        for target in targets:
            if source not in edges.get(target, set()):
                continue
            pair = tuple(sorted((source, target)))
            if pair in seen:
                continue
            seen.add(pair)
            relative, line = origin.get(f"{source}->{target}", (".", 1))
            message = (
                f"{source} y {target} se importan mutuamente; rompe el ciclo "
                "con una interfaz en la capa de menor nivel"
            )
            out.append(_violation(relative, line, "capas", "capa-ciclo", message))
    return out


def analyze(units: list[Unit], language: str) -> list[quality.Violation]:
    """Aplica todas las reglas de SOLID y clean code."""
    out: list[quality.Violation] = []
    out.extend(todo_violations(units))
    out.extend(lsp_violations(units, language))
    out.extend(srp_violations(units, language))
    out.extend(util_violations(units, language))
    out.extend(cycle_violations(units, language))
    return quality.dedupe(out)
