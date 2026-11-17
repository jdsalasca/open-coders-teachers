"""Utilidades compartidas por el runner (sin dependencias del CLI)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

LOCAL_BIN = "node_modules/.bin"

SKIP_FILE = ROOT / ".git" / "lint-skip"

SKIP_LOG = ROOT / ".git" / "lint-skip.log"

SKIP_TTL = 600  # segundos: un skip viejo no vale

TIMEOUT = 600  # segundos por comando; un linter colgado no bloquea el commit


@dataclass(frozen=True)
class Command:
    """Un comando del linter y las extensiones que le corresponden.

    file_exts: se le pasan los archivos del lote con esas extensiones.
    needs: solo se ejecuta si el lote trae alguna de esas extensiones.
    requires: ruta que debe existir dentro de la carpeta del lenguaje.
    parser: post-proceso del resultado ("go-cover" exige cobertura minima).
    """

    argv: list[str]
    file_exts: tuple[str, ...] = ()
    needs: tuple[str, ...] = ()
    requires: str = ""
    parser: str = ""
    takes_files: bool = True


@dataclass(frozen=True)
class Lang:
    """Lenguaje, carpeta del repo, comandos y extensiones prohibidas."""

    name: str
    folder: str
    exts: tuple[str, ...]
    check: tuple[Command, ...]
    fix: tuple[Command, ...]
    fix_unsafe: tuple[Command, ...] = ()
    banned: tuple[str, ...] = ()
    max_file_lines: int = 0
    test_glob: str = ""


GO_RACE = () if sys.platform == "win32" else ("-race",)

LANGS = (
    Lang(
        name="python",
        folder="python-teacher",
        exts=(".py",),
        max_file_lines=400,
        test_glob="test_*.py",
        check=(
            Command(["ruff", "check", "--output-format=concise"], (".py",)),
            Command(["ruff", "format", "--check"], (".py",)),
            Command(["mypy", "."]),
            Command(["lint-imports"]),
            Command(
                [
                    "pytest",
                    "--cov=app",
                    "--cov-report=term-missing",
                    "--cov-report=xml",
                    "--cov-fail-under=60",
                ],
                requires="tests",
            ),
        ),
        fix=(
            Command(["ruff", "check", "--fix"], (".py",)),
            Command(["ruff", "format"], (".py",)),
        ),
        fix_unsafe=(
            Command(["ruff", "check", "--fix", "--unsafe-fixes"], (".py",)),
            Command(["ruff", "format"], (".py",)),
        ),
    ),
    Lang(
        name="typescript",
        folder="typescript-teacher",
        exts=(".ts", ".tsx", ".js", ".jsx"),
        test_glob="*.test.ts",
        check=(
            Command(["eslint", "--format=unix"], (".ts", ".tsx", ".js", ".jsx")),
            Command(["prettier", "--check"], (".ts", ".tsx", ".js", ".jsx", ".json", ".md")),
            Command(["tsc", "--noEmit"], needs=(".ts", ".tsx")),
            Command(["depcruise", "src", "--config", ".dependency-cruiser.js"]),
            Command(["vitest", "run", "--coverage"], requires="vitest.config.ts"),
            Command(["jscpd", "src"], requires=".jscpd.json"),
        ),
        fix=(
            Command(["eslint", "--fix"], (".ts", ".tsx", ".js", ".jsx")),
            Command(["prettier", "--write"], (".ts", ".tsx", ".js", ".jsx", ".json", ".md")),
        ),
    ),
    Lang(
        name="react",
        folder="React-teacher",
        exts=(".ts", ".tsx", ".js", ".jsx", ".scss"),
        banned=(".css",),
        test_glob="*.test.ts*",
        check=(
            Command(["eslint", "--format=unix"], (".ts", ".tsx", ".js", ".jsx")),
            Command(["stylelint"], (".scss",)),
            Command(["tsc", "--noEmit"], needs=(".ts", ".tsx")),
            Command(["knip", "--no-config-hints"]),
            Command(["depcruise", "src", "--config", ".dependency-cruiser.js"]),
            Command(["vitest", "run", "--coverage"], requires="vitest.config.ts"),
            Command(["jscpd", "src"], requires=".jscpd.json"),
            Command(
                ["prettier", "--check"],
                (".ts", ".tsx", ".js", ".jsx", ".scss", ".json", ".html"),
            ),
        ),
        fix=(
            Command(["eslint", "--fix"], (".ts", ".tsx", ".js", ".jsx")),
            Command(["stylelint", "--fix"], (".scss",)),
            Command(
                ["prettier", "--write"],
                (".ts", ".tsx", ".js", ".jsx", ".scss", ".json", ".html"),
            ),
        ),
    ),
    Lang(
        name="go",
        folder="go-teacher",
        exts=(".go",),
        max_file_lines=500,
        test_glob="*_test.go",
        check=(
            # golangci-lint ya corre gofmt como formatter.
            Command(["golangci-lint", "run", "--output.text.print-issued-lines=false"]),
            Command(
                [
                    "go",
                    "test",
                    *GO_RACE,
                    "-shuffle=on",
                    "./...",
                    "-coverpkg=./internal/...",
                    "-coverprofile=coverage.out",
                ],
                requires="go.mod",
                parser="go-cover",
            ),
        ),
        fix=(
            Command(["gofmt", "-w"], (".go",)),
            Command(["golangci-lint", "fmt"], requires="go.mod"),
            Command(["golangci-lint", "run", "--fix"]),
        ),
    ),
    Lang(
        name="rust",
        folder="Rust-teacher",
        exts=(".rs",),
        max_file_lines=400,
        test_glob="tests/*.rs",
        check=(
            Command(["cargo", "fmt", "--check"], (".rs",), takes_files=False),
            Command(
                [
                    "cargo",
                    "clippy",
                    "--all-targets",
                    "--all-features",
                    "--",
                    "-D",
                    "warnings",
                ],
                (".rs",),
                takes_files=False,
            ),
            Command(
                [
                    "cargo",
                    "llvm-cov",
                    "--fail-under-lines",
                    "60",
                    "--summary-only",
                    "--lcov",
                    "--output-path",
                    "target/lcov.info",
                ],
                needs=(".rs",),
                requires="Cargo.toml",
            ),
        ),
        fix=(Command(["cargo", "fmt"]),),
        fix_unsafe=(
            Command(["cargo", "fmt"]),
            Command(
                [
                    "cargo",
                    "clippy",
                    "--fix",
                    "--all-targets",
                    "--allow-dirty",
                    "--allow-staged",
                ]
            ),
        ),
    ),
    Lang(
        name="java",
        folder="Java-teacher",
        exts=(".java",),
        test_glob="*Test.java",
        check=(
            Command(["mvn", "-q", "-B", "spotless:check"]),
            Command(["mvn", "-q", "-B", "checkstyle:check"]),
            Command(["mvn", "-q", "-B", "pmd:cpd-check"]),
            Command(["mvn", "-q", "-B", "pmd:check"]),
            Command(["mvn", "-q", "-B", "spotbugs:check"]),
            Command(["mvn", "-q", "-B", "test"]),
        ),
        fix=(Command(["mvn", "-q", "-B", "spotless:apply"]),),
    ),
)


def lang_by_folder(rel_path: str) -> Lang | None:
    """Lenguaje cuya carpeta contiene el archivo."""
    parts = Path(rel_path).parts
    if not parts:
        return None
    return next((lang for lang in LANGS if parts[0] == lang.folder), None)


def lang_for(rel_path: str) -> str | None:
    """Devuelve el lenguaje segun la carpeta y la extension del archivo."""
    lang = lang_by_folder(rel_path)
    if lang and Path(rel_path).suffix in lang.exts:
        return lang.name
    return None


def git_files(*args: str) -> list[str] | None:
    """Lista de archivos que devuelve git; None si git falla."""
    try:
        out = subprocess.run(  # noqa: S603 - argumentos fijos, sin shell
            ["git", *args, "-z"],  # noqa: S607 - git esta en el PATH
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        return None
    return [p for p in out.stdout.split("\0") if p]


SKIP = {
    "node_modules",
    ".git",
    "dist",
    "target",
    ".venv",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    "coverage",
    ".jscpd",
    ".next",
    ".nuxt",
    ".svelte-kit",
    ".godot",
    "jdk",
    ".toolchains",
    "vendor",
    "third_party",
    "third-party",
    "venv",
    "env",
    "site-packages",
    ".tox",
    ".nox",
    ".eggs",
    ".cache",
    ".parcel-cache",
    ".turbo",
    ".tmp",
}


def expand(files: list[str]) -> list[str]:
    """Convierte carpetas en sus archivos y descarta directorios generados."""
    out: list[str] = []
    for f in files:
        path = ROOT / f
        if path.is_dir():
            out.extend(x.relative_to(ROOT).as_posix() for x in path.rglob("*") if x.is_file())
        else:
            out.append(f)
    return [f.replace("\\", "/") for f in out if not SKIP & set(Path(f).parts)]


def staged_deleted() -> list[str] | None:
    """Rutas borradas en el indice; None si git falla."""
    return git_files("diff", "--cached", "--name-only", "--diff-filter=D")


def languages_of(paths: list[str]) -> set[str]:
    """Lenguajes afectados por una lista de rutas."""
    names = set()
    for path in paths:
        lang = lang_by_folder(path)
        if lang and Path(path).suffix in lang.exts:
            names.add(lang.name)
    return names


def candidates(staged: bool) -> list[str] | None:
    """Archivos a revisar: staged o todos; None si git no responde."""
    if staged:
        found = git_files("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    else:
        found = git_files("ls-files", "--cached", "--others", "--exclude-standard")
        if found == []:
            # Sin git (zip descargado) o repo vacio: recorrer el arbol.
            found = [p.relative_to(ROOT).as_posix() for p in walk_files(ROOT)]
    if found is None:
        return None
    # Un archivo borrado sigue en el indice hasta el commit: no se puede lintar.
    return [f for f in found if (ROOT / f).exists()]


def should_run(cmd: Command, lang: Lang, files: list[str]) -> bool:
    """False si el lote o la carpeta no cumplen los requisitos del comando."""
    if cmd.requires and not (ROOT / lang.folder / cmd.requires).exists():
        return False
    gate = cmd.needs or cmd.file_exts
    return not gate or any(Path(f).suffix in gate for f in files)


def matching(cmd: Command, files: list[str]) -> list[str]:
    """Archivos del lote que le corresponden a este comando."""
    return [f for f in files if Path(f).suffix in cmd.file_exts]


def run(cmd: Command, lang: Lang, files: list[str]) -> tuple[int | None, str]:
    """Ejecuta un comando en la carpeta del lenguaje y filtra ruido.

    Devuelve None como codigo si la herramienta no esta instalada.
    """
    local_bin = ROOT / lang.folder / LOCAL_BIN
    exe = shutil.which(cmd.argv[0], path=str(local_bin)) or shutil.which(cmd.argv[0])
    if exe is None:
        return None, f"[X] falta '{cmd.argv[0]}' (ver README)"
    extra = (
        [Path(f).relative_to(lang.folder).as_posix() for f in matching(cmd, files)]
        if cmd.takes_files
        else []
    )
    try:
        proc = subprocess.run(  # noqa: S603 - lista de argumentos, sin shell
            [exe, *cmd.argv[1:], *extra],
            cwd=ROOT / lang.folder,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return 1, f"[X] '{cmd.argv[0]}' excedio {TIMEOUT}s"
    prefix = str(ROOT / lang.folder)
    output = clean(proc.stdout + proc.stderr)
    return proc.returncode, output.replace(prefix + "\\", "").replace(prefix + "/", "")


def clean(text: str) -> str:
    """Quita el ruido de Maven y las lineas vacias del reporte."""
    dropped = (
        "WARNING:",
        "Re-run Maven",
        "For more information",
        "To see the full stack",
        "-> [Help 1]",
        "Help 1]",
    )
    kept = []
    for raw in text.splitlines():
        line = raw.removeprefix("[ERROR] ")
        if not line.strip() or line.strip().startswith(dropped):
            continue
        if "maven.apache.org" in line:
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def root_command(argv: list[str]) -> tuple[int | None, str]:
    """Corre una herramienta desde la raiz del repo (secretos, docs)."""
    local_bin = ROOT / "tools" / "node" / "node_modules" / ".bin"
    exe = shutil.which(argv[0], path=str(local_bin)) or shutil.which(argv[0])
    if exe is None:
        return None, f"[X] falta '{argv[0]}' (ver README)"
    try:
        proc = subprocess.run(  # noqa: S603 - lista de argumentos, sin shell
            [exe, *argv[1:]],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return 1, f"[X] '{argv[0]}' excedio {TIMEOUT}s"
    output = clean(proc.stdout + proc.stderr)
    return proc.returncode, output


def show(code: int | None, output: str, ok: str) -> int:
    """Traduce el resultado de una herramienta a codigo de estado."""
    if code is None:
        print(output)
        return 2
    if code != 0:
        print(output)
        return 1
    print(f"  {ok}")
    return 0


def walk_files(root: Path) -> Iterator[Path]:
    """Recorre root sin entrar en directorios generados."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for name in filenames:
            yield Path(dirpath) / name


TOOLS = ROOT / "tools"

NODE_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")


def portable_bin(name: str) -> str | None:
    """Binario del baseline portable (tools/node) o del PATH."""
    local = TOOLS / "node" / "node_modules" / ".bin"
    return shutil.which(name, path=str(local)) or shutil.which(name)


def exec_external(argv: list[str], cwd: Path) -> tuple[int | None, str]:
    """Ejecuta una herramienta externa en la carpeta del proyecto."""
    exe = portable_bin(argv[0])
    if exe is None:
        return None, f"[X] falta '{argv[0]}' (instala tools/node: npm install)"
    try:
        proc = subprocess.run(  # noqa: S603 - argumentos fijos, sin shell
            [exe, *argv[1:]],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return 1, f"[X] '{argv[0]}' excedio {TIMEOUT}s"
    output = clean(proc.stdout + proc.stderr)
    return proc.returncode, output.replace(str(cwd) + os.sep, "").replace(str(cwd) + "/", "")


def relative(files: list[str], folder: Path) -> list[str]:
    """Rutas relativas al proyecto para pasarlas como argumentos."""
    return [Path(f).relative_to(folder).as_posix() for f in files]
