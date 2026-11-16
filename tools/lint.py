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


# Cada comando: (argv, acepta lista de archivos). Los que compilan por paquete
# (golangci-lint, mvn) corren sobre el modulo completo.
@dataclass(frozen=True)
class Command:
    """Un comando del linter.

    takes_files: si acepta rutas de archivo como argumentos.
    needs: extensiones que deben existir en el lote para ejecutarlo.
    """

    argv: list[str]
    takes_files: bool = False
    # Solo se ejecuta si hay archivos con estas extensiones en el lote (tsc
    # falla con TS18003 cuando el proyecto no tiene ni un .ts).
    needs: tuple[str, ...] = ()


@dataclass(frozen=True)
class Lang:
    """Lenguaje, carpeta del repo y comandos de revision/arreglo."""

    name: str
    folder: str
    exts: tuple[str, ...]
    check: tuple[Command, ...]
    fix: tuple[Command, ...]


LANGS = (
    Lang(
        name="python",
        folder="python-teacher",
        exts=(".py",),
        check=(
            Command(["ruff", "check", "--output-format=concise"], True),
            Command(["ruff", "format", "--check"], True),
        ),
        fix=(
            Command(["ruff", "check", "--fix"], True),
            Command(["ruff", "format"], True),
        ),
    ),
    Lang(
        name="typescript",
        folder="typescript-teacher",
        exts=(".ts", ".tsx", ".js", ".jsx"),
        check=(
            Command(["eslint", "--format=unix"], True),
            Command(["prettier", "--check"], True),
            Command(["tsc", "--noEmit"], False, (".ts", ".tsx")),
        ),
        fix=(
            Command(["eslint", "--fix"], True),
            Command(["prettier", "--write"], True),
        ),
    ),
    Lang(
        name="go",
        folder="go-teacher",
        exts=(".go",),
        check=(
            Command(["gofmt", "-l"], True),
            Command(["golangci-lint", "run", "--output.text.print-issued-lines=false"]),
        ),
        fix=(
            Command(["gofmt", "-w"], True),
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
        ),
        fix=(Command(["mvn", "-q", "-B", "spotless:apply"]),),
    ),
)


def lang_for(rel_path: str) -> str | None:
    """Devuelve el lenguaje segun la carpeta y la extension del archivo."""
    parts = Path(rel_path).parts
    if not parts:
        return None
    for lang in LANGS:
        if parts[0] == lang.folder and Path(rel_path).suffix in lang.exts:
            return lang.name
    return None


def git_files(*args: str) -> list[str]:
    """Lista de archivos que devuelve git, sin vacios."""
    out = subprocess.run(["git", *args, "-z"], cwd=ROOT, capture_output=True, text=True, check=True)
    return [p for p in out.stdout.split("\0") if p]


def candidates(staged: bool) -> list[str]:
    """Archivos a revisar: staged o todos (incluye los no rastreados)."""
    if staged:
        return git_files("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    return git_files("ls-files", "--cached", "--others", "--exclude-standard")


def run(cmd: Command, lang: Lang, files: list[str]) -> tuple[int, str]:
    """Ejecuta un comando en la carpeta del lenguaje y filtra ruido."""
    local_bin = ROOT / lang.folder / LOCAL_BIN
    exe = shutil.which(cmd.argv[0], path=str(local_bin)) or shutil.which(cmd.argv[0])
    if exe is None:
        return 2, f"[X] falta '{cmd.argv[0]}' (ver README)"
    extra = [Path(f).relative_to(lang.folder).as_posix() for f in files] if cmd.takes_files else []
    proc = subprocess.run(
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


def report(lang: Lang, files: list[str], fix: bool) -> bool:
    """Corre el linter. Devuelve True si el lenguaje quedo limpio."""
    print(f"\n== {lang.name} ({len(files)} archivo(s)) ==")
    if fix:
        for cmd in lang.fix:
            run(cmd, lang, files)
    ok = True
    for cmd in lang.check:
        if cmd.needs and not any(Path(f).suffix in cmd.needs for f in files):
            continue
        code, output = run(cmd, lang, files)
        if code == 2:
            print(output)
            return False
        if code != 0:
            ok = False
            if output:
                print(output)
    print("  ok" if ok else "  con problemas")
    return ok


def main() -> int:
    """Punto de entrada: corre los linters y resume el resultado."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help="archivos concretos (por defecto todo)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--staged", action="store_true", help="solo lo que esta en stage")
    group.add_argument("--fix", action="store_true", help="aplica arreglos automaticos")
    args = parser.parse_args()

    files = args.files or candidates(args.staged)
    by_lang: dict[str, list[str]] = {}
    for f in files:
        name = lang_for(f)
        if name:
            by_lang.setdefault(name, []).append(f)

    if not by_lang:
        print("Nada que revisar.")
        return 0

    clean = True
    for lang in LANGS:
        if lang.name in by_lang:
            clean &= report(lang, by_lang[lang.name], args.fix)

    if not clean:
        print("\nProblemas de lint. Arreglo automatico: python tools/lint.py --fix")
        return 1
    print("\nTodo limpio.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
