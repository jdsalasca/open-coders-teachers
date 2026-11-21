"""Normaliza la salida de los linters en violaciones por archivo."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from lintlib.common import ROOT, Command

CATEGORIES = (
    "calidad",
    "capas",
    "nombres",
    "acoplamiento",
    "srp",
    "complejidad",
    "imports",
    "formato",
    "tests",
    "cobertura",
)

EXTS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".java",
    ".rs",
    ".scss",
    ".css",
    ".md",
    ".json",
    ".yml",
    ".yaml",
}

ANSI = re.compile(r"\x1b\[[0-9;]*m")

_HINTS = (
    (
        "nombres",
        (
            "naming",
            "varnamelen",
            "predeclared",
            "errname",
            "typename",
            "methodname",
            "localvariablename",
            "membername",
            "parametername",
            "constantname",
            "packagename",
            "staticvariablename",
            "shortvariable",
            "longvariable",
            "shortclassname",
            "shortmethodname",
            "module_name_repetitions",
            "similar_names",
            "non_snake_case",
            "many_single_char_names",
            "wrong_self_convention",
            "struct_field_names",
            "enum_variant_names",
            "upper_case_acronyms",
            "abbreviationaswordinname",
            "dollar-variable-pattern",
            "selector-class-pattern",
        ),
    ),
    (
        "imports",
        (
            "simple-import-sort",
            "import/order",
            "customimportorder",
            "avoidstarimport",
            "unusedimports",
            "importorder",
            "redundantimport",
            "gci",
            "goimports",
            "gofmt",
            "gofumpt",
            "wildcard_imports",
            "unused_imports",
            "import/no-duplicates",
        ),
    ),
    (
        "complejidad",
        (
            "complexity",
            "cyclop",
            "gocognit",
            "gocyclo",
            "nestif",
            "max-depth",
            "max-lines-per-function",
            "max-statements",
            "max-params",
            "funlen",
            "cognitive_complexity",
            "cognitive complexity",
            "too_many_arguments",
            "maximum number of arguments",
            "argument-limit",
            "npathcomplexity",
            "methodlength",
            "excessivemethodlength",
            "excessiveparameterlist",
            "plr0912",
            "plr0913",
            "plr0915",
            "c901",
            "type_complexity",
        ),
    ),
    (
        "srp",
        (
            "max-lines",
            "max-classes-per-file",
            "filelength",
            "classfanoutcomplexity",
            "classdataabstractioncoupling",
            "excessiveclasslength",
            "toomany methods",
            "toomanyfields",
            "excessivepubliccount",
            "godclass",
            "couplingbetweenobjects",
            "plr0904",
            "too_many_lines",
            "struct_excessive_bools",
        ),
    ),
    (
        "capas",
        (
            "depguard",
            "archunit",
            "not-to",
            "no-cycles",
            "modelo-aislado",
            "vista-sin-controlador",
            "capas",
            "layer",
        ),
    ),
    (
        "acoplamiento",
        ("cycle", "ciclo", "coupling", "fan-out", "fanout", "circular", "dependencia"),
    ),
    ("formato", ("prettier", "spotless", "rustfmt", "formatting", "format")),
    (
        "tests",
        (
            "pytest",
            "vitest",
            "go test",
            "cargo test",
            "surefire",
            "test failed",
            "tests run",
        ),
    ),
    ("cobertura", ("coverage", "cov-fail", "llvm-cov", "jacoco", "cobertura")),
)


@dataclass(frozen=True)
class Finding:
    """Hallazgo crudo de una herramienta, antes de categorizar."""

    path: str = ""
    line: int = 1
    column: int = 1
    rule: str = ""
    message: str = ""
    tool: str = ""
    fixable: bool = False
    category: str = ""


@dataclass(frozen=True)
class Violation:
    """Violacion normalizada y lista para el reporte."""

    path: str
    line: int
    column: int
    category: str
    rule: str
    message: str
    tool: str
    fixable: bool


def _text(value: object) -> str:
    """Devuelve texto o cadena vacia si el valor no es string."""
    return value if isinstance(value, str) else ""


def _int(value: object, default: int = 1) -> int:
    """Convierte un valor en entero positivo, o devuelve el default."""
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return max(1, value)
    if isinstance(value, str):
        try:
            return max(1, int(value))
        except ValueError:
            return default
    return default


def _map(value: object) -> dict[str, object]:
    """Devuelve un mapa si el valor lo es; si no, uno vacio."""
    return value if isinstance(value, dict) else {}


def _items(value: object) -> list[object]:
    """Devuelve una lista si el valor lo es; si no, una vacia."""
    return value if isinstance(value, list) else []


def _json(text: str) -> object:
    """Parsea JSON y devuelve None si la salida no lo es."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for line in text.splitlines():
            if not line.startswith(("{", "[")):
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
        return None


def repo_path(raw: str, folder: str) -> str:
    """Convierte una ruta de herramienta en ruta relativa al repo."""
    path = raw.replace("\\", "/").strip()
    path = path.removeprefix("//?/").removeprefix("?/")
    if not path:
        return folder
    marker = f"/{folder}/"
    if marker in path:
        path = path.split(marker, 1)[1]
    elif path.startswith(folder + "/"):
        path = path[len(folder) + 1 :]
    path = path.lstrip("./")
    if not folder:
        return path
    return f"{folder}/{path}" if path else folder


def _ruff_category(rule: str) -> str | None:
    """Categoria de un codigo de ruff."""
    if rule.startswith("I"):
        return "imports"
    if rule.startswith("N"):
        return "nombres"
    if rule in {"C901", "PLR0912", "PLR0913", "PLR0915"}:
        return "complejidad"
    if rule == "PLR0904":
        return "srp"
    return None


def categorize(rule: str, tool: str, message: str, default: str = "calidad") -> str:
    """Asigna una categoria determinista a un hallazgo."""
    ruff = _ruff_category(rule) if tool == "ruff" else None
    if ruff:
        return ruff
    special = {
        "prettier": "formato",
        "spotless": "formato",
        "rustfmt": "formato",
        "lint-imports": "capas",
        "archunit": "capas",
        "ls-lint": "nombres",
    }
    if tool in special:
        return special[tool]
    if tool == "depcruise":
        cycle = any(word in rule.lower() for word in ("ciclo", "cycle"))
        return "acoplamiento" if cycle else "capas"
    text = f"{rule} {message}".lower()
    for category, needles in _HINTS:
        if any(needle in text for needle in needles):
            return category
    return default


def to_violation(finding: Finding, folder: str, default: str) -> Violation:
    """Convierte un hallazgo crudo en una violacion categorizada."""
    rule = finding.rule or finding.tool or "lint"
    message = finding.message.strip() or rule
    return Violation(
        path=repo_path(finding.path, folder),
        line=finding.line,
        column=finding.column,
        category=finding.category or categorize(rule, finding.tool, message, default),
        rule=rule,
        message=message,
        tool=finding.tool or rule,
        fixable=finding.fixable,
    )


def _ruff(text: str) -> list[Finding]:
    """Ruff en formato JSON."""
    out: list[Finding] = []
    for item in _items(_json(text)):
        row = _map(item)
        location = _map(row.get("location"))
        out.append(
            Finding(
                path=_text(row.get("filename")),
                line=_int(location.get("row")),
                column=_int(location.get("column")),
                rule=_text(row.get("code")),
                message=_text(row.get("message")),
                tool="ruff",
                fixable=row.get("fix") is not None,
            )
        )
    return out


def _eslint(text: str) -> list[Finding]:
    """ESLint en formato JSON."""
    out: list[Finding] = []
    for file in _items(_json(text)):
        row = _map(file)
        path = _text(row.get("filePath"))
        for message in _items(row.get("messages")):
            item = _map(message)
            if _int(item.get("severity"), 1) == 0:
                continue
            out.append(
                Finding(
                    path=path,
                    line=_int(item.get("line")),
                    column=_int(item.get("column")),
                    rule=_text(item.get("ruleId")) or "eslint",
                    message=_text(item.get("message")),
                    tool="eslint",
                    fixable=item.get("fix") is not None,
                )
            )
    return out


def _stylelint(text: str) -> list[Finding]:
    """Stylelint en formato JSON."""
    out: list[Finding] = []
    for file in _items(_json(text)):
        row = _map(file)
        path = _text(row.get("source"))
        for warning in _items(row.get("warnings")):
            item = _map(warning)
            out.append(
                Finding(
                    path=path,
                    line=_int(item.get("line")),
                    column=_int(item.get("column")),
                    rule=_text(item.get("rule")) or "stylelint",
                    message=_text(item.get("text")),
                    tool="stylelint",
                )
            )
    return out


def _golangci(text: str) -> list[Finding]:
    """golangci-lint en formato JSON."""
    data = _map(_json(text))
    out: list[Finding] = []
    for issue in _items(data.get("Issues")):
        row = _map(issue)
        pos = _map(row.get("Pos"))
        out.append(
            Finding(
                path=_text(pos.get("Filename")),
                line=_int(pos.get("Line")),
                column=_int(pos.get("Column")),
                rule=_text(row.get("FromLinter")) or "golangci-lint",
                message=_text(row.get("Text")),
                tool="golangci-lint",
            )
        )
    error = _text(_map(data.get("Report")).get("Error"))
    if not out and error:
        return parse_generic(error, "golangci-lint") or [
            Finding(message=error, tool="golangci-lint")
        ]
    return out


def _has_suggestion(message: dict[str, object]) -> bool:
    """True si clippy propone un reemplazo automatico."""
    return any(
        _map(child).get("suggested_replacement") is not None
        for child in _items(message.get("children"))
    )


def _clippy(text: str) -> list[Finding]:
    """Cargo clippy con --message-format=json."""
    out: list[Finding] = []
    for line in text.splitlines():
        if not line.startswith("{"):
            continue
        row = _map(_json(line))
        if row.get("reason") != "compiler-message":
            continue
        message = _map(row.get("message"))
        if _text(message.get("level")) not in {"warning", "error"}:
            continue
        spans = [_map(span) for span in _items(message.get("spans"))]
        span = next(
            (item for item in spans if item.get("is_primary")),
            spans[0] if spans else {},
        )
        code = _map(message.get("code"))
        out.append(
            Finding(
                path=_text(span.get("file_name")),
                line=_int(span.get("line_start")),
                column=_int(span.get("column_start")),
                rule=_text(code.get("code")) or "clippy",
                message=_text(message.get("message")),
                tool="clippy",
                fixable=_has_suggestion(message),
            )
        )
    return out


def _depcruise(text: str) -> list[Finding]:
    """dependency-cruiser en formato JSON."""
    data = _map(_json(text))
    summary = _map(data.get("summary"))
    out: list[Finding] = []
    for item in _items(summary.get("violations")):
        row = _map(item)
        source = row.get("from")
        path = _text(source) if isinstance(source, str) else _text(_map(source).get("resolved"))
        target = row.get("to")
        target_text = (
            _text(target) if isinstance(target, str) else _text(_map(target).get("resolved"))
        )
        rule = _text(_map(row.get("rule")).get("name")) or "dependency-cruiser"
        message = _text(row.get("comment")) or f"{path} -> {target_text}"
        out.append(Finding(path=path, rule=rule, message=message, tool="depcruise"))
    return out


def _nodes(root: ET.Element, name: str) -> list[ET.Element]:
    """Elementos por nombre, ignorando el namespace de Maven."""
    return [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == name]


def _xml(text: str) -> ET.Element | None:
    """Parsea XML generado por Maven; None si no es XML."""
    try:
        return ET.fromstring(text)  # noqa: S314 - XML local generado por Maven
    except ET.ParseError:
        return None


def _checkstyle(text: str) -> list[Finding]:
    """Checkstyle en XML."""
    root = _xml(text)
    if root is None:
        return []
    out: list[Finding] = []
    for file in _nodes(root, "file"):
        path = file.get("name", "")
        for error in _nodes(file, "error"):
            source = error.get("source", "")
            out.append(
                Finding(
                    path=path,
                    line=_int(error.get("line")),
                    column=_int(error.get("column")),
                    rule=source.rsplit(".", 1)[-1],
                    message=error.get("message", ""),
                    tool="checkstyle",
                )
            )
    return out


def _pmd(text: str) -> list[Finding]:
    """PMD en XML."""
    root = _xml(text)
    if root is None:
        return []
    out: list[Finding] = []
    for file in _nodes(root, "file"):
        path = file.get("name", "")
        out.extend(
            Finding(
                path=path,
                line=_int(violation.get("beginline")),
                column=_int(violation.get("begincolumn")),
                rule=violation.get("rule", "pmd"),
                message=(violation.text or "").strip(),
                tool="pmd",
            )
            for violation in _nodes(file, "violation")
        )
    return out


def _java_path(node: ET.Element) -> str:
    """Ruta Java a partir de SpotBugs (sourcepath o clase)."""
    return (
        node.get("sourcepath")
        or _class_path(node.get("classname", ""))
        or node.get("sourcefile")
        or ""
    )


def _class_path(classname: str) -> str:
    """Convierte edu.teachers.Task en src/main/java/edu/teachers/Task.java."""
    if not classname:
        return ""
    return "src/main/java/" + classname.replace(".", "/") + ".java"


def _spotbugs(text: str) -> list[Finding]:
    """SpotBugs en XML."""
    root = _xml(text)
    if root is None:
        return []
    out: list[Finding] = []
    for bug in _nodes(root, "BugInstance"):
        sources = _nodes(bug, "SourceLine")
        source = sources[0] if sources else None
        message = ""
        for name in ("LongMessage", "ShortMessage"):
            nodes = _nodes(bug, name)
            if nodes:
                message = nodes[0].text or ""
                break
        out.append(
            Finding(
                path=_java_path(source) if source is not None else "",
                line=_int(source.get("start")) if source is not None else 1,
                rule=bug.get("type", "spotbugs"),
                message=message,
                tool="spotbugs",
            )
        )
    return out


def _tsc(text: str) -> list[Finding]:
    """TypeScript en modo --pretty false."""
    pattern = re.compile(r"^(.+?)\((\d+),(\d+)\): (error|warning)(?: (TS\d+))?: (.+)$")
    return [
        Finding(
            path=match.group(1),
            line=_int(match.group(2)),
            column=_int(match.group(3)),
            rule=match.group(5) or "tsc",
            message=match.group(6),
            tool="tsc",
        )
        for line in text.splitlines()
        if (match := pattern.match(line.strip()))
    ]


def _mypy(text: str) -> list[Finding]:
    """Mypy con codigos de error."""
    pattern = re.compile(
        r"^(.+?):(\d+)(?::(\d+))?: (error|warning|note): (.+?)(?:\s+\[([a-z0-9-]+)\])?$"
    )
    out: list[Finding] = []
    for line in text.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        out.append(
            Finding(
                path=match.group(1),
                line=_int(match.group(2)),
                column=_int(match.group(3)),
                rule=match.group(6) or "mypy",
                message=match.group(5),
                tool="mypy",
            )
        )
    return out


def _file_list(text: str, tool: str) -> list[Finding]:
    """Herramientas que solo listan archivos (prettier, gofmt, spotless)."""
    out: list[Finding] = []
    for line in text.splitlines():
        stripped = line.strip()
        diff = re.match(r"^Diff in (.+?) at line (\d+):", stripped)
        if diff:
            out.append(
                Finding(
                    path=diff.group(1),
                    line=_int(diff.group(2)),
                    rule=tool,
                    message="archivo sin formatear",
                    tool=tool,
                )
            )
            continue
        compact = re.match(r"^Diff in (?P<path>.+?):(?P<line>\d+):$", stripped)
        if compact:
            out.append(
                Finding(
                    path=compact.group("path"),
                    line=_int(compact.group("line")),
                    rule=tool,
                    message="archivo sin formatear",
                    tool=tool,
                )
            )
            continue
        arrow = re.match(r"^--> (?P<path>.+?):(?P<line>\d+):(?P<col>\d+)$", stripped)
        if arrow:
            out.append(
                Finding(
                    path=arrow.group("path"),
                    line=_int(arrow.group("line")),
                    column=_int(arrow.group("col")),
                    rule=tool,
                    message="archivo sin formatear",
                    tool=tool,
                )
            )
            continue
        if not stripped or stripped.startswith(("[", "!", "?", "<", ">")):
            continue
        if Path(stripped).suffix in EXTS:
            out.append(
                Finding(path=stripped, rule=tool, message="archivo sin formatear", tool=tool)
            )
    return out


def parse_generic(text: str, tool: str) -> list[Finding]:
    """Extrae path:linea:columna de salidas de texto."""
    patterns = (
        re.compile(r"^(?P<path>.+?):(?P<line>\d+):(?P<col>\d+)$"),
        re.compile(
            r"^(?P<path>.+?):(?P<line>\d+):(?P<col>\d+):\s*(?:error|warning)?\s*:?\s*(?P<msg>.+)$"
        ),
        re.compile(r"^(?P<path>.+?):(?P<line>\d+):\s*(?P<msg>.+)$"),
        re.compile(r"^\s*--> (?P<path>.+?):(?P<line>\d+):(?P<col>\d+)$"),
        re.compile(r"At (?P<path>[\w./\\-]+\.java):\[line (?P<line>\d+)\]"),
        re.compile(r"^(?P<path>.+?) failed for .*?rules?: (?P<msg>.+)$"),
    )
    out: list[Finding] = []
    for line in ANSI.sub("", text).splitlines():
        stripped = line.strip()
        if stripped.startswith("-->"):
            stripped = stripped[3:].strip()
        for pattern in patterns:
            match = pattern.match(stripped)
            if not match:
                continue
            path = match.group("path")
            if Path(path).suffix not in EXTS:
                continue
            data = match.groupdict()
            message = _text(data.get("msg")) or line.strip()
            out.append(
                Finding(
                    path=path,
                    line=_int(data.get("line")),
                    column=_int(data.get("col")),
                    rule=tool,
                    message=message,
                    tool=tool,
                )
            )
            break
    return out


def _tests(text: str, tool: str) -> list[Finding]:
    """Fallos de test en formatos habituales."""
    patterns = (
        re.compile(r"^FAILED (\S+?)(?:::(\S+))?(?: - (.+))?$"),
        re.compile(r"^ERROR (\S+?)(?:::(\S+))?(?: - (.+))?$"),
        re.compile(r"^FAIL (\S+) > (.+)$"),
        re.compile(r"^FAIL\s+(\S+)"),
        re.compile(r"^\s*× (.+)$"),
        re.compile(r"^--- FAIL: (\S+)"),
        re.compile(r"^test (\S+) \.\.\. FAILED$"),
    )
    out: list[Finding] = []
    for line in text.splitlines():
        for pattern in patterns:
            match = pattern.match(line.strip())
            if not match:
                continue
            groups = match.groups()
            path = groups[0] if groups[0] and Path(groups[0]).suffix in EXTS else ""
            message = next((part for part in groups[1:] if part), line.strip())
            out.append(Finding(path=path, rule=tool, message=message, tool=tool, category="tests"))
            break
    return out


def _maven(text: str) -> list[Finding]:
    """Maven: fallos de test y violaciones de ArchUnit."""
    out = _tests(text, "maven")
    lowered = text.lower()
    archunit = "violat" in lowered or "architecture" in lowered
    for line in text.splitlines():
        if "Tests run:" in line and re.search(r"(Failures|Errors): [1-9]", line):
            out.append(Finding(rule="tests", message=line.strip(), tool="maven", category="tests"))
        match = re.search(r"\(([\w./\\-]+\.java):(\d+)\)", line)
        if archunit and match:
            out.append(
                Finding(
                    path=match.group(1),
                    line=_int(match.group(2)),
                    rule="archunit",
                    message=line.strip(),
                    tool="maven",
                    category="capas",
                )
            )
    return out


def _coverage(text: str, tool: str) -> list[Finding]:
    """Linea de resumen de cobertura cuando el comando falla."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    summary = next(
        (line for line in lines if line.lower().startswith(("total", "all files"))),
        lines[-1] if lines else "",
    )
    return [Finding(rule="coverage-total", message=summary, tool=tool)] if summary else []


def _semgrep(text: str) -> list[Finding]:
    """Semgrep en formato JSON."""
    data = _map(_json(text))
    out: list[Finding] = []
    for result in _items(data.get("results")):
        row = _map(result)
        start = _map(row.get("start"))
        extra = _map(row.get("extra"))
        out.append(
            Finding(
                path=_text(row.get("path")),
                line=_int(start.get("line")),
                column=_int(start.get("col")),
                rule=_text(row.get("check_id")) or "semgrep",
                message=_text(extra.get("message")),
                tool="semgrep",
            )
        )
    return out


def parse_xml(report: str, text: str) -> list[Finding]:
    """Parsea un reporte XML de Maven segun su tipo."""
    parsers = {
        "checkstyle-xml": _checkstyle,
        "pmd-xml": _pmd,
        "spotbugs-xml": _spotbugs,
    }
    parser = parsers.get(report)
    return parser(text) if parser else []


def _xml_report(cmd: Command, folder: str) -> list[Finding] | None:
    """Lee el XML que deja un plugin de Maven."""
    path = ROOT / folder / cmd.artifact
    if not cmd.artifact or not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    return parse_xml(cmd.report, text)


def _structured(cmd: Command, text: str, folder: str) -> list[Finding] | None:
    """Aplica el parser declarado por el comando, si existe."""
    if cmd.report.endswith("-xml"):
        return _xml_report(cmd, folder)
    parsers = {
        "ruff-json": _ruff,
        "eslint-json": _eslint,
        "stylelint-json": _stylelint,
        "golangci-json": _golangci,
        "clippy-json": _clippy,
        "depcruise-json": _depcruise,
        "tsc": _tsc,
        "mypy": _mypy,
        "file-list": lambda value: _file_list(value, cmd.argv[0]),
        "cargo-fmt": lambda value: _file_list(value, "rustfmt"),
        "spotless": lambda value: _file_list(value, "spotless"),
        "pytest": lambda value: _tests(value, "pytest"),
        "vitest": lambda value: _tests(value, "vitest"),
        "go-test": lambda value: _tests(value, "go test"),
        "maven-test": _maven,
        "coverage": lambda value: _coverage(value, cmd.argv[0]),
        "semgrep-json": _semgrep,
        "generic": lambda value: parse_generic(value, cmd.argv[0]),
    }
    parser = parsers.get(cmd.report)
    if parser is None:
        return None
    return parser(text)


def parse_command(cmd: Command, output: str, code: int | None, folder: str) -> list[Violation]:
    """Convierte la salida de un comando en violaciones normalizadas."""
    if cmd.report == "coverage" and code == 0:
        return []
    text = ANSI.sub("", output)
    findings = _structured(cmd, text, folder)
    if findings is None:
        findings = parse_generic(text, cmd.argv[0])
    violations = [to_violation(finding, folder, cmd.category) for finding in findings]
    if cmd.report == "coverage":
        return dedupe(violations)
    if cmd.report == "maven-test" and any(
        tag in text for tag in ("(naming)", "(imports)", "(design)", "(sizes)", "(coding)")
    ):
        return dedupe(violations)
    if code not in (0, None) and not violations:
        message = next(
            (line.strip() for line in text.splitlines() if line.strip()),
            "fallo sin salida",
        )
        violations.append(
            Violation(
                folder,
                1,
                1,
                cmd.category,
                cmd.argv[0],
                message[:300],
                cmd.argv[0],
                False,
            )
        )
    return dedupe(violations)


def dedupe(violations: list[Violation]) -> list[Violation]:
    """Quita duplicados conservando el orden."""
    seen: set[tuple[str, int, int, str, str, str]] = set()
    out: list[Violation] = []
    for violation in violations:
        key = (
            violation.path,
            violation.line,
            violation.column,
            violation.category,
            violation.rule,
            violation.message,
        )
        if key not in seen:
            seen.add(key)
            out.append(violation)
    return out


def summary(violations: list[Violation]) -> dict[str, int]:
    """Cuenta violaciones por categoria."""
    counts: dict[str, int] = dict.fromkeys(CATEGORIES, 0)
    for violation in violations:
        counts[violation.category] = counts.get(violation.category, 0) + 1
    return {category: count for category, count in counts.items() if count}


def render_text(violations: list[Violation]) -> str:
    """Reporte legible agrupado por archivo."""
    if not violations:
        return "Sin violaciones."
    grouped: dict[str, list[Violation]] = defaultdict(list)
    for violation in violations:
        grouped[violation.path].append(violation)
    lines: list[str] = []
    for path in sorted(grouped):
        lines.append(path)
        for violation in sorted(
            grouped[path], key=lambda item: (item.line, item.column, item.category)
        ):
            mark = "auto" if violation.fixable else "manual"
            lines.append(
                f"  {violation.category:<12} {violation.line:>4}:{violation.column:<3} "
                f"{violation.message} [{violation.rule}] ({mark})"
            )
        lines.append("")
    counts = summary(violations)
    detail = " · ".join(f"{category} {count}" for category, count in counts.items())
    lines.append(f"Resumen: {detail}")
    return "\n".join(lines)


def render_json(violations: list[Violation]) -> str:
    """Reporte estructurado para agentes."""
    ordered = sorted(
        violations, key=lambda item: (item.path, item.line, item.column, item.category)
    )
    return json.dumps(
        {
            "ok": not violations,
            "total": len(violations),
            "summary": summary(violations),
            "violations": [asdict(violation) for violation in ordered],
        },
        ensure_ascii=False,
        indent=2,
    )
