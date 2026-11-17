"""Baseline portable para proyectos externos detectados por manifiesto."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from lintlib.common import (
    NODE_EXTS,
    ROOT,
    TOOLS,
    exec_external,
    portable_bin,
    relative,
    show,
    walk_files,
)

PROJECTS = (
    ("node", "package.json"),
    ("python", "pyproject.toml"),
    ("python", "requirements.txt"),
    ("go", "go.mod"),
    ("java", "pom.xml"),
    ("java", "build.gradle"),
    ("java", "build.gradle.kts"),
    ("rust", "Cargo.toml"),
    ("godot", "project.godot"),
)

KIND_BY_EXT = {
    ".py": "python",
    ".ts": "node",
    ".tsx": "node",
    ".js": "node",
    ".jsx": "node",
    ".mjs": "node",
    ".cjs": "node",
    ".go": "go",
    ".java": "java",
    ".kt": "java",
    ".rs": "rust",
    ".gd": "godot",
}


@dataclass(frozen=True)
class Project:
    """Proyecto externo detectado por su manifiesto."""

    kind: str
    folder: Path
    files: list[str]


def owner_of(path: Path, root: Path) -> tuple[str, Path] | None:
    """Manifiesto mas cercano, prefiriendo el lenguaje de la extension."""
    preferred = KIND_BY_EXT.get(path.suffix.lower())
    current = path.parent
    while True:
        found = [(kind, current) for kind, manifest in PROJECTS if (current / manifest).is_file()]
        if found:
            for kind, folder in found:
                if kind == preferred:
                    return kind, folder
            return found[0]
        if current == root:
            return None
        current = current.parent


def is_rust_workspace(folder: Path) -> bool:
    """True si el Cargo.toml declara un workspace."""
    try:
        text = (folder / "Cargo.toml").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return re.search(r"(?m)^\s*\[workspace\]\s*$", text) is not None


def merge_rust_workspaces(projects: list[Project]) -> list[Project]:
    """Funde los crates miembros en su workspace para no repetir clippy."""
    roots = [p for p in projects if p.kind == "rust" and is_rust_workspace(p.folder)]
    if not roots:
        return projects
    files = {root.folder: set(root.files) for root in roots}
    absorbed = set()
    for project in projects:
        if project.kind != "rust" or project.folder in files:
            continue
        root = next(
            (candidate for candidate in roots if project.folder.is_relative_to(candidate.folder)),
            None,
        )
        if root is not None:
            files[root.folder].update(project.files)
            absorbed.add(project.folder)
    return [
        Project(project.kind, project.folder, sorted(files[project.folder]))
        if project.folder in files
        else project
        for project in projects
        if project.folder not in absorbed
    ]


def discover(root: Path) -> list[Project]:
    """Agrupa los archivos por proyecto (manifiesto mas cercano)."""
    groups: dict[tuple[str, Path], list[str]] = {}
    for path in walk_files(root):
        found = owner_of(path, root)
        if found:
            groups.setdefault(found, []).append(path.as_posix())
    projects = [Project(kind, folder, sorted(files)) for (kind, folder), files in groups.items()]
    return merge_rust_workspaces(projects)


def node_project(project: Project, fix: bool) -> int:
    """ESLint + Stylelint + dependency-cruiser con el baseline portable."""
    status = 0
    files = project.files
    code = [f for f in files if Path(f).suffix in NODE_EXTS]
    styles = [f for f in files if Path(f).suffix == ".scss"]
    root = TOOLS / "node"

    if code:
        argv = [
            "eslint",
            "--no-config-lookup",
            "--config",
            str(root / "eslint.config.js"),
            *(["--fix"] if fix else []),
            *relative(code, project.folder),
        ]
        status = max(status, show(*exec_external(argv, project.folder), "sin hallazgos"))

    if styles:
        argv = [
            "stylelint",
            "--config",
            str(root / "stylelint.config.js"),
            *(["--fix"] if fix else []),
            *relative(styles, project.folder),
        ]
        status = max(status, show(*exec_external(argv, project.folder), "sin hallazgos"))

    if (project.folder / "src").is_dir():
        argv = [
            "depcruise",
            "src",
            "--config",
            str(root / "depcruise.cjs"),
        ]
        status = max(status, show(*exec_external(argv, project.folder), "sin ciclos"))
    return status


def go_project(project: Project, fix: bool) -> int:
    """golangci-lint con el baseline portable (sin reglas de capas)."""
    argv = ["golangci-lint", "run", "--config", str(TOOLS / "go" / ".golangci.yml")]
    if fix:
        argv.append("--fix")
    return show(*exec_external(argv, project.folder), "sin hallazgos")


SOURCE_EXTS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".java",
    ".kt",
    ".go",
    ".rs",
    ".gd",
    ".cs",
    ".c",
    ".cpp",
    ".cc",
    ".h",
    ".hpp",
}

TEST_RE = re.compile(r"(?i)(^|[/_\-.])(test|spec|tests?)([/_\-.]|$)|(?:Test|Tests|IT|Spec)\.\w+$")

GENERATED_RE = re.compile(
    r"(?i)(?:\.min\.|\.bundle\.|\.generated\.|(?:^|/)(?:vendor|third_party|third-party|pdfjs)/)"
)

PORTABLE_MAX_LINES = 400


def portable_size(project: Project) -> tuple[int, list[str]]:
    """Reporta fuentes de mas de PORTABLE_MAX_LINES lineas."""
    status = 0
    lines: list[str] = []
    for name in project.files:
        path = Path(name)
        if path.suffix.lower() not in SOURCE_EXTS:
            continue
        if TEST_RE.search(path.name) or GENERATED_RE.search(name):
            continue
        try:
            total = sum(1 for _ in path.open(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if total > PORTABLE_MAX_LINES:
            relative = path.relative_to(project.folder).as_posix()
            lines.append(f"  {relative}:1 archivo de {total} lineas (maximo {PORTABLE_MAX_LINES})")
            status = 1
    return status, lines


def ancestor_has(folder: Path, root: Path, name: str) -> bool:
    """True si el archivo o carpeta existe en la carpeta o un ancestro hasta root."""
    current = folder
    while True:
        if (current / name).exists():
            return True
        if current == root:
            return False
        current = current.parent


def project_warnings(project: Project, root: Path) -> list[str]:
    """Avisos de higiene que no bloquean pero conviene ver."""
    warnings = []
    if not any(TEST_RE.search(Path(name).name) for name in project.files):
        warnings.append("no encontre tests")
    if not ancestor_has(project.folder, root, ".github/workflows"):
        warnings.append("sin CI")
    readmes = ("README.md", "README.rst", "README")
    if not any(ancestor_has(project.folder, root, name) for name in readmes):
        warnings.append("sin README")
    return warnings


def godot_project(project: Project, fix: bool) -> int:
    """Corre gdlint y gdformat para proyectos Godot."""
    fmt = ["gdformat", "."] if fix else ["gdformat", "--check", "."]
    status = show(*exec_external(fmt, project.folder), "sin hallazgos")
    return max(status, show(*exec_external(["gdlint", "."], project.folder), "sin hallazgos"))


def cargo_metadata(folder: Path) -> dict[str, Any] | None:
    """Metadata del crate o workspace; None si cargo no responde."""
    exe = portable_bin("cargo")
    if exe is None:
        return None
    try:
        proc = subprocess.run(  # noqa: S603 - executable resuelto con shutil.which
            [exe, "metadata", "--no-deps", "--format-version", "1"],
            cwd=folder,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    try:
        return cast("dict[str, Any]", json.loads(proc.stdout))
    except ValueError:
        return None


def target_flags(kinds: set[str]) -> list[str]:
    """Flags de cargo para los tipos de target presentes."""
    flags = []
    if "lib" in kinds or kinds & {"proc-macro", "cdylib", "staticlib", "dylib"}:
        flags.append("--lib")
    if "bin" in kinds:
        flags.append("--bins")
    if "example" in kinds:
        flags.append("--examples")
    return flags or ["--all-targets"]


def cargo_target_flags(folder: Path) -> list[str]:
    """Flags de targets reales (lib/bin/example) del crate o workspace."""
    data = cargo_metadata(folder)
    if data is None:
        return ["--all-targets"]
    kinds = set()
    for package in data.get("packages", []):
        for target in package.get("targets", []):
            kinds.update(target.get("kind", []))
    return target_flags(kinds)


def rust_project(project: Project, fix: bool) -> int:
    """Formatea y pasa clippy estricto al codigo de produccion."""
    fmt = ["cargo", "fmt"] if fix else ["cargo", "fmt", "--check"]
    status = show(*exec_external(fmt, project.folder), "sin hallazgos")
    flags = cargo_target_flags(project.folder)
    if is_rust_workspace(project.folder):
        flags = ["--workspace", *flags]
    clippy = ["cargo", "clippy"]
    if fix:
        clippy += ["--fix", "--allow-dirty"]
    clippy += [*flags, "--message-format=short", "--"]
    clippy += [
        "-D",
        "warnings",
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
    ]
    return max(status, show(*exec_external(clippy, project.folder), "sin hallazgos"))


def java_project(project: Project) -> int:
    """Semgrep (p/java + reglas propias) como baseline de seguridad."""
    argv = [
        "semgrep",
        "--config",
        "p/java",
        "--config",
        str(ROOT / ".semgrep" / "rules.yml"),
        "--error",
        "--quiet",
        ".",
    ]
    return show(*exec_external(argv, project.folder), "sin hallazgos")


def python_project(project: Project, fix: bool) -> int:
    """Ruff con el baseline portable."""
    files = relative(project.files, project.folder)
    argv = ["ruff", "check", "--config", str(TOOLS / "python" / "ruff.toml")]
    argv += ["--fix"] if fix else ["--output-format=concise"]
    return show(*exec_external(argv + files, project.folder), "sin hallazgos")


def run_project(project: Project, root: Path, fix: bool) -> int:
    """Corre el baseline que corresponde al tipo de proyecto."""
    rel = project.folder.relative_to(root).as_posix() or "."
    print(f"\n== {project.kind}: {rel} ({len(project.files)} archivo(s)) ==")
    status, size_lines = portable_size(project)
    if size_lines:
        print("\n".join(size_lines))
    for warning in project_warnings(project, root):
        print(f"  aviso: {warning}")

    if project.kind == "node":
        result = node_project(project, fix)
    elif project.kind == "go":
        result = go_project(project, fix)
    elif project.kind == "python":
        result = python_project(project, fix)
    elif project.kind == "rust":
        result = rust_project(project, fix)
    elif project.kind == "godot":
        result = godot_project(project, fix)
    else:
        result = java_project(project)
    return max(status, result)


def portable(path: Path, fix: bool) -> int:
    """Audita un proyecto externo completo."""
    root = path.resolve()
    if not root.is_dir():
        print(f"[X] no existe la carpeta {root}")
        return 2
    projects = discover(root)
    if not projects:
        print(
            f"[X] {root}: no encontre package.json, go.mod, pom.xml, build.gradle, "
            "pyproject.toml, requirements.txt, Cargo.toml ni project.godot"
        )
        print("    Sin manifiesto no hay proyecto que auditar (no es 'todo limpio').")
        return 2

    total = sum(len(project.files) for project in projects)
    print(f"Proyectos detectados: {len(projects)} | archivos: {total}")
    results = [run_project(project, root, fix) for project in projects]
    unverified = results.count(2)

    if 1 in results:
        if unverified:
            print(f"\n{unverified} proyecto(s) sin baseline portable (ver arriba).")
        print("\nHallazgos. Arreglo automatico: --project <ruta> --fix")
        return 1
    if unverified:
        print(f"\nSin hallazgos, pero {unverified} proyecto(s) no se pudieron verificar.")
        return 2
    print("\nTodo limpio.")
    return 0
