"""Validacion determinista de proyectos externos (--project --validate)."""

from __future__ import annotations

import contextlib
import re
from dataclasses import replace
from pathlib import Path

from lintlib import quality
from lintlib.common import NODE_EXTS, ROOT, TOOLS, Command, exec_external, relative
from lintlib.portable import (
    Project,
    discover,
    is_rust_workspace,
    portable_size,
    project_warnings,
)

RUST_LINTS = (
    "-D",
    "warnings",
    "-D",
    "clippy::many_single_char_names",
    "-D",
    "clippy::too_many_lines",
    "-D",
    "clippy::cognitive_complexity",
    "-D",
    "clippy::too_many_arguments",
    "-D",
    "clippy::module_name_repetitions",
    "-D",
    "clippy::similar_names",
    "-D",
    "clippy::needless_pass_by_value",
    "-D",
    "clippy::redundant_clone",
    "-D",
    "clippy::unnecessary_wraps",
    "-D",
    "clippy::wildcard_imports",
    "-D",
    "clippy::unused_self",
    "-D",
    "clippy::manual_let_else",
    "-D",
    "clippy::items_after_statements",
    "-D",
    "clippy::struct_excessive_bools",
    "-D",
    "clippy::type_complexity",
    "-D",
    "clippy::needless_range_loop",
    "-D",
    "clippy::redundant_closure_for_method_calls",
    "-D",
    "clippy::trivially_copy_pass_by_ref",
    "-D",
    "clippy::return_self_not_must_use",
    "-D",
    "clippy::must_use_candidate",
    "-D",
    "clippy::missing_errors_doc",
    "-D",
    "clippy::missing_panics_doc",
    "-D",
    "clippy::doc_markdown",
    "-D",
    "clippy::unwrap_used",
    "-D",
    "clippy::expect_used",
    "-D",
    "clippy::panic",
    "-D",
    "clippy::todo",
    "-D",
    "clippy::unimplemented",
    "-D",
    "clippy::dbg_macro",
)

SIZE_RE = re.compile(r"^\s*(.+?):1 archivo de (\d+) lineas \(maximo (\d+)\)")

RUST_ENV = {"CLIPPY_CONF_DIR": str(TOOLS / "rust")}


def project_prefix(project: Project, root: Path) -> str:
    """Prefijo del proyecto relativo a la raiz externa."""
    prefix = project.folder.relative_to(root).as_posix()
    return "" if prefix == "." else prefix


def external_path(violation: quality.Violation, root: Path) -> quality.Violation:
    """Convierte rutas absolutas en relativas a la raiz externa."""
    raw = violation.path.replace("\\", "/")
    path = Path(raw)
    if path.is_absolute():
        with contextlib.suppress(ValueError):
            raw = path.resolve().relative_to(root).as_posix()
    return replace(violation, path=raw)


def parse_result(
    cmd: Command,
    result: tuple[int | None, str],
    project: Project,
    root: Path,
) -> list[quality.Violation]:
    """Parsea la salida de una herramienta externa."""
    code, output = result
    folder = project_prefix(project, root)
    found = quality.parse_command(cmd, output, code, folder)
    return [external_path(violation, root) for violation in found]


def fallback(
    cmd: Command, result: tuple[int | None, str], project: Project, root: Path
) -> quality.Violation:
    """Violacion de proyecto cuando la herramienta falla sin archivo."""
    _, output = result
    message = next(
        (line.strip() for line in output.splitlines() if line.strip()),
        "fallo sin salida",
    )
    return quality.Violation(
        project_prefix(project, root) or ".",
        1,
        1,
        "calidad",
        cmd.argv[0],
        message[:300],
        "portable",
        False,
    )


def with_fallback(
    cmd: Command,
    result: tuple[int | None, str],
    project: Project,
    root: Path,
) -> list[quality.Violation]:
    """Anade el fallback solo si no hubo violaciones parseables."""
    found = parse_result(cmd, result, project, root)
    code, _ = result
    if (code is None or code != 0) and not found:
        found.append(fallback(cmd, result, project, root))
    return found


def _result(
    cmd: Command,
    result: tuple[int | None, str],
    project: Project,
    root: Path,
) -> tuple[int, list[quality.Violation]]:
    """Traduce el resultado de una herramienta a estado y violaciones."""
    code, _ = result
    status = 2 if code is None else (0 if code == 0 else 1)
    return status, with_fallback(cmd, result, project, root)


def run_json_result(
    cmd: Command, argv: list[str], project: Project, root: Path
) -> tuple[int, list[quality.Violation]]:
    """Ejecuta una herramienta con salida JSON y normaliza el resultado."""
    result = exec_external(argv, project.folder, json_stdout=True)
    return _result(cmd, result, project, root)


def run_text_result(
    cmd: Command, argv: list[str], project: Project, root: Path
) -> tuple[int, list[quality.Violation]]:
    """Ejecuta una herramienta de texto y normaliza el resultado."""
    result = exec_external(argv, project.folder)
    return _result(cmd, result, project, root)


def size_violations(project: Project, root: Path) -> list[quality.Violation]:
    """Convierte el tamano de archivo en violaciones de SRP."""
    status, lines = portable_size(project)
    if status == 0:
        return []
    prefix = project_prefix(project, root)
    out: list[quality.Violation] = []
    for line in lines:
        match = SIZE_RE.match(line)
        if not match:
            continue
        path = match.group(1) if not prefix else f"{prefix}/{match.group(1)}"
        message = f"archivo de {match.group(2)} lineas (maximo {match.group(3)})"
        out.append(
            quality.Violation(path, 1, 1, "srp", "max-file-lines", message, "portable", False)
        )
    return out


def rust_clippy(project: Project, fix: bool) -> list[str]:
    """Comando clippy estricto para el proyecto Rust."""
    argv = ["cargo", "clippy"]
    if is_rust_workspace(project.folder):
        argv.append("--workspace")
    argv.append("--all-targets")
    if fix:
        argv.extend(["--fix", "--allow-dirty"])
    else:
        argv.append("--message-format=json")
    return [*argv, "--", *RUST_LINTS]


def rust_violations(project: Project, root: Path, fix: bool) -> tuple[int, list[quality.Violation]]:
    """Formato y clippy estricto para Rust."""
    if fix:
        exec_external(["cargo", "fmt"], project.folder)
        exec_external(rust_clippy(project, True), project.folder, env=RUST_ENV)
    fmt = run_text_result(
        Command(["cargo"], report="cargo-fmt", category="formato"),
        ["cargo", "fmt", "--check"],
        project,
        root,
    )
    result = exec_external(
        rust_clippy(project, False), project.folder, json_stdout=True, env=RUST_ENV
    )
    clippy = _result(Command(["cargo"], report="clippy-json"), result, project, root)
    return max(fmt[0], clippy[0]), [*fmt[1], *clippy[1]]


def node_violations(project: Project, root: Path, fix: bool) -> tuple[int, list[quality.Violation]]:
    """ESLint, Stylelint y dependency-cruiser con el baseline portable."""
    status = 0
    out: list[quality.Violation] = []
    code = [f for f in project.files if Path(f).suffix in NODE_EXTS]
    styles = [f for f in project.files if Path(f).suffix == ".scss"]
    config = TOOLS / "node"
    if code:
        base = [
            "eslint",
            "--no-config-lookup",
            "--config",
            str(config / "eslint.config.js"),
        ]
        if fix:
            exec_external([*base, "--fix", *relative(code, project.folder)], project.folder)
        result = run_json_result(
            Command(["eslint"], report="eslint-json"),
            [*base, "--format=json", *relative(code, project.folder)],
            project,
            root,
        )
        status = max(status, result[0])
        out.extend(result[1])
    if styles:
        base = ["stylelint", "--config", str(config / "stylelint.config.js")]
        if fix:
            exec_external([*base, "--fix", *relative(styles, project.folder)], project.folder)
        result = run_json_result(
            Command(["stylelint"], report="stylelint-json"),
            [*base, "--formatter=json", *relative(styles, project.folder)],
            project,
            root,
        )
        status = max(status, result[0])
        out.extend(result[1])
    if (project.folder / "src").is_dir():
        result = run_json_result(
            Command(["depcruise"], report="depcruise-json", category="capas"),
            [
                "depcruise",
                "src",
                "--config",
                str(config / "depcruise.cjs"),
                "--output-type",
                "json",
            ],
            project,
            root,
        )
        status = max(status, result[0])
        out.extend(result[1])
    return status, out


def go_violations(project: Project, root: Path, fix: bool) -> tuple[int, list[quality.Violation]]:
    """golangci-lint con el baseline portable."""
    base = ["golangci-lint", "run", "--config", str(TOOLS / "go" / ".golangci.yml")]
    if fix:
        exec_external([*base, "--fix"], project.folder)
    return run_json_result(
        Command(["golangci-lint"], report="golangci-json"),
        [*base, "--output.json.path", "stdout", "--output.text.path", "stderr"],
        project,
        root,
    )


def python_violations(
    project: Project, root: Path, fix: bool
) -> tuple[int, list[quality.Violation]]:
    """Ruff con el baseline portable."""
    files = relative(project.files, project.folder)
    base = ["ruff", "check", "--config", str(TOOLS / "python" / "ruff.toml")]
    if fix:
        exec_external([*base, "--fix", *files], project.folder)
    return run_json_result(
        Command(["ruff"], report="ruff-json"),
        [*base, "--output-format=json", *files],
        project,
        root,
    )


def godot_violations(
    project: Project, root: Path, fix: bool
) -> tuple[int, list[quality.Violation]]:
    """Gdlint y gdformat para proyectos Godot."""
    if fix:
        exec_external(["gdformat", "."], project.folder)
    fmt = run_text_result(
        Command(["gdformat"], report="file-list", category="formato"),
        ["gdformat", "--check", "."],
        project,
        root,
    )
    lint = run_text_result(
        Command(["gdlint"], report="generic"),
        ["gdlint", "."],
        project,
        root,
    )
    return max(fmt[0], lint[0]), [*fmt[1], *lint[1]]


def java_violations(project: Project, root: Path, fix: bool) -> tuple[int, list[quality.Violation]]:
    """Semgrep como baseline de seguridad para Java."""
    del fix
    return run_text_result(
        Command(["semgrep"], report="generic"),
        [
            "semgrep",
            "--config",
            "p/java",
            "--config",
            str(ROOT / ".semgrep" / "rules.yml"),
            "--error",
            "--quiet",
            ".",
        ],
        project,
        root,
    )


def project_violations(
    project: Project, root: Path, fix: bool
) -> tuple[int, list[quality.Violation]]:
    """Ejecuta el validador que corresponde al tipo de proyecto."""
    if project.kind == "node":
        return node_violations(project, root, fix)
    if project.kind == "go":
        return go_violations(project, root, fix)
    if project.kind == "python":
        return python_violations(project, root, fix)
    if project.kind == "rust":
        return rust_violations(project, root, fix)
    if project.kind == "godot":
        return godot_violations(project, root, fix)
    return java_violations(project, root, fix)


def validate_project(
    project: Project, root: Path, fix: bool
) -> tuple[int, list[quality.Violation], list[str]]:
    """Valida un proyecto y devuelve estado, violaciones y avisos."""
    status, _ = portable_size(project)
    violations = size_violations(project, root) if status else []
    project_status, found = project_violations(project, root, fix)
    return (
        max(status, project_status),
        [*violations, *found],
        project_warnings(project, root),
    )


def finish(status: int) -> int:
    """Mensaje final del modo externo."""
    if status == 2:
        print("\nFalta una herramienta. Instalala y reintenta (ver README).")
        return 2
    if status == 1:
        print("\nHallazgos. Arreglo automatico: --fix")
        return 1
    print("\nTodo limpio.")
    return 0


def portable_validate(path: Path, fix: bool, as_json: bool) -> int:
    """Audita un proyecto externo y reporta violaciones por archivo."""
    root = path.resolve()
    if not root.is_dir():
        print(f"[X] no existe la carpeta {root}")
        return 2
    projects = discover(root)
    if not projects:
        print(f"[X] {root}: no encontre un manifiesto de proyecto.")
        print("    Sin manifiesto no hay proyecto que auditar (no es 'todo limpio').")
        return 2
    status = 0
    violations: list[quality.Violation] = []
    warnings: list[str] = []
    for project in projects:
        project_status, found, project_warnings_found = validate_project(project, root, fix)
        status = max(status, project_status)
        violations.extend(found)
        warnings.extend(project_warnings_found)
    violations = quality.dedupe(violations)
    status = max(status, 1 if violations else 0)
    if as_json:
        print(quality.render_json(violations))
        return status
    print(f"\n== validacion externa: {root.name} ==")
    for warning in warnings:
        print(f"  aviso: {warning}")
    print(quality.render_text(violations))
    return finish(status)
