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
import re
import subprocess
import sys
import time
from pathlib import Path

from lintlib.audit import (  # noqa: F401 - reexportado para tests y CLI
    AUDIT,
    MUTATION,
    audit,
    mutation,
    osv_queries,
    parse_cargo_lock,
    parse_maven_dependencies,
    parse_osv_response,
    security,
)
from lintlib.common import (
    LANGS,
    ROOT,
    SKIP_FILE,
    SKIP_LOG,
    SKIP_TTL,
    Command,
    Lang,
    candidates,
    expand,
    git_files,
    lang_by_folder,
    lang_for,  # noqa: F401 - reexportado para tests
    languages_of,
    root_command,
    run,
    should_run,
    staged_deleted,
    walk_files,
)
from lintlib.portable import (  # noqa: F401 - reexportado para tests y CLI
    Project,
    discover,
    portable,
    portable_size,
    project_warnings,
    target_flags,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


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
    changed = [
        path
        for path in files
        if path in CONFIG_LANGS or (path.startswith("tools/lintlib/") and path.endswith(".py"))
    ]
    if not changed:
        return False
    everything = candidates(False) or []
    for path in changed:
        language = CONFIG_LANGS.get(path, "*")
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
    """Cada lenguaje del repo debe conservar al menos un test versionado."""
    found = git_files("ls-files", "--cached")
    if found is None:
        found = [path.relative_to(ROOT).as_posix() for path in walk_files(ROOT)]
    missing = []
    for lang in LANGS:
        if not lang.test_glob:
            continue
        if not any(Path(path).match(lang.test_glob) for path in found):
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


def expand_deleted(deleted: list[str], by_lang: dict[str, list[str]]) -> None:
    """Un borrado de codigo dispara el gate completo de su lenguaje."""
    names = languages_of(deleted)
    if not names:
        return
    everything = candidates(False) or []
    for name in names:
        lang = next(lg for lg in LANGS if lg.name == name)
        by_lang[name] = [
            f for f in everything if f.startswith(lang.folder + "/") and Path(f).suffix in lang.exts
        ]


def expand_config(
    files: list[str],
    deleted: list[str],
    by_lang: dict[str, list[str]],
    fixing: bool,
) -> list[str]:
    """Expande el alcance cuando cambia una configuracion."""
    if add_config_langs([*files, *deleted], by_lang) and not fixing:
        # El gate completo tambien cubre semgrep, docs y nombres del repo.
        # Con --fix no se expande: evita reformatear docs y JSON ajenos al cambio.
        return sorted(set(files) | set(candidates(False) or []))
    return files


def repo_mode(args: argparse.Namespace) -> int:
    """Modo repo: las seis carpetas de este proyecto."""
    files = expand(args.files) if args.files else candidates(args.staged)
    deleted = staged_deleted() if args.staged else []
    if files is None or deleted is None:
        print("[X] git no respondio: no pude listar los archivos a revisar.")
        return 2
    missing = missing_tests()
    if missing:
        print("[X] tests obligatorios ausentes:")
        print("\n".join(missing))
        return 1
    guard = staged_guard(files) if args.staged else None
    if guard is not None:
        return guard
    by_lang, banned = classify(files)
    expand_deleted(deleted, by_lang)
    files = expand_config(files, deleted, by_lang, args.fix or args.unsafe)
    mode = special_mode(args, by_lang)
    if mode is not None:
        return mode
    has_docs = any(f.endswith(".md") for f in files)
    if not by_lang and not banned and not has_docs and not deleted:
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
