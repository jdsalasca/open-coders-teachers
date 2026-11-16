"""Ejecuta el linter de cada lenguaje sobre los archivos indicados.

uso:
  python tools/lint.py             # todo el repo
  python tools/lint.py --fix       # arregla y vuelve a revisar
  python tools/lint.py --fix --unsafe   # incluye arreglos que cambian comportamiento
  python tools/lint.py --staged    # solo lo que esta en el indice (hook)
  python tools/lint.py --audit     # vulnerabilidades en dependencias
  python tools/lint.py --security  # secretos, patrones inseguros y dependencias
  python tools/lint.py --skip "motivo"  # permite el proximo commit sin linters
  python tools/lint.py a.py b.ts   # archivos concretos

Sale 0 si todo pasa, 1 si hay problemas, 2 si falta una herramienta.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL_BIN = "node_modules/.bin"
SKIP_FILE = ROOT / ".git" / "lint-skip"
SKIP_LOG = ROOT / ".git" / "lint-skip.log"
SKIP_TTL = 600  # segundos: un skip viejo no vale
TIMEOUT = 600  # segundos por comando; un linter colgado no bloquea el commit

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# file_exts vacio: el comando corre sobre el modulo completo (golangci-lint,
# mvn). Con file_exts solo recibe archivos de esas extensiones.
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


LANGS = (
    Lang(
        name="python",
        folder="python-teacher",
        exts=(".py",),
        max_file_lines=400,
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
        check=(
            # golangci-lint ya corre gofmt como formatter.
            Command(["golangci-lint", "run", "--output.text.print-issued-lines=false"]),
            Command(
                ["go", "test", "./...", "-coverprofile=coverage.out"],
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
        name="java",
        folder="Java-teacher",
        exts=(".java",),
        check=(
            Command(["mvn", "-q", "-B", "spotless:check"]),
            Command(["mvn", "-q", "-B", "checkstyle:check"]),
            Command(["mvn", "-q", "-B", "pmd:cpd-check"]),
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


def git_files(*args: str) -> list[str]:
    """Lista de archivos que devuelve git, sin vacios."""
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
        return []
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
    return [f for f in out if not SKIP & set(Path(f).parts)]


def candidates(staged: bool) -> list[str]:
    """Archivos a revisar: staged o todos (incluye los no rastreados)."""
    if staged:
        found = git_files("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    else:
        found = git_files("ls-files", "--cached", "--others", "--exclude-standard")
        if not found:
            # Sin git (zip descargado) o repo vacio: recorrer el arbol.
            found = [p.relative_to(ROOT).as_posix() for p in walk_files(ROOT)]
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
    extra = [Path(f).relative_to(lang.folder).as_posix() for f in matching(cmd, files)]
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
    """Corre una herramienta desde la raiz del repo (secretos, semgrep)."""
    exe = shutil.which(argv[0])
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


def skip_warning(reason: str, origin: str) -> None:
    """Aviso no bloqueante cuando se omite el pre-commit a proposito."""
    print(f"\n[AVISO] Pre-commit omitido por {origin}.")
    print(f"  Motivo declarado: {reason}")
    print("  Esto NO es una aprobacion.")
    print("  Pide confirmacion del skip al humano, dile lo que vas a permitir")
    print("  y el porque antes de hacerlo.")


def write_skip(reason: str) -> int:
    """Deja un permiso de un solo uso para el proximo commit."""
    if not (ROOT / ".git").is_dir():
        print("[X] No es un repositorio git.")
        return 2
    SKIP_FILE.write_text(json.dumps({"reason": reason, "created": time.time()}), encoding="utf-8")
    skip_warning(reason, "--skip")
    print("\n  El proximo `git commit` no ejecuta linters (un solo uso, 10 minutos).")
    return 0


def consume_skip() -> bool:
    """Consume el permiso si existe y no caduco. True = commit permitido."""
    if not SKIP_FILE.exists():
        return False
    try:
        data = json.loads(SKIP_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    SKIP_FILE.unlink(missing_ok=True)
    if time.time() - float(data.get("created", 0)) > SKIP_TTL:
        print("\n[AVISO] El skip caduco; se ejecutan los linters igual.")
        return False
    reason = str(data.get("reason", "sin motivo declarado"))
    with SKIP_LOG.open("a", encoding="utf-8") as log:
        log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{reason}\n")
    skip_warning(reason, "--skip")
    print("\n  Commit permitido sin linters. Queda en .git/lint-skip.log")
    return True


def go_cover(cmd: Command, lang: Lang) -> tuple[int | None, str]:
    """Corre las pruebas de Go y exige 50% de cobertura total."""
    code, output = run(cmd, lang, [])
    if code is None or code != 0:
        return code, output
    code, report = run(Command(["go", "tool", "cover", "-func=coverage.out"]), lang, [])
    if code is None or code != 0:
        return code, report
    total = next(
        (
            float(line.split()[-1].rstrip("%"))
            for line in report.splitlines()
            if line.startswith("total:")
        ),
        0.0,
    )
    if total < 50.0:
        return 1, f"{report}\n[!] cobertura total {total:.1f}% < 50%"
    return 0, f"  cobertura Go: {total:.1f}%"


def execute(cmd: Command, lang: Lang, files: list[str]) -> tuple[int | None, str]:
    """Ejecuta un comando de revision, con su parser si lo tiene."""
    if cmd.parser == "go-cover":
        return go_cover(cmd, lang)
    return run(cmd, lang, files)


# Marcadores de código generado sin cuidado. "needs" es la marca de
# justificación que debe seguir a la directiva en la misma línea.
SLOP_RULES = (
    (
        (".ts", ".tsx", ".js", ".jsx"),
        re.compile(r"\b(?:it|test|describe)\.only\s*\("),
        "test enfocado (.only)",
        None,
    ),
    (
        (".ts", ".tsx", ".js", ".jsx"),
        re.compile(r"\b(?:it|test|describe)\.skip\s*\("),
        "test omitido (.skip)",
        None,
    ),
    (
        (".ts", ".tsx", ".js", ".jsx"),
        re.compile(r"\b(?:xit|xdescribe)\s*\("),
        "test omitido (xit/xdescribe)",
        None,
    ),
    (
        (".ts", ".tsx", ".js", ".jsx"),
        re.compile(r"eslint-disable(?:-next-line|-line)?"),
        "eslint-disable",
        "--",
    ),
    (
        (".py",),
        re.compile(r"pytest\.mark\.skip\b(?!if)"),
        "test omitido (pytest.mark.skip)",
        None,
    ),
    ((".py",), re.compile(r"@unittest\.skip\b"), "test omitido (unittest.skip)", None),
    ((".py",), re.compile(r"#\s*noqa"), "noqa", " - "),
    ((".java",), re.compile(r"@Disabled\b"), "test deshabilitado (@Disabled)", None),
    ((".go",), re.compile(r"//\s*nolint"), "nolint", "//"),
)


def slop_check(files: list[str], base: Path = ROOT) -> tuple[int, list[str]]:
    """Busca tests apagados y supresiones sin justificar."""
    status = 0
    lines: list[str] = []
    for name in files:
        suffix = Path(name).suffix
        rules = [
            (pattern, label, needs) for exts, pattern, label, needs in SLOP_RULES if suffix in exts
        ]
        if not rules:
            continue
        try:
            content = (base / name).read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for number, line in enumerate(content, 1):
            for pattern, label, needs in rules:
                match = pattern.search(line)
                if not match:
                    continue
                if needs and needs in line[match.end() :]:
                    continue
                lines.append(f"  {name}:{number}: {label} sin justificar: {line.strip()}")
                status = 1
    return status, lines


def size_check(lang: Lang, files: list[str], base: Path = ROOT) -> tuple[int, list[str]]:
    """Reporta archivos que exceden el maximo de lineas del lenguaje."""
    if not lang.max_file_lines:
        return 0, []
    status = 0
    lines: list[str] = []
    for name in files:
        if Path(name).suffix not in lang.exts:
            continue
        try:
            total = sum(1 for _ in (base / name).open(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if total > lang.max_file_lines:
            lines.append(f"  {name}:1 archivo de {total} lineas (maximo {lang.max_file_lines})")
            status = 1
    return status, lines


def report(
    lang: Lang,
    files: list[str],
    fix: tuple[Command, ...] = (),
    fast: bool = False,
) -> tuple[int, list[str]]:
    """Corre el linter. 0 limpio, 1 problemas, 2 herramienta ausente."""
    lines = [f"== {lang.name} ({len(files)} archivo(s)) =="]
    for cmd in fix:
        run(cmd, lang, files)
    status, size_lines = size_check(lang, files)
    slop_status, slop_lines = slop_check(files)
    status = max(status, slop_status)
    lines.extend(size_lines + slop_lines)
    for cmd in lang.check:
        if fast and not cmd.file_exts:
            continue
        if not should_run(cmd, lang, files):
            continue
        code, output = execute(cmd, lang, files)
        if code is None:
            lines.append(output)
            return 2, lines
        if code != 0:
            status = 1
            if output:
                lines.append(output)
    lines.append("  ok" if status == 0 else "  con problemas")
    return status, lines


AUDIT: dict[str, Command] = {
    "typescript": Command(["npm", "audit", "--audit-level=high"]),
    "react": Command(["npm", "audit", "--audit-level=high"]),
    "go": Command(["govulncheck", "./..."]),
}


def security(langs: list[str]) -> int:
    """Secretos, patrones inseguros y dependencias vulnerables."""
    status = 0

    print("\n== secretos (gitleaks) ==")
    report = Path(tempfile.gettempdir()) / "gitleaks-report.json"
    code, output = root_command(
        [
            "gitleaks",
            "detect",
            "--source",
            ".",
            "--no-git",
            "--redact",
            "--no-banner",
            "-v",
            "--report-format",
            "json",
            "--report-path",
            str(report),
        ]
    )
    if code not in (0, None) and report.exists():
        output = f"{output}\n{report.read_text(encoding='utf-8', errors='replace')}"
    report.unlink(missing_ok=True)
    status = max(status, show(code, output, "sin secretos"))

    print("\n== patrones inseguros (semgrep p/ci) ==")
    code, output = root_command(
        [
            "semgrep",
            "--config",
            "p/ci",
            "--error",
            "--quiet",
            "--exclude",
            "node_modules",
            "--exclude",
            "dist",
            "--exclude",
            "coverage",
            "--exclude",
            "target",
            ".",
        ]
    )
    status = max(status, show(code, output, "sin hallazgos"))

    for name in langs:
        lang = next(lg for lg in LANGS if lg.name == name)
        if name == "go":
            print("\n== gosec (Go) ==")
            cmd = Command(
                [
                    "golangci-lint",
                    "run",
                    "--default=none",
                    "--enable=gosec",
                    "--output.text.print-issued-lines=false",
                ]
            )
            status = max(status, show(*run(cmd, lang, []), "sin hallazgos"))
        elif name == "java":
            print("\n== java: semgrep p/ci + IllegalCatch (sin spotbugs: no lee bytecode 25)")

    return max(status, audit(langs))


def audit(langs: list[str]) -> int:
    """Busca vulnerabilidades conocidas en las dependencias de cada lenguaje."""
    status = 0
    for name in langs:
        lang = next(lg for lg in LANGS if lg.name == name)
        print(f"\n== vulnerabilidades: {name} ==")
        if name == "python":
            req = ROOT / lang.folder / "requirements.txt"
            if not req.exists():
                print("  sin requirements.txt: nada que auditar")
                continue
            code, output = run(Command(["pip-audit", "-r", "requirements.txt"]), lang, [])
        elif name == "java":
            print("  OWASP dependency-check no corre en el hook; usa")
            print("  mvn org.owasp:dependency-check-maven:check")
            continue
        else:
            code, output = run(AUDIT[name], lang, [])
        if code is None:
            print(output)
            return 2
        if code != 0:
            status = 1
            if output:
                print(output)
        else:
            print("  sin vulnerabilidades conocidas")
    return status


def classify(files: list[str]) -> tuple[dict[str, list[str]], list[str]]:
    """Separa por lenguaje y detecta extensiones prohibidas."""
    by_lang: dict[str, list[str]] = {}
    banned: list[str] = []
    for f in files:
        lang = lang_by_folder(f)
        suffix = Path(f).suffix
        if lang and suffix in lang.banned:
            banned.append(f"  {f}: extension prohibida, usa SCSS (.scss)")
        elif lang and suffix in lang.exts:
            by_lang.setdefault(lang.name, []).append(f)
    return by_lang, banned


PROJECTS = (
    ("node", "package.json"),
    ("go", "go.mod"),
    ("java", "pom.xml"),
    ("python", "pyproject.toml"),
)
TOOLS = ROOT / "tools"
NODE_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")


@dataclass(frozen=True)
class Project:
    """Proyecto externo detectado por su manifiesto."""

    kind: str
    folder: Path
    files: list[str]


def walk_files(root: Path):
    """Recorre root sin entrar en directorios generados."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for name in filenames:
            yield Path(dirpath) / name


def owner_of(path: Path, root: Path) -> tuple[str, Path] | None:
    """Manifiesto mas cercano que contiene el archivo."""
    current = path.parent
    while True:
        for kind, manifest in PROJECTS:
            if (current / manifest).is_file():
                return kind, current
        if current == root:
            return None
        current = current.parent


def discover(root: Path) -> list[Project]:
    """Agrupa los archivos por proyecto (manifiesto mas cercano)."""
    groups: dict[tuple[str, Path], list[str]] = {}
    for path in walk_files(root):
        found = owner_of(path, root)
        if found:
            groups.setdefault(found, []).append(path.as_posix())
    return [Project(kind, folder, sorted(files)) for (kind, folder), files in groups.items()]


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


def java_project(project: Project) -> int:
    """Semgrep (p/java) como baseline de seguridad: no requiere Maven."""
    argv = ["semgrep", "--config", "p/java", "--error", "--quiet", "."]
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
    if project.kind == "node":
        return node_project(project, fix)
    if project.kind == "go":
        return go_project(project, fix)
    if project.kind == "python":
        return python_project(project, fix)
    return java_project(project)


def portable(path: Path, fix: bool) -> int:
    """Audita un proyecto externo completo."""
    root = path.resolve()
    if not root.is_dir():
        print(f"[X] no existe la carpeta {root}")
        return 2
    projects = discover(root)
    if not projects:
        print(f"[X] {root}: no encontre package.json, go.mod, pom.xml ni pyproject.toml")
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


def parse_args() -> argparse.Namespace:
    """Lee las banderas de la linea de comandos."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help="archivos concretos (por defecto todo)")
    parser.add_argument(
        "--fast",
        action="store_true",
        help="solo herramientas de archivo (sin tests, tipos ni arquitectura)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="salida JSON para agentes (solo modo normal)",
    )
    parser.add_argument(
        "--unsafe",
        action="store_true",
        help="con --fix: incluye arreglos que pueden cambiar comportamiento",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--staged", action="store_true", help="solo lo que esta en stage")
    group.add_argument("--fix", action="store_true", help="aplica arreglos automaticos")
    group.add_argument(
        "--audit", action="store_true", help="busca vulnerabilidades en dependencias"
    )
    group.add_argument(
        "--security",
        action="store_true",
        help="secretos, patrones inseguros y dependencias",
    )
    parser.add_argument(
        "--project",
        metavar="RUTA",
        help="audita un proyecto externo detectado por manifiesto",
    )
    group.add_argument(
        "--skip",
        nargs="?",
        const="sin motivo declarado",
        metavar="MOTIVO",
        help="permite el proximo commit sin linters (de un solo uso)",
    )
    return parser.parse_args()


def dirty_count() -> int:
    """Cuantos archivos tienen cambios sin commitear."""
    proc = subprocess.run(
        ["git", "status", "--porcelain"],  # noqa: S607 - git esta en el PATH
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return len([line for line in proc.stdout.splitlines() if line.strip()])


def emit_json(status: int, banned: list[str], records: list[dict[str, object]]) -> int:
    """Imprime el resumen estructurado y devuelve el estado."""
    print(
        json.dumps(
            {
                "ok": status == 0,
                "status": status,
                "banned": banned,
                "languages": records,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return status


def finish(status: int) -> int:
    """Mensaje final en texto segun el estado."""
    if status == 2:
        print("\nFalta una herramienta. Instalala y reintenta (ver README).")
        return 2
    if status == 1:
        print("\nProblemas de lint. Arreglo automatico: python tools/lint.py --fix")
        return 1
    print("\nTodo limpio.")
    return 0


def lint_all(args: argparse.Namespace, by_lang: dict[str, list[str]], banned: list[str]) -> int:
    """Corre los linters de cada lenguaje y resume el resultado."""
    before = dirty_count() if (args.fix or args.unsafe) else 0
    status = 1 if banned else 0
    if banned:
        print("\n== estructura ==")
        print("\n".join(banned))

    fixers = args.fix or args.unsafe
    records: list[dict[str, object]] = []
    for lang in LANGS:
        if lang.name not in by_lang:
            continue
        commands = lang.fix_unsafe if args.unsafe else lang.fix
        lang_status, lines = report(lang, by_lang[lang.name], commands if fixers else (), args.fast)
        status = max(status, lang_status)
        records.append(
            {
                "name": lang.name,
                "files": len(by_lang[lang.name]),
                "status": lang_status,
                "output": lines,
            }
        )
        if not args.json:
            print("\n".join(lines))

    if fixers and not args.json:
        print(f"\nArreglos automaticos: {dirty_count() - before} archivo(s) modificado(s).")

    if args.json:
        return emit_json(status, banned, records)
    return finish(status)


def is_inside(path: Path) -> bool:
    """True si la ruta esta dentro de este repo."""
    try:
        path.resolve().relative_to(ROOT)
        return True
    except ValueError:
        return False


def external_target(files: list[str]) -> Path | None:
    """Ruta externa unica, si el usuario apunto a otro proyecto."""
    if not files:
        return None
    first = Path(files[0])
    candidate = first.resolve() if first.is_absolute() else (ROOT / first).resolve()
    if is_inside(candidate):
        return None
    return candidate


def external_mode(args: argparse.Namespace) -> int | None:
    """Corre el modo portable si la ruta apunta fuera del repo."""
    target = external_target(args.files)
    if target is None:
        return None
    if len(args.files) == 1 and target.is_dir():
        return portable(target, args.fix or args.unsafe)
    print("[X] ruta fuera del repo: usa --project <carpeta>")
    return 2


def repo_mode(args: argparse.Namespace) -> int:
    """Modo repo: las cinco carpetas de este proyecto."""
    files = expand(args.files) if args.files else candidates(args.staged)
    by_lang, banned = classify(files)
    everything = [lang.name for lang in LANGS]
    if args.audit:
        return audit(sorted(by_lang) or everything)
    if args.security:
        return security(sorted(by_lang) or everything)
    if not by_lang and not banned:
        if args.json:
            print(
                json.dumps(
                    {"ok": True, "status": 0, "banned": [], "languages": []},
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print("Nada que revisar.")
            if args.files:
                print("Si es un proyecto externo, usa: --project <ruta>")
        return 2 if args.files else 0
    return lint_all(args, by_lang, banned)


def validate(args: argparse.Namespace) -> str | None:
    """Errores de combinacion de banderas, o None si todo esta bien."""
    if args.unsafe and not args.fix:
        return "--unsafe solo tiene sentido junto a --fix"
    if args.project and (args.audit or args.security):
        return "--project no se combina con --audit ni --security"
    if args.fast and (args.audit or args.security or args.project or args.skip is not None):
        return "--fast solo aplica al modo normal (sin --audit, --security, --project ni --skip)"
    if args.json and (args.audit or args.security or args.project or args.skip is not None):
        return "--json solo aplica al modo normal (sin --audit, --security, --project ni --skip)"
    return None


def main() -> int:
    """Punto de entrada: decide el modo y delega."""
    args = parse_args()
    error = validate(args)
    if error:
        print(f"[X] {error}")
        return 2
    if args.skip is not None:
        return write_skip(args.skip)
    if args.staged and consume_skip():
        return 0
    if args.project:
        return portable(Path(args.project), args.fix or args.unsafe)
    external = external_mode(args)
    if external is not None:
        return external
    return repo_mode(args)


if __name__ == "__main__":
    raise SystemExit(main())
