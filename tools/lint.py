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


LANGS = (
    Lang(
        name="python",
        folder="python-teacher",
        exts=(".py",),
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
    out = subprocess.run(  # noqa: S603 - argumentos fijos, sin shell
        ["git", *args, "-z"],  # noqa: S607 - git esta en el PATH
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
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
    proc = subprocess.run(  # noqa: S603 - lista de argumentos, sin shell
        [exe, *cmd.argv[1:], *extra],
        cwd=ROOT / lang.folder,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
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
    proc = subprocess.run(  # noqa: S603 - lista de argumentos, sin shell
        [exe, *argv[1:]],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, clean(proc.stdout + proc.stderr)


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


def report(lang: Lang, files: list[str], fix: tuple[Command, ...] = ()) -> int:
    """Corre el linter. 0 limpio, 1 problemas, 2 herramienta ausente."""
    print(f"\n== {lang.name} ({len(files)} archivo(s)) ==")
    for cmd in fix:
        run(cmd, lang, files)
    status = 0
    for cmd in lang.check:
        if not should_run(cmd, lang, files):
            continue
        code, output = execute(cmd, lang, files)
        if code is None:
            print(output)
            return 2
        if code != 0:
            status = 1
            if output:
                print(output)
    print("  ok" if status == 0 else "  con problemas")
    return status


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


def parse_args() -> argparse.Namespace:
    """Lee las banderas de la linea de comandos."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help="archivos concretos (por defecto todo)")
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
        "--security", action="store_true", help="secretos, patrones inseguros y dependencias"
    )
    group.add_argument(
        "--skip",
        nargs="?",
        const="sin motivo declarado",
        metavar="MOTIVO",
        help="permite el proximo commit sin linters (de un solo uso)",
    )
    return parser.parse_args()


def lint_all(args: argparse.Namespace, by_lang: dict[str, list[str]], banned: list[str]) -> int:
    """Corre los linters de cada lenguaje y resume el resultado."""
    status = 1 if banned else 0
    if banned:
        print("\n== estructura ==")
        print("\n".join(banned))

    fixers = args.fix or args.unsafe
    for lang in LANGS:
        if lang.name in by_lang:
            commands = lang.fix_unsafe if args.unsafe else lang.fix
            status = max(status, report(lang, by_lang[lang.name], commands if fixers else ()))

    if status == 2:
        print("\nFalta una herramienta. Instalala y reintenta (ver README).")
        return 2
    if status == 1:
        print("\nProblemas de lint. Arreglo automatico: python tools/lint.py --fix")
        return 1
    print("\nTodo limpio.")
    return 0


def main() -> int:
    """Punto de entrada: decide el modo y delega."""
    args = parse_args()

    if args.skip is not None:
        return write_skip(args.skip)
    if args.staged and consume_skip():
        return 0

    files = expand(args.files) if args.files else candidates(args.staged)
    by_lang, banned = classify(files)
    if not by_lang and not banned:
        print("Nada que revisar.")
        return 0

    if args.audit:
        return audit(sorted(by_lang))
    if args.security:
        return security(sorted(by_lang))
    return lint_all(args, by_lang, banned)


if __name__ == "__main__":
    raise SystemExit(main())
