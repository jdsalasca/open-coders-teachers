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
import tomllib
import urllib.request
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


# -race requiere cgo; el runner no asume gcc en Windows.
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
                ["cargo", "llvm-cov", "--fail-under-lines", "60", "--summary-only"],
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
    run(
        Command(["go", "tool", "cover", "-html=coverage.out", "-o", "coverage.html"]),
        lang,
        [],
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
    (
        (".ts", ".tsx", ".js", ".jsx"),
        re.compile(
            r"^\s*//\s*(?:const|let|var|function|class|if|for|while|return|import|export)\b"
        ),
        "codigo comentado",
        None,
    ),
    (
        (".py",),
        re.compile(r"^\s*#\s*(?:def|class|import|from|return|if|for|while)\b"),
        "codigo comentado",
        None,
    ),
    (
        (".tsx",),
        re.compile(r"#[0-9a-fA-F]{3,8}\b"),
        "color hex en TSX (usa tokens SCSS)",
        None,
    ),
    ((".java",), re.compile(r"@Disabled\b"), "test deshabilitado (@Disabled)", None),
    ((".go",), re.compile(r"//\s*nolint"), "nolint", "//"),
    ((".rs",), re.compile(r"#\[allow\("), "allow sin justificar", "reason"),
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
    report = Path(tempfile.gettempdir()) / f"gitleaks-{os.getpid()}.json"
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
            "--config",
            ".semgrep/rules.yml",
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
            "--exclude",
            "tools/fixtures",
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


MUTATION: dict[str, Command] = {
    "java": Command(
        ["mvn", "-q", "-B", "test-compile", "pitest:mutationCoverage"],
        requires="pom.xml",
    ),
    "react": Command(["stryker", "run"], requires="stryker.conf.json"),
    "typescript": Command(["stryker", "run"], requires="stryker.conf.json"),
}


def mutation(langs: list[str]) -> int:
    """Mutation testing: mide si los tests detectan cambios en el codigo."""
    status = 0
    ran = 0
    for name in langs:
        cmd = MUTATION.get(name)
        if cmd is None:
            continue
        lang = next(lg for lg in LANGS if lg.name == name)
        ran += 1
        print(f"\n== mutacion: {name} ==")
        status = max(status, show(*run(cmd, lang, []), "mutantes cazados"))
    if not ran:
        print("Sin mutation testing configurado para el lote.")
        print("Configurados: react y typescript (stryker.conf.json).")
        return 2
    return status


def repo_slug() -> str | None:
    """owner/repo del remoto de GitHub, si existe."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],  # noqa: S607 - git en el PATH
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", result.stdout.strip())
    return match.group(1) if match else None


def parse_alerts(raw: str) -> list[dict] | None:
    """Aplana las paginas de gh --slurp; None si la respuesta no es JSON."""
    try:
        pages = json.loads(raw or "[]")
    except ValueError:
        return None
    if pages and isinstance(pages[0], list):
        return [alert for page in pages for alert in page]
    return pages


OSV_URL = "https://api.osv.dev/v1/querybatch"
MAVEN_TYPES = {"jar", "war", "pom", "ejb", "ejb-client", "test-jar", "maven-plugin"}


def parse_maven_dependencies(text: str) -> list[tuple[str, str]]:
    """Extrae (group:artifact, version) del listado de Maven."""
    packages = []
    for raw in text.splitlines():
        parts = raw.strip().split(" -- ")[0].split(":")
        if len(parts) >= 4 and parts[2] in MAVEN_TYPES and parts[3]:
            packages.append((f"{parts[0]}:{parts[1]}", parts[3]))
    return sorted(set(packages))


def maven_packages() -> list[tuple[str, str]] | None:
    """Dependencias de Java-teacher (test incluye compile y runtime)."""
    exe = shutil.which("mvn")
    if exe is None:
        return None
    output = ROOT / "Java-teacher" / "target" / "dependencies.txt"
    try:
        proc = subprocess.run(  # noqa: S603 - executable resuelto con shutil.which
            [
                exe,
                "-q",
                "-B",
                "dependency:list",
                "-DincludeScope=test",
                f"-DoutputFile={output}",
            ],
            cwd=ROOT / "Java-teacher",
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0 or not output.exists():
        return None
    return parse_maven_dependencies(output.read_text(encoding="utf-8"))


def cargo_packages() -> list[tuple[str, str]] | None:
    """Dependencias de Cargo.lock; None si no existe o no parsea."""
    lock = ROOT / "Rust-teacher" / "Cargo.lock"
    if not lock.exists():
        return None
    try:
        return parse_cargo_lock(lock.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None


def parse_cargo_lock(text: str) -> list[tuple[str, str]]:
    """Extrae (crate, version) de Cargo.lock, solo de crates.io."""
    data = tomllib.loads(text)
    packages = [
        (package["name"], package["version"])
        for package in data.get("package", [])
        if str(package.get("source", "")).startswith("registry+")
    ]
    return sorted(set(packages))


def osv_queries(packages: list[tuple[str, str]], ecosystem: str = "Maven") -> dict[str, object]:
    """Cuerpo de la consulta batch a OSV."""
    return {
        "queries": [
            {"package": {"name": name, "ecosystem": ecosystem}, "version": version}
            for name, version in packages
        ]
    }


def parse_osv_response(packages: list[tuple[str, str]], data: object) -> list[str] | None:
    """Convierte una respuesta batch de OSV; None si esta incompleta."""
    if not isinstance(data, dict):
        return None
    results = data.get("results")
    if not isinstance(results, list) or len(results) != len(packages):
        return None
    rows = []
    for (name, version), result in zip(packages, results, strict=True):
        if not isinstance(result, dict):
            return None
        vulns = result.get("vulns", [])
        if not isinstance(vulns, list):
            return None
        for vuln in vulns:
            if not isinstance(vuln, dict):
                return None
            rows.append(f"  {name}@{version}: {vuln.get('id', '?')}")
    return rows


def osv_vulnerabilities(
    packages: list[tuple[str, str]], ecosystem: str = "Maven"
) -> list[str] | None:
    """Vulnerabilidades conocidas por OSV; None si no hay respuesta."""
    request = urllib.request.Request(
        OSV_URL,
        data=json.dumps(osv_queries(packages, ecosystem)).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:  # noqa: S310 - URL https fija
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    return parse_osv_response(packages, data)


def dependabot_alerts() -> tuple[int | None, str]:
    """Alertas abiertas de Maven via Dependabot, con paginacion."""
    slug = repo_slug()
    if slug is None:
        return 2, "[X] no encontre un remoto de GitHub para consultar alertas"
    try:
        result = subprocess.run(  # noqa: S603 - argumentos fijos
            [  # noqa: S607 - gh en el PATH
                "gh",
                "api",
                "--paginate",
                "--slurp",
                f"repos/{slug}/dependabot/alerts?state=open&per_page=100",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, "[X] falta gh (GitHub CLI) o no respondio"
    if result.returncode != 0:
        message = result.stderr.strip()
        if "Resource not accessible" in message or "HTTP 403" in message:
            return 2, "[X] el token no puede leer alertas: verificacion incompleta"
        return 1, f"[X] gh no pudo consultar alertas: {message}"
    alerts = parse_alerts(result.stdout)
    if alerts is None:
        return 1, "[X] respuesta inesperada de gh"
    # Node/Go/Python ya se auditan con sus herramientas; Dependabot cubre Maven.
    maven = [
        alert
        for alert in alerts
        if str(alert.get("dependency", {}).get("manifest_path", "")).endswith("pom.xml")
    ]
    lines = [
        "  {} [{}] {}".format(
            alert.get("dependency", {}).get("package", {}).get("name", "?"),
            alert.get("security_advisory", {}).get("severity", "?"),
            alert.get("dependency", {}).get("manifest_path", ""),
        )
        for alert in maven
    ]
    return (1, "\n".join(lines)) if lines else (0, "")


def audit_maven() -> int:
    """Dependabot para Maven: complemento de OSV, no su sustituto."""
    print("\n== dependencias Java (Dependabot) ==")
    if os.environ.get("LINT_SKIP_DEPENDABOT") == "1":
        print("  omitido: el token de CI no lee alertas Dependabot (OSV ya audita Maven)")
        return 0
    code, output = dependabot_alerts()
    if code == 0 and output.strip():
        print(output)
        return 0
    return show(code, output, "sin alertas abiertas")


def audit_osv(packages: list[tuple[str, str]] | None, ecosystem: str, source: str) -> int:
    """Audita paquetes con OSV; 2 si no se pudo verificar."""
    if packages is None:
        print(f"  [X] no pude leer {source}: verificacion incompleta")
        return 2
    rows = osv_vulnerabilities(packages, ecosystem)
    if rows is None:
        print("  [X] OSV no respondio: verificacion incompleta")
        return 2
    if rows:
        print("\n".join(rows))
        return 1
    print(f"  sin vulnerabilidades conocidas (OSV, {len(packages)} deps)")
    return 0


def audit_java(_lang: Lang) -> int:
    """Dependencias Maven via OSV."""
    return audit_osv(maven_packages(), "Maven", "las dependencias Maven")


def audit_rust(_lang: Lang) -> int:
    """Dependencias de crates.io via OSV."""
    return audit_osv(cargo_packages(), "crates.io", "Cargo.lock")


def audit_python(lang: Lang) -> int:
    """Dependencias Python con pip-audit; sin requirements no hay nada que ver."""
    req = ROOT / lang.folder / "requirements.txt"
    if not req.exists():
        print("  sin requirements.txt: nada que auditar")
        return 0
    return audit_command(Command(["pip-audit", "-r", "requirements.txt"]), lang)


def audit_command(cmd: Command, lang: Lang) -> int:
    """Corre un scanner de dependencias y traduce su estado."""
    code, output = run(cmd, lang, [])
    if code is None:
        print(output)
        return 2
    if code != 0:
        if output:
            print(output)
        return 1
    print("  sin vulnerabilidades conocidas")
    return 0


AUDIT_HANDLERS = {
    "java": audit_java,
    "python": audit_python,
    "rust": audit_rust,
}


def audit(langs: list[str]) -> int:
    """Busca vulnerabilidades conocidas en las dependencias de cada lenguaje."""
    status = 0
    for name in langs:
        lang = next(lg for lg in LANGS if lg.name == name)
        print(f"\n== vulnerabilidades: {name} ==")
        handler = AUDIT_HANDLERS.get(name)
        if handler is not None:
            status = max(status, handler(lang))
        else:
            status = max(status, audit_command(AUDIT[name], lang))

    print("\n== vulnerabilidades: tools/node ==")
    code, output = root_command(["npm", "audit", "--prefix", "tools/node", "--audit-level=high"])
    status = max(status, show(code, output, "sin vulnerabilidades conocidas"))

    return max(status, audit_maven())


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
    ("rust", "Cargo.toml"),
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


def rust_project(project: Project, fix: bool) -> int:
    """Formatea y lintea con el baseline portable (sin tests)."""
    fmt = ["cargo", "fmt"] if fix else ["cargo", "fmt", "--check"]
    status = show(*exec_external(fmt, project.folder), "sin hallazgos")
    clippy = ["cargo", "clippy", "--all-targets", "--", "-D", "warnings"]
    if fix:
        clippy = ["cargo", "clippy", "--fix", "--all-targets", "--allow-dirty"]
    return max(status, show(*exec_external(clippy, project.folder), "sin hallazgos"))


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
    if project.kind == "rust":
        return rust_project(project, fix)
    return java_project(project)


def portable(path: Path, fix: bool) -> int:
    """Audita un proyecto externo completo."""
    root = path.resolve()
    if not root.is_dir():
        print(f"[X] no existe la carpeta {root}")
        return 2
    projects = discover(root)
    if not projects:
        print(
            f"[X] {root}: no encontre package.json, go.mod, pom.xml, pyproject.toml ni Cargo.toml"
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
    group.add_argument("--mutation", action="store_true", help="mutation testing (Stryker)")
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


def lint_all(
    args: argparse.Namespace,
    by_lang: dict[str, list[str]],
    banned: list[str],
    files: list[str],
) -> int:
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

    repo_status, repo_lines = repo_checks(files, fixers)
    status = max(status, repo_status)
    records.append(
        {
            "name": "repo",
            "files": len(files),
            "status": repo_status,
            "output": repo_lines,
        }
    )
    if not args.json:
        print("\n" + "\n".join(repo_lines))

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


def staged_lines() -> int:
    """Lineas cambiadas en el indice (suma de altas y bajas)."""
    try:
        out = subprocess.run(
            ["git", "diff", "--cached", "--numstat"],  # noqa: S607 - git en el PATH
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
        return 0
    total = 0
    for line in out.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            total += int(parts[0]) + int(parts[1])
    return total


def special_mode(args: argparse.Namespace, by_lang: dict[str, list[str]]) -> int | None:
    """Modos globales que no dependen del lote de archivos."""
    if not (args.audit or args.security or args.mutation):
        return None
    langs = sorted(by_lang) or [lang.name for lang in LANGS]
    if args.audit:
        return audit(langs)
    if args.security:
        return security(langs)
    return mutation(langs)


def repo_checks(files: list[str], fix: bool = False) -> tuple[int, list[str]]:
    """Docs (markdownlint + enlaces) y nombres de archivo (ls-lint)."""
    lines = ["== repo =="]
    status = 0
    md = [f for f in files if f.endswith(".md")]

    checks: list[tuple[str, list[str]]] = []
    if any(f.startswith("tools/") and f.endswith(".py") for f in files):
        checks.append(("autochequeo (test_lint)", ["python", "tools/test_lint.py"]))
    if md:
        markdown = ["markdownlint", *md, "--config", ".markdownlint.json"]
        checks.append(("docs (markdownlint)", markdown + (["--fix"] if fix else [])))
        checks.append(("docs (enlaces)", ["python", "tools/check_links.py", *md]))
    policy_exts = (".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".java", ".rs")
    policy = [
        f for f in files if Path(f).suffix in policy_exts and not f.startswith("tools/fixtures/")
    ]
    if policy:
        checks.append(
            (
                "politica (semgrep)",
                [
                    "semgrep",
                    "--config",
                    ".semgrep/rules.yml",
                    "--error",
                    "--quiet",
                    *policy,
                ],
            )
        )
    checks.append(("nombres (ls-lint)", ["ls-lint"]))

    for label, argv in checks:
        code, output = root_command(argv)
        if code is None:
            lines.append(output)
            return 2, lines
        if code != 0:
            status = 1
            lines.append(f"  [X] {label}")
            if output:
                lines.append(output)
        else:
            lines.append(f"  ok: {label}")
    return status, lines


# Un cambio de configuracion debe disparar el gate completo del proyecto.
CONFIG_LANGS = {
    "python-teacher/pyproject.toml": "python",
    "python-teacher/requirements.txt": "python",
    "typescript-teacher/package.json": "typescript",
    "typescript-teacher/tsconfig.json": "typescript",
    "typescript-teacher/eslint.config.js": "typescript",
    "typescript-teacher/vitest.config.ts": "typescript",
    "typescript-teacher/.jscpd.json": "typescript",
    "typescript-teacher/.prettierrc.json": "typescript",
    "typescript-teacher/stryker.conf.json": "typescript",
    "React-teacher/package.json": "react",
    "React-teacher/tsconfig.json": "react",
    "React-teacher/eslint.config.js": "react",
    "React-teacher/stylelint.config.js": "react",
    "React-teacher/knip.json": "react",
    "React-teacher/vitest.config.ts": "react",
    "React-teacher/.jscpd.json": "react",
    "React-teacher/stryker.conf.json": "react",
    "React-teacher/playwright.config.ts": "react",
    "typescript-teacher/package-lock.json": "typescript",
    "typescript-teacher/.dependency-cruiser.js": "typescript",
    "React-teacher/package-lock.json": "react",
    "React-teacher/.dependency-cruiser.js": "react",
    "React-teacher/.prettierrc.json": "react",
    "go-teacher/.golangci.yml": "go",
    "go-teacher/go.mod": "go",
    "Java-teacher/pom.xml": "java",
    "Java-teacher/config/checkstyle/checkstyle.xml": "java",
    "Java-teacher/config/pmd/ruleset.xml": "java",
    "Rust-teacher/Cargo.toml": "rust",
    "Rust-teacher/Cargo.lock": "rust",
    "Rust-teacher/clippy.toml": "rust",
    "Rust-teacher/rust-toolchain.toml": "rust",
    "Rust-teacher/rustfmt.toml": "rust",
    # Afectan a todo el repo o al propio gate: corren las cinco carpetas.
    ".semgrep/rules.yml": "*",
    ".markdownlint.json": "*",
    ".ls-lint.yml": "*",
    ".github/workflows/ci.yml": "*",
    ".github/workflows/mutation.yml": "*",
    "tools/lint.py": "*",
    "tools/test_lint.py": "*",
    "tools/check_links.py": "*",
    "tools/check_adr.py": "*",
}


def staged_guard(files: list[str]) -> int | None:
    """Avisa del tamano y rechaza staging parcial o git roto."""
    changed = staged_lines()
    if changed > 400:
        print(f"[aviso] commit grande: {changed} lineas cambiadas. Considera partirlo.")
    unstaged = git_files("diff", "--name-only")
    if unstaged is None:
        print("[X] git no respondio al comparar el indice con el arbol.")
        return 2
    mixed = sorted(set(files) & set(unstaged))
    if not mixed:
        return None
    print("[X] archivos staged con cambios sin stagear:")
    for name in mixed:
        print(f"    {name}")
    print("    El lint mira el arbol de trabajo; stagea todo o separa el cambio.")
    return 2


def add_config_langs(files: list[str], by_lang: dict[str, list[str]]) -> bool:
    """Un cambio de configuracion dispara el gate completo de su lenguaje.

    Devuelve True si hubo configuracion en el lote, aunque ya hubiera archivos
    de ese lenguaje: un config staged con codigo no debe saltarse el gate.
    """
    changed = [path for path in files if path in CONFIG_LANGS]
    if not changed:
        return False
    everything = candidates(False) or []
    for path in changed:
        language = CONFIG_LANGS[path]
        names = [lang.name for lang in LANGS] if language == "*" else [language]
        for name in names:
            lang = next(lg for lg in LANGS if lg.name == name)
            project = [
                f
                for f in everything
                if f.startswith(lang.folder + "/") and Path(f).suffix in lang.exts
            ]
            by_lang[name] = project or by_lang.get(name, [path])
    return True


def missing_tests() -> list[str]:
    """Cada lenguaje del repo debe conservar al menos un test."""
    missing = []
    for lang in LANGS:
        if not lang.test_glob:
            continue
        if not any((ROOT / lang.folder).rglob(lang.test_glob)):
            missing.append(f"  {lang.folder}: no encontre {lang.test_glob}")
    return missing


def empty_result(args: argparse.Namespace) -> int:
    """Sin lenguajes ni docs: explica el caso y devuelve el estado."""
    if args.json:
        print(
            json.dumps(
                {"ok": True, "status": 0, "banned": [], "languages": []},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    print("Nada que revisar.")
    if args.files:
        print("Si es un proyecto externo, usa: --project <ruta>")
        return 2
    return 0


def repo_mode(args: argparse.Namespace) -> int:
    """Modo repo: las cinco carpetas de este proyecto."""
    files = expand(args.files) if args.files else candidates(args.staged)
    if files is None:
        print("[X] git no respondio: no pude listar los archivos a revisar.")
        return 2
    missing = missing_tests()
    if missing:
        print("[X] tests obligatorios ausentes:")
        print("\n".join(missing))
        return 1
    if args.staged:
        guard = staged_guard(files)
        if guard is not None:
            return guard
    by_lang, banned = classify(files)
    if add_config_langs(files, by_lang) and not (args.fix or args.unsafe):
        # El gate completo tambien cubre semgrep, docs y nombres del repo.
        # Con --fix no se expande: evita reformatear docs y JSON ajenos al cambio.
        files = sorted(set(files) | set(candidates(False) or []))
    mode = special_mode(args, by_lang)
    if mode is not None:
        return mode
    has_docs = any(f.endswith(".md") for f in files)
    if not by_lang and not banned and not has_docs:
        return empty_result(args)
    return lint_all(args, by_lang, banned, files)


def validate(args: argparse.Namespace) -> str | None:
    """Errores de combinacion de banderas, o None si todo esta bien."""
    if args.unsafe and not args.fix:
        return "--unsafe solo tiene sentido junto a --fix"
    if args.project and (args.audit or args.security):
        return "--project no se combina con --audit ni --security"
    if args.fast and (
        args.audit or args.security or args.mutation or args.project or args.skip is not None
    ):
        return "--fast solo aplica al modo normal (sin --audit, --security, --project ni --skip)"
    if args.json and (
        args.audit or args.security or args.mutation or args.project or args.skip is not None
    ):
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
