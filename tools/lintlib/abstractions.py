"""Puertos orientados a operaciones e inversion de dependencias."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from lintlib import quality

PORT_SUFFIXES = (
    "Port",
    "UseCase",
    "Gateway",
    "Repository",
    "Provider",
    "Service",
    "Controller",
    "View",
    "ViewModel",
    "Presenter",
    "Handler",
)

OPERATIONS = (
    "create",
    "list",
    "find",
    "get",
    "save",
    "delete",
    "remove",
    "update",
    "add",
    "exists",
    "count",
    "complete",
    "approve",
    "register",
    "search",
    "load",
    "store",
    "publish",
    "send",
    "fetch",
    "handle",
    "execute",
    "process",
    "validate",
    "sync",
    "import",
    "export",
    "calculate",
    "apply",
    "mark",
    "rename",
    "start",
    "stop",
    "run",
    "read",
    "write",
    "open",
    "close",
    "build",
    "parse",
    "render",
    "increment",
    "decrement",
    "reset",
    "cancel",
    "confirm",
    "reject",
    "assign",
    "schedule",
    "notify",
    "pay",
    "verify",
    "upload",
    "download",
    "transform",
    "convert",
    "map",
    "filter",
    "sort",
    "aggregate",
    "summarize",
    "generate",
    "evaluate",
    "check",
    "ensure",
    "require",
    "resolve",
    "connect",
    "disconnect",
    "clear",
    "flush",
    "commit",
    "rollback",
    "begin",
    "end",
    "on",
    "is",
    "has",
    "can",
    "should",
    "to",
    "from",
    "equals",
    "hash",
)

IGNORED_METHODS = {"tostring", "equals", "hashcode", "__init__"}

PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.MULTILINE)
JAVA_TYPE = re.compile(r"^\s*(?:public\s+)?(interface|class|enum|record)\s+(\w+)", re.MULTILINE)
JAVA_FIELD = re.compile(r"^\s*private\s+(?:final\s+)?([A-Z]\w*)\s+(\w+)\s*;", re.MULTILINE)
TS_EXPORT_CLASS = re.compile(
    r"^\s*export\s+(?:default\s+)?(?:abstract\s+)?class\s+(\w+)", re.MULTILINE
)
TS_EXPORT_INTERFACE = re.compile(r"^\s*export\s+interface\s+(\w+)", re.MULTILINE)
TS_IMPORT = re.compile(
    r"import\s+(?:type\s+)?\{([^}]+)\}\s+from\s+[\"']([^\"']+)[\"']", re.MULTILINE
)

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


@dataclass(frozen=True)
class Port:
    """Abstraccion con sus metodos y ubicacion."""

    relative: str
    name: str
    methods: tuple[str, ...]
    line: int
    framework: bool = False


def _line(text: str, position: int) -> int:
    """Linea 1-based de una posicion."""
    return text.count("\n", 0, position) + 1


def _skip(relative: str) -> bool:
    """True si la ruta es generada, de test o de dependencias."""
    name = Path(relative).name
    return (
        bool(set(Path(relative).parts) & SKIP)
        or name.startswith("test_")
        or name.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx", "_test.go", ".d.ts"))
    )


def _suffix(name: str) -> bool:
    """True si el nombre declara un puerto o abstraccion operacional."""
    return name.endswith(PORT_SUFFIXES)


def _body(text: str, start: int) -> str:
    """Contenido entre la primera llave y su cierre."""
    opening = text.find("{", start)
    if opening < 0:
        return ""
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[opening + 1 : index]
    return text[opening + 1 :]


def _python_ports(root: Path) -> list[Port]:
    """Protocols y ABCs con nombre de puerto."""
    out: list[Port] = []
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        if _skip(relative):
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for index, line in enumerate(lines):
            match = re.match(r"^(\s*)class\s+(\w+)\s*\(([^)]*)\)", line)
            if not match or not re.search(r"\b(Protocol|ABC)\b", match.group(3)):
                continue
            name = match.group(2)
            if not _suffix(name):
                continue
            indent = len(match.group(1))
            body: list[str] = []
            for item in lines[index + 1 :]:
                if item.strip() and len(item) - len(item.lstrip()) <= indent:
                    break
                body.append(item)
            methods = tuple(
                method
                for method in re.findall(r"^\s+(?:async\s+)?def\s+(\w+)", "\n".join(body), re.M)
                if method not in {"__init__"}
            )
            out.append(Port(relative, name, methods, index + 1))
    return out


def _java_ports(root: Path) -> list[Port]:
    """Interfaces y clases abstractas Java con nombre de puerto."""
    out: list[Port] = []
    for path in sorted(root.rglob("*.java")):
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(
            r"^\s*(?:public\s+)?(interface|abstract\s+class)\s+(\w+)", text, re.M
        ):
            name = match.group(2)
            if not _suffix(name):
                continue
            body = _body(text, match.end())
            methods = tuple(
                method
                for method in re.findall(
                    r"^\s*(?:public\s+)?(?:abstract\s+)?[\w<>\[\], ?]+\s+(\w+)\s*\(",
                    body,
                    re.M,
                )
                if method != name
            )
            declaration = text[match.start() : text.find("{", match.end())]
            framework = bool(
                re.search(
                    r"extends\s+(?:JpaRepository|CrudRepository|Repository)\b",
                    declaration,
                )
            )
            out.append(Port(relative, name, methods, _line(text, match.start()), framework))
    return out


def _go_ports(root: Path) -> list[Port]:
    """Interfaces Go con nombre de puerto."""
    out: list[Port] = []
    for path in sorted(root.rglob("*.go")):
        relative = path.relative_to(root).as_posix()
        if _skip(relative):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r"^\s*type\s+(\w+)\s+interface\s*\{", text, re.M):
            name = match.group(1)
            if not _suffix(name):
                continue
            body = _body(text, match.end() - 1)
            methods = tuple(re.findall(r"^\s*(\w+)\s*\(", body, re.M))
            out.append(Port(relative, name, methods, _line(text, match.start())))
    return out


def _rust_ports(root: Path) -> list[Port]:
    """Traits Rust con nombre de puerto."""
    out: list[Port] = []
    for path in sorted(root.rglob("*.rs")):
        relative = path.relative_to(root).as_posix()
        if _skip(relative):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r"^\s*pub\s+trait\s+(\w+)", text, re.M):
            name = match.group(1)
            if not _suffix(name):
                continue
            body = _body(text, match.end())
            methods = tuple(re.findall(r"^\s*fn\s+(\w+)", body, re.M))
            out.append(Port(relative, name, methods, _line(text, match.start())))
    return out


def _ts_ports(root: Path) -> list[Port]:
    """Interfaces TypeScript con nombre de puerto."""
    out: list[Port] = []
    for path in sorted(root.rglob("*")):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        relative = path.relative_to(root).as_posix()
        if _skip(relative):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r"^\s*export\s+interface\s+(\w+)", text, re.M):
            name = match.group(1)
            if not _suffix(name):
                continue
            body = _body(text, match.end())
            methods = tuple(name for name in re.findall(r"^\s*(\w+)\s*(?:\(|:\s*\()", body, re.M))
            out.append(Port(relative, name, methods, _line(text, match.start())))
    return out


def _port_violations(port: Port) -> list[quality.Violation]:
    """Tamano, framework y nombres de operacion de un puerto."""
    out: list[quality.Violation] = []

    def add(rule: str, message: str, category: str = "srp") -> None:
        out.append(
            quality.Violation(
                port.relative,
                port.line,
                1,
                category,
                rule,
                message,
                "abstractions",
                False,
            )
        )

    if port.framework:
        add(
            "abstraccion-framework",
            f"{port.name} extiende un repositorio de framework; define un puerto propio",
            "capas",
        )
    _shape_violations(port, add)
    for method in port.methods:
        name = method.lower()
        if name in IGNORED_METHODS:
            continue
        if not any(name.startswith(prefix) for prefix in OPERATIONS):
            add(
                "metodo-no-operacional",
                f"{port.name}.{method} no parece una operacion; usa un verbo",
                "calidad",
            )
    return out


def _shape_violations(port: Port, add: Callable[[str, str, str], None]) -> None:
    """Cantidad de operaciones del puerto."""
    if not port.methods:
        if not port.framework:
            add("abstraccion-vacia", f"{port.name} no declara operaciones", "srp")
    elif len(port.methods) > 4:
        add(
            "abstraccion-grande",
            f"{port.name} tiene {len(port.methods)} operaciones; divide por caso de uso",
            "srp",
        )


def _package_kind(package: str) -> str:
    """Capa por segmentos del paquete Java."""
    parts = package.split(".")
    for kind in (
        "domain",
        "application",
        "service",
        "infrastructure",
        "web",
        "repo",
        "adapters",
    ):
        if kind in parts:
            return "application" if kind == "service" else kind
    return "other"


def _java_types(root: Path) -> dict[str, tuple[str, str]]:
    """Tipo Java -> (kind, capa del paquete)."""
    out: dict[str, tuple[str, str]] = {}
    for path in sorted(root.rglob("*.java")):
        relative = path.relative_to(root).as_posix()
        if _skip(relative):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        package = PACKAGE_RE.search(text)
        kind = _package_kind(package.group(1) if package else "")
        for match in JAVA_TYPE.finditer(text):
            out[match.group(2)] = (match.group(1), kind)
    return out


def _java_dependencies(text: str) -> list[tuple[str, int]]:
    """Campos y parametros de constructor de un servicio Java."""
    dependencies: list[tuple[str, int]] = [
        (match.group(1), _line(text, match.start())) for match in JAVA_FIELD.finditer(text)
    ]
    for constructor in re.finditer(r"public\s+\w+\s*\(([^)]*)\)", text, re.DOTALL):
        start = _line(text, constructor.start(1))
        for item in constructor.group(1).split(","):
            match = re.match(r"([A-Z]\w*)\s+\w+", item.strip())
            if match:
                dependencies.append((match.group(1), start))
    return dependencies


def _java_dip_for(
    relative: str,
    dependencies: list[tuple[str, int]],
    types: dict[str, tuple[str, str]],
) -> list[quality.Violation]:
    """DIP de un servicio Java."""
    out: list[quality.Violation] = []
    seen: set[tuple[str, str]] = set()
    for type_name, line in dependencies:
        kind, layer = types.get(type_name, ("class", "other"))
        if kind == "class" and layer in {"repo", "infrastructure", "adapters", "web"}:
            key = ("dip-concreta", type_name)
            if key not in seen:
                seen.add(key)
                message = f"depende de {type_name} (clase concreta); usa un puerto"
                out.append(
                    quality.Violation(
                        relative,
                        line,
                        1,
                        "capas",
                        "dip-concreta",
                        message,
                        "abstractions",
                        False,
                    )
                )
        if kind == "interface" and type_name.endswith("Repository"):
            key = ("dip-framework", type_name)
            if key not in seen:
                seen.add(key)
                message = f"depende de {type_name} (repositorio de framework); usa un puerto"
                out.append(
                    quality.Violation(
                        relative,
                        line,
                        1,
                        "capas",
                        "dip-framework",
                        message,
                        "abstractions",
                        False,
                    )
                )
    return out


def _java_dip(root: Path) -> list[quality.Violation]:
    """Servicios Java que dependen de clases concretas o repos de framework."""
    types = _java_types(root)
    out: list[quality.Violation] = []
    for path in sorted(root.rglob("*.java")):
        relative = path.relative_to(root).as_posix()
        if _skip(relative):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        package = PACKAGE_RE.search(text)
        if _package_kind(package.group(1) if package else "") != "application":
            continue
        out.extend(_java_dip_for(relative, _java_dependencies(text), types))
    return out


def _ts_exports(root: Path) -> dict[str, dict[str, str]]:
    """Archivo TypeScript -> export -> clase/interfaz."""
    out: dict[str, dict[str, str]] = {}
    for path in sorted(root.rglob("*")):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        relative = path.relative_to(root).as_posix()
        if _skip(relative):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        symbols = dict.fromkeys(TS_EXPORT_INTERFACE.findall(text), "interface")
        symbols.update(dict.fromkeys(TS_EXPORT_CLASS.findall(text), "class"))
        out[relative] = symbols
    return out


def _ts_target(path: Path, spec: str) -> Path | None:
    """Archivo TypeScript al que apunta un import relativo."""
    if not spec.startswith("."):
        return None
    target = (path.parent / spec).resolve()
    candidates = [target.with_suffix(".ts"), target.with_suffix(".tsx")]
    candidates.extend([target / "index.ts", target / "index.tsx"])
    return next((item for item in candidates if item.exists()), None)


def _ts_dip_for(
    path: Path, text: str, exports: dict[str, dict[str, str]], root: Path
) -> list[quality.Violation]:
    """Imports de clases concretas en un controlador/viewmodel."""
    relative = path.relative_to(root).as_posix()
    out: list[quality.Violation] = []
    for match in TS_IMPORT.finditer(text):
        names = [
            name.strip().removeprefix("type ").strip()
            for name in match.group(1).split(",")
            if name.strip()
        ]
        target_file = _ts_target(path, match.group(2))
        if target_file is None:
            continue
        relative_target = target_file.relative_to(root).as_posix()
        symbols = exports.get(relative_target, {})
        for name in names:
            if symbols.get(name) != "class":
                continue
            message = f"importa {name} (clase concreta); depende de una abstraccion"
            out.append(
                quality.Violation(
                    relative,
                    _line(text, match.start()),
                    1,
                    "capas",
                    "dip-concreta",
                    message,
                    "abstractions",
                    False,
                )
            )
    return out


def _ts_dip(root: Path) -> list[quality.Violation]:
    """Controladores TypeScript que importan clases concretas."""
    exports = _ts_exports(root)
    out: list[quality.Violation] = []
    for path in sorted(root.rglob("*")):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        relative = path.relative_to(root).as_posix()
        if _skip(relative):
            continue
        if not any(part in {"controller", "viewmodel"} for part in Path(relative).parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        out.extend(_ts_dip_for(path, text, exports, root))
    return out


def analyze(root: Path, language: str, prefix: str = "") -> list[quality.Violation]:
    """Analiza puertos y DIP de un proyecto."""
    parsers = {
        "python": _python_ports,
        "go": _go_ports,
        "rust": _rust_ports,
        "java": _java_ports,
        "typescript": _ts_ports,
        "react": _ts_ports,
    }
    parser = parsers.get(language)
    if parser is None:
        return []
    ports = parser(root)
    out: list[quality.Violation] = []
    for port in ports:
        out.extend(_port_violations(port))
    if language == "java":
        out.extend(_java_dip(root))
    if language in {"typescript", "react"}:
        out.extend(_ts_dip(root))
    if prefix:
        out = [
            quality.Violation(
                f"{prefix}/{violation.path}",
                violation.line,
                violation.column,
                violation.category,
                violation.rule,
                violation.message,
                violation.tool,
                violation.fixable,
            )
            for violation in out
        ]
    return quality.dedupe(out)
