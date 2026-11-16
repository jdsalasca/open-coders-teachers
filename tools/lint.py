"""Ejecuta el linter de cada lenguaje sobre los archivos indicados.

uso:
  python tools/lint.py             # todo el repo
  python tools/lint.py --fix       # arregla y vuelve a revisar
  python tools/lint.py --staged    # solo lo que esta en el indice (hook)
  python tools/lint.py a.py b.ts   # archivos concretos

Sale 0 si todo pasa, 1 si hay problemas, 2 si falta una herramienta.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL_BIN = "node_modules/.bin"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# file_exts vacio: el comando corre sobre el modulo completo (golangci-lint,
# mvn). Con file_exts solo recibe archivos de esas extensiones.
@dataclass(frozen=True)
class Command:
    """Un comando del linter y las extensiones que le corresponden.

    file_exts: se le pasan los archivos del lote con esas extensiones.
    needs: solo se ejecuta si el lote trae alguna de esas extensiones.
    """

    argv: list[str]
    file_exts: tuple[str, ...] = ()
    needs: tuple[str, ...] = ()


@dataclass(frozen=True)
class Lang:
    """Lenguaje, carpeta del repo, comandos y extensiones prohibidas."""

    name: str
    folder: str
    exts: tuple[str, ...]
    check: tuple[Command, ...]
    fix: tuple[Command, ...]
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
        ),
        fix=(
            Command(["ruff", "check", "--fix"], (".py",)),
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
        ),
        fix=(
            Command(["gofmt", "-w"], (".go",)),
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
            Command(["mvn", "-q", "-B", "test", "-Dtest=ArchitectureTest"]),
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


SKIP = {"node_modules", ".git", "dist", "target", ".venv", "__pycache__", ".mypy_cache"}


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


def should_run(cmd: Command, files: list[str]) -> bool:
    """False si el lote no trae archivos que este comando sepa revisar."""
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
    dropped = (
        "WARNING:",
        "Re-run Maven",
        "For more information",
        "To see the full stack",
        "-> [Help 1]",
        "Help 1]",
    )
    kept = []
    for raw in (proc.stdout + proc.stderr).splitlines():
        line = raw.removeprefix("[ERROR] ")
        if not line.strip() or line.strip().startswith(dropped):
            continue
        if "maven.apache.org" in line:
            continue
        kept.append(line)
    output = "\n".join(kept).strip()
    return proc.returncode, output.replace(prefix + "\\", "").replace(prefix + "/", "")


def report(lang: Lang, files: list[str], fix: bool) -> int:
    """Corre el linter. 0 limpio, 1 problemas, 2 herramienta ausente."""
    print(f"\n== {lang.name} ({len(files)} archivo(s)) ==")
    if fix:
        for cmd in lang.fix:
            run(cmd, lang, files)
    status = 0
    for cmd in lang.check:
        if not should_run(cmd, files):
            continue
        code, output = run(cmd, lang, files)
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


def main() -> int:
    """Punto de entrada: corre los linters y resume el resultado."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help="archivos concretos (por defecto todo)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--staged", action="store_true", help="solo lo que esta en stage")
    group.add_argument("--fix", action="store_true", help="aplica arreglos automaticos")
    group.add_argument(
        "--audit", action="store_true", help="busca vulnerabilidades en dependencias"
    )
    args = parser.parse_args()

    files = expand(args.files) if args.files else candidates(args.staged)
    by_lang, banned = classify(files)

    if not by_lang and not banned:
        print("Nada que revisar.")
        return 0

    if args.audit:
        return audit(sorted(by_lang))

    status = 1 if banned else 0
    if banned:
        print("\n== estructura ==")
        print("\n".join(banned))

    for lang in LANGS:
        if lang.name in by_lang:
            status = max(status, report(lang, by_lang[lang.name], args.fix))

    if status == 2:
        print("\nFalta una herramienta. Instalala y reintenta (ver README).")
        return 2
    if status == 1:
        print("\nProblemas de lint. Arreglo automatico: python tools/lint.py --fix")
        return 1
    print("\nTodo limpio.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
