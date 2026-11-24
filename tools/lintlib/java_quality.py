"""Arquitectura, Spring, DTOs y tests de proyectos Java externos."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from lintlib import quality, solid

PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.MULTILINE)
IMPORT_RE = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)\s*;", re.MULTILINE)
TYPE_RE = re.compile(
    r"^\s*(?:public\s+)?(?:final\s+|abstract\s+)?(class|interface|enum|record)\s+(\w+)",
    re.MULTILINE,
)
TEST_RE = re.compile(r"^\s*@(?:Test|ParameterizedTest)\b", re.MULTILINE)
ASSERT_RE = re.compile(r"\b(assert\w*|verify|andExpect|assertThat|assertThrows|fail)\b")

FRAMEWORKS = (
    "jakarta.persistence",
    "javax.persistence",
    "org.springframework",
    "org.hibernate",
    "lombok",
)

LAYER_RULES = {
    "domain": {"web", "service", "repo", "config"},
    "service": {"web", "repo"},
    "web": {"repo"},
    "repo": {"web", "service"},
}


@dataclass(frozen=True)
class Rule:
    """Categoria y nombre estable de una regla Java."""

    category: str
    name: str


DOMAIN_FRAMEWORK = Rule("capas", "dominio-framework")
LAYER_DEPENDENCY = Rule("capas", "capa-dependencia")
SPRING_CONTROLLER = Rule("calidad", "spring-controller")
SPRING_SERVICE = Rule("calidad", "spring-service")
SPRING_REPO = Rule("capas", "spring-repo")
FIELD_INJECTION = Rule("calidad", "inyeccion-campo")
DTO_DOMAIN = Rule("capas", "dto-dominio")
MAPPER = Rule("srp", "mapper")
GOD_FILE = Rule("srp", "archivo-tipos")
ENTITY_EXPOSED = Rule("capas", "entidad-expuesta")
TEST_NO_ASSERT = Rule("tests", "test-sin-assert")
TEST_LARGE = Rule("tests", "test-largo")
TEST_GIANT = Rule("tests", "test-gigante")
TEST_MISSING = Rule("tests", "sin-test-unitario")
NO_TESTS = Rule("tests", "sin-tests")
TRANSACTIONAL_CONTROLLER = Rule("capas", "transaccional-en-controller")
ENTITY_LOCATION = Rule("capas", "entidad-fuera-de-infra")
PII_LOG = Rule("calidad", "pii-en-log")
SLEEP_PRODUCTION = Rule("calidad", "sleep-en-produccion")


@dataclass(frozen=True)
class JavaType:
    """Declaracion de tipo Java con sus anotaciones inmediatas."""

    name: str
    kind: str
    annotations: str
    line: int


@dataclass(frozen=True)
class JavaFile:
    """Fuente Java con paquete, imports y tipos declarados."""

    path: Path
    relative: str
    package: str
    imports: tuple[tuple[str, int], ...]
    types: tuple[JavaType, ...]
    text: str


def _line(text: str, position: int) -> int:
    """Linea 1-based de una posicion en el texto."""
    return text.count("\n", 0, position) + 1


def _types(text: str) -> tuple[JavaType, ...]:
    """Tipos declarados y sus anotaciones de la linea anterior."""
    lines = text.splitlines()
    out: list[JavaType] = []
    for match in TYPE_RE.finditer(text):
        line = _line(text, match.start())
        annotations: list[str] = []
        index = line - 2
        while index >= 0:
            stripped = lines[index].strip()
            if stripped.startswith("@"):
                annotations.append(stripped)
                index -= 1
                continue
            break
        out.append(
            JavaType(
                name=match.group(2),
                kind=match.group(1),
                annotations=" ".join(reversed(annotations)),
                line=line,
            )
        )
    return tuple(out)


def _parse(path: Path, root: Path) -> JavaFile:
    """Lee un archivo Java y extrae su estructura basica."""
    text = path.read_text(encoding="utf-8", errors="replace")
    package = PACKAGE_RE.search(text)
    imports = tuple(
        (match.group(1), _line(text, match.start())) for match in IMPORT_RE.finditer(text)
    )
    return JavaFile(
        path=path,
        relative=path.relative_to(root).as_posix(),
        package=package.group(1) if package else "",
        imports=imports,
        types=_types(text),
        text=text,
    )


def scan(root: Path) -> list[JavaFile]:
    """Fuentes de src/main/java, ordenadas por ruta."""
    base = root / "src" / "main" / "java"
    if not base.is_dir():
        return []
    return [_parse(path, root) for path in sorted(base.rglob("*.java"))]


def package_kind(package: str) -> str:
    """Capa de un paquete por su nombre."""
    parts = package.split(".")
    for kind in ("domain", "service", "web", "repo", "config"):
        if kind in parts:
            return kind
    return "other"


def _violation(file: JavaFile, line: int, rule: Rule, message: str) -> quality.Violation:
    """Violacion Java relativa a la raiz del proyecto."""
    return quality.Violation(
        file.relative, line, 1, rule.category, rule.name, message, "java", False
    )


def _path_violation(relative: str, line: int, rule: Rule, message: str) -> quality.Violation:
    """Violacion Java a partir de una ruta relativa."""
    return quality.Violation(relative, line, 1, rule.category, rule.name, message, "java", False)


def layer_violations(file: JavaFile) -> list[quality.Violation]:
    """Direccion de dependencias entre capas y frameworks en dominio."""
    kind = package_kind(file.package)
    out: list[quality.Violation] = []
    for imported, line in file.imports:
        target = package_kind(imported)
        if kind == "domain" and imported.startswith(FRAMEWORKS):
            message = f"el dominio importa {imported}; el dominio no conoce frameworks"
            out.append(_violation(file, line, DOMAIN_FRAMEWORK, message))
        if target in LAYER_RULES.get(kind, set()):
            message = f"{kind} importa {imported}; depende hacia {target}"
            out.append(_violation(file, line, LAYER_DEPENDENCY, message))
    return out


def _has_annotation(java_type: JavaType, *names: str) -> bool:
    """True si el tipo lleva alguna de las anotaciones."""
    return any(
        annotation.startswith(name)
        for annotation in java_type.annotations.split()
        for name in names
    )


def spring_violations(file: JavaFile) -> list[quality.Violation]:
    """Anotaciones Spring e inyeccion por constructor."""
    kind = package_kind(file.package)
    out: list[quality.Violation] = []
    for java_type in file.types:
        if (
            kind == "web"
            and java_type.name.endswith("Controller")
            and not _has_annotation(java_type, "@RestController", "@Controller")
        ):
            message = f"{java_type.name} debe llevar @RestController o @Controller"
            out.append(_violation(file, java_type.line, SPRING_CONTROLLER, message))
        if (
            kind == "service"
            and java_type.name.endswith("Service")
            and not _has_annotation(java_type, "@Service")
        ):
            message = f"{java_type.name} debe llevar @Service"
            out.append(_violation(file, java_type.line, SPRING_SERVICE, message))
        if (
            java_type.kind == "interface"
            and "extends JpaRepository" in file.text
            and kind not in {"repo", "repository", "persistence"}
        ):
            message = f"{java_type.name} extiende JpaRepository fuera de repo/"
            out.append(_violation(file, java_type.line, SPRING_REPO, message))
    for match in re.finditer(r"(?m)^\s*@Autowired\b", file.text):
        message = "@Autowired en campo; usa inyeccion por constructor"
        out.append(
            _violation(
                file,
                _line(file.text, match.start()),
                FIELD_INJECTION,
                message,
            )
        )
    return out


def dto_violations(file: JavaFile) -> list[quality.Violation]:
    """DTOs que exponen tipos del dominio."""
    if "web.dto" not in file.package:
        return []
    domain = [imported for imported, _ in file.imports if ".domain." in imported]
    if not domain:
        return []
    names = ", ".join(domain[:3])
    message = f"DTO importa {len(domain)} tipos del dominio ({names}); usa DTOs propios y mappers"
    return [_violation(file, 1, DTO_DOMAIN, message)]


def mapper_violations(file: JavaFile) -> list[quality.Violation]:
    """Servicios que construyen DTOs en vez de delegar en un mapper."""
    if package_kind(file.package) != "service" or not re.search(r"new\s+Dtos\.", file.text):
        return []
    message = "el servicio construye DTOs; extrae un mapper"
    return [_violation(file, 1, MAPPER, message)]


def god_file_violations(file: JavaFile) -> list[quality.Violation]:
    """Archivos con demasiados tipos declarados (DTOs gigantes)."""
    if len(file.types) <= 10:
        return []
    message = f"archivo con {len(file.types)} tipos; separa DTOs o clases"
    return [_violation(file, 1, GOD_FILE, message)]


def entity_boundary_violations(file: JavaFile, entities: set[str]) -> list[quality.Violation]:
    """Controladores que devuelven o reciben entidades en vez de DTOs."""
    if package_kind(file.package) != "web":
        return []
    out: list[quality.Violation] = []
    for entity in entities:
        returned = re.search(
            rf"^\s*public\s+(?:List<|Optional<)?\s*{entity}\b", file.text, re.MULTILINE
        )
        received = re.search(rf"@RequestBody\s+{entity}\b", file.text)
        if returned or received:
            message = f"el web usa la entidad {entity}; expone un DTO"
            match = returned or received
            if match is not None:
                out.append(
                    _violation(
                        file,
                        _line(file.text, match.start()),
                        ENTITY_EXPOSED,
                        message,
                    )
                )
    return out


def missing_assertions(relative: str, text: str) -> list[quality.Violation]:
    """Tests sin ninguna asercion."""
    blocks = TEST_RE.split(text)
    out: list[quality.Violation] = []
    position = 0
    for block in blocks[1:]:
        start = text.find(block, position)
        position = start + len(block)
        if ASSERT_RE.search(block):
            continue
        message = "test sin asercion; verifica el comportamiento"
        out.append(_path_violation(relative, _line(text, start), TEST_NO_ASSERT, message))
    return out


def test_file_violations(path: Path, root: Path) -> list[quality.Violation]:
    """Tamano, cantidad de casos y aserciones de un archivo de test."""
    text = path.read_text(encoding="utf-8", errors="replace")
    relative = path.relative_to(root).as_posix()
    out: list[quality.Violation] = []
    lines = text.count("\n") + 1
    if lines > 400:
        message = f"test de {lines} lineas; divide por caso"
        out.append(_path_violation(relative, 1, TEST_LARGE, message))
    tests = len(TEST_RE.findall(text))
    if tests > 15:
        message = f"test con {tests} casos; divide por responsabilidad"
        out.append(_path_violation(relative, 1, TEST_GIANT, message))
    out.extend(missing_assertions(relative, text))
    return out


def missing_unit_tests(main_files: list[JavaFile], test_names: set[str]) -> list[quality.Violation]:
    """Servicios de produccion sin un test unitario con su nombre."""
    out: list[quality.Violation] = []
    for file in main_files:
        if package_kind(file.package) != "service":
            continue
        for java_type in file.types:
            if java_type.kind != "class" or not java_type.name.endswith("Service"):
                continue
            if f"{java_type.name}Test" in test_names:
                continue
            message = f"sin {java_type.name}Test; agrega un test unitario"
            out.append(_violation(file, java_type.line, TEST_MISSING, message))
    return out


def test_violations(root: Path, main_files: list[JavaFile]) -> list[quality.Violation]:
    """Tests ausentes, gigantes o sin aserciones."""
    test_root = root / "src" / "test" / "java"
    test_files = sorted(test_root.rglob("*.java")) if test_root.is_dir() else []
    out: list[quality.Violation] = []
    if not test_files:
        out.append(_path_violation("src/test/java", 1, NO_TESTS, "no encontre tests"))
    test_names = {path.stem for path in test_files}
    for path in test_files:
        out.extend(test_file_violations(path, root))
    out.extend(missing_unit_tests(main_files, test_names))
    return out


PII_LOG_RE = re.compile(
    r"log\s*\.\s*(?:info|warn|error|debug|trace)\s*\([^;]*"
    r"\b(?:email|e-mail|mail|phone|telefono|documento|cpf|dni|address|direccion)\b",
    re.IGNORECASE,
)
SLEEP_RE = re.compile(r"Thread\s*\.\s*sleep\s*\(")
# Capas donde una @Entity de JPA no deberia aparecer.
NON_PERSISTENCE = {"web", "controller", "service", "application"}


def strict_violations(file: JavaFile) -> list[quality.Violation]:
    """Reglas de exigencia que no cubre ninguna herramienta externa."""
    out: list[quality.Violation] = []
    kind = package_kind(file.package)
    name = Path(file.relative).name

    if name.endswith("Controller.java") and "@Transactional" in file.text:
        line = _line(file.text, file.text.index("@Transactional"))
        out.append(
            _path_violation(
                file.relative,
                line,
                TRANSACTIONAL_CONTROLLER,
                "el controller declara @Transactional; la transaccion pertenece al servicio",
            )
        )

    if "@Entity" in file.text and kind in NON_PERSISTENCE:
        line = _line(file.text, file.text.index("@Entity"))
        out.append(
            _path_violation(
                file.relative,
                line,
                ENTITY_LOCATION,
                f"@Entity en la capa {kind}; la persistencia va en infraestructura",
            )
        )

    pii = PII_LOG_RE.search(file.text)
    if pii:
        out.append(
            _path_violation(
                file.relative,
                _line(file.text, pii.start()),
                PII_LOG,
                "el log podria exponer datos personales; registra un identificador, no el dato",
            )
        )

    sleep = SLEEP_RE.search(file.text)
    if sleep:
        out.append(
            _path_violation(
                file.relative,
                _line(file.text, sleep.start()),
                SLEEP_PRODUCTION,
                "Thread.sleep en produccion bloquea el hilo; usa un scheduler o un timeout",
            )
        )

    return out


def analyze(root: Path) -> list[quality.Violation]:
    """Analiza un proyecto Java y devuelve violaciones deterministas."""
    main_files = scan(root)
    if not main_files:
        return []
    entities = {
        java_type.name
        for file in main_files
        for java_type in file.types
        if "@Entity" in java_type.annotations
    }
    out: list[quality.Violation] = []
    for file in main_files:
        out.extend(layer_violations(file))
        out.extend(spring_violations(file))
        out.extend(dto_violations(file))
        out.extend(mapper_violations(file))
        out.extend(god_file_violations(file))
        out.extend(entity_boundary_violations(file, entities))
        out.extend(strict_violations(file))
    out.extend(test_violations(root, main_files))
    units = [solid.Unit(file.relative, file.text, file.imports) for file in main_files]
    out.extend(solid.analyze(units, "java"))
    return quality.dedupe(out)
