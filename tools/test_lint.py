"""Autochequeo del runner: deteccion, portable, skip y canarios por lenguaje."""

import contextlib
import io
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import check_links
import lint


def check(condition: bool, message: str = "") -> None:
    """Falla el autochequeo si la condicion no se cumple."""
    if not condition:
        raise AssertionError(message)


def run(argv: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Corre una herramienta y devuelve el resultado completo."""
    return subprocess.run(  # noqa: S603 - argv fijo de los tests
        argv,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_detecta_cada_lenguaje() -> None:
    """Extensiones validas en la carpeta correcta."""
    check(lint.lang_for("python-teacher/src/app.py") == "python")
    check(lint.lang_for("typescript-teacher/src/app.tsx") == "typescript")
    check(lint.lang_for("React-teacher/src/App.tsx") == "react")
    check(lint.lang_for("go-teacher/main.go") == "go")
    check(lint.lang_for("Java-teacher/src/main/java/App.java") == "java")


def test_react() -> None:
    """React comparte TS y ademas acepta SCSS."""
    check(lint.lang_for("React-teacher/src/App.module.scss") == "react")
    check(lint.lang_for("React-teacher/src/App.css") is None)


def test_ignora_extension_y_carpeta_equivocadas() -> None:
    """No adivina lenguaje por extension suelta ni por mayusculas."""
    check(lint.lang_for("AGENTS.md") is None)
    check(lint.lang_for("python-teacher/notas.txt") is None)
    check(lint.lang_for("Go-teacher/main.go") is None)
    check(lint.lang_for("typescript-teacher/app.py") is None)


def test_clasifica_css_prohibido() -> None:
    """Un .css en React-teacher se reporta como prohibido."""
    by_lang, banned = lint.classify(["React-teacher/src/App.css", "React-teacher/src/App.tsx"])
    check(list(by_lang) == ["react"])
    check(len(banned) == 1)


def test_expand_ignora_generados() -> None:
    """Una carpeta se expande sin entrar en node_modules ni dist."""
    files = lint.expand(["React-teacher"])
    check(bool(files))
    check(not [f for f in files if "node_modules" in f or f.startswith("React-teacher/dist")])


def test_descubre_proyecto_por_manifiesto() -> None:
    """Un package.json delimita un proyecto node."""
    fixture = lint.ROOT / "tools" / "fixtures" / "bad-app"
    projects = lint.discover(fixture)
    check(len(projects) == 1, f"esperaba 1 proyecto, hay {len(projects)}")
    check(projects[0].kind == "node")
    check(any(f.endswith("bad.ts") for f in projects[0].files))


def test_portable_encuentra_hallazgos() -> None:
    """El baseline portable no puede devolver cero sobre el fixture malo."""
    fixture = lint.ROOT / "tools" / "fixtures" / "bad-app"
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = lint.portable(fixture, False)
    salida = buffer.getvalue()
    check(code == 1, f"esperaba hallazgos (1), obtuve {code}")
    check("max-params" in salida, "no reporto demasiados parametros")
    check("no-unused-vars" in salida, "no reporto variable sin usar")


def test_canario_python() -> None:
    """La config de ruff de python-teacher sigue cazando violaciones."""
    fixture = lint.ROOT / "tools" / "fixtures" / "bad-py" / "bad.py"
    config = lint.ROOT / "python-teacher" / "pyproject.toml"
    proc = run(
        [
            "ruff",
            "check",
            "--config",
            str(config),
            "--output-format=concise",
            str(fixture),
        ]
    )
    salida = proc.stdout + proc.stderr
    check(proc.returncode != 0, "ruff no detecto el fixture malo")
    check("PLR0913" in salida, "no reporto demasiados parametros")
    check("F401" in salida, "no reporto import sin usar")


def test_canario_go() -> None:
    """La config portable de Go sigue cazando violaciones."""
    fixture = lint.ROOT / "tools" / "fixtures" / "bad-go"
    config = lint.ROOT / "tools" / "go" / ".golangci.yml"
    proc = run(
        [
            "golangci-lint",
            "run",
            "--config",
            str(config),
            "--output.text.print-issued-lines=false",
        ],
        cwd=fixture,
    )
    salida = proc.stdout + proc.stderr
    check(proc.returncode != 0, "golangci-lint no detecto el fixture malo")
    check("argument-limit" in salida, "no reporto demasiados parametros")


def test_skip_de_un_solo_uso() -> None:
    """El skip avisa, se consume una vez y queda en el log."""
    original = (lint.SKIP_FILE, lint.SKIP_LOG)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            lint.SKIP_FILE = Path(tmp) / "skip"
            lint.SKIP_LOG = Path(tmp) / "log"
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                lint.write_skip("prueba de skip")
                check(lint.SKIP_FILE.exists(), "no se creo el marcador")
                usado = lint.consume_skip()
            check(usado, "el skip debia permitir el commit")
            check(not lint.SKIP_FILE.exists(), "el marcador no se consumio")
            check("Pide confirmacion" in buffer.getvalue(), "falto el aviso al humano")
    finally:
        lint.SKIP_FILE, lint.SKIP_LOG = original


def test_skip_caducado() -> None:
    """Un skip viejo no permite el commit."""
    original = (lint.SKIP_FILE, lint.SKIP_LOG, lint.SKIP_TTL)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            lint.SKIP_FILE = Path(tmp) / "skip"
            lint.SKIP_LOG = Path(tmp) / "log"
            lint.SKIP_TTL = 0
            with contextlib.redirect_stdout(io.StringIO()):
                lint.write_skip("viejo")
                usado = lint.consume_skip()
    finally:
        lint.SKIP_FILE, lint.SKIP_LOG, lint.SKIP_TTL = original
    check(not usado, "un skip caducado no debe pasar")


def test_tamano_de_archivo() -> None:
    """Un archivo que excede el maximo se reporta."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "big.py").write_text("x\n" * 10, encoding="utf-8")
        lang = lint.Lang("x", "python-teacher", (".py",), (), (), max_file_lines=5)
        code, lines = lint.size_check(lang, ["big.py"], base=base)
    check(code == 1, "no detecto el archivo largo")
    check(bool(lines), "no reporto el archivo largo")


def test_slop_detecta_tests_apagados() -> None:
    """Un test enfocado no debe pasar."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "x.test.ts").write_text('it.only("corre solo", () => {});\n', encoding="utf-8")
        code, lines = lint.slop_check(["x.test.ts"], base=base)
    check(code == 1, "no detecto el test enfocado")
    check(any(".only" in line for line in lines), "no reporto .only")


def test_slop_exige_justificacion() -> None:
    """Una supresion con motivo no es violacion."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "x.ts").write_text(
            "// eslint-disable-next-line no-console -- lo pide la CLI\n",
            encoding="utf-8",
        )
        (base / "y.py").write_text("import os  # noqa: S603 - motivo\n", encoding="utf-8")
        code, lines = lint.slop_check(["x.ts", "y.py"], base=base)
    check(code == 0, f"marco supresiones justificadas: {lines}")


def test_check_links_detecta_rotos() -> None:
    """Un enlace local inexistente se reporta."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "a.md").write_text("[x](no-existe.md)\n", encoding="utf-8")
        problems = check_links.check_file(base / "a.md")
    check(bool(problems), "no detecto el enlace roto")


def test_check_links_acepta_validos() -> None:
    """Un enlace a un archivo existente no es problema."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "b.md").write_text("# Hola\n", encoding="utf-8")
        (base / "a.md").write_text("[x](b.md#hola)\n", encoding="utf-8")
        problems = check_links.check_file(base / "a.md")
    check(not problems, f"marco un enlace valido: {problems}")


def test_cada_carpeta_configurada_existe() -> None:
    """Las carpetas de LANGS existen en disco."""
    for lang in lint.LANGS:
        check((lint.ROOT / lang.folder).is_dir(), lang.folder)


def test_expand_normaliza_separadores() -> None:
    """Una ruta con backslash se compara igual que una con slash."""
    files = lint.expand(["typescript-teacher\\tsconfig.json"])

    check(files == ["typescript-teacher/tsconfig.json"], str(files))


def test_config_con_codigo_expande_el_proyecto() -> None:
    """Un config staged junto a codigo no se salta el gate completo."""
    by_lang = {"typescript": ["typescript-teacher/src/model/counter.ts"]}

    changed = lint.add_config_langs(
        ["typescript-teacher/tsconfig.json", "typescript-teacher/src/model/counter.ts"],
        by_lang,
    )

    check(changed, "no detecto el cambio de configuracion")
    check(
        "typescript-teacher/src/controller/counter-controller.ts" in by_lang["typescript"],
        "no expandio al proyecto completo",
    )


def test_config_solo_expande_su_lenguaje() -> None:
    """Un config de Python no dispara los demas lenguajes."""
    by_lang: dict[str, list[str]] = {}

    lint.add_config_langs(["python-teacher/pyproject.toml"], by_lang)

    check(set(by_lang) == {"python"}, f"lenguajes: {sorted(by_lang)}")
    check(len(by_lang["python"]) > 1, "no expandio al proyecto python")


def test_config_global_expande_los_cinco_lenguajes() -> None:
    """Las reglas de semgrep y el runner afectan a todos."""
    by_lang: dict[str, list[str]] = {}

    lint.add_config_langs([".semgrep/rules.yml"], by_lang)

    check(
        set(by_lang) == {lang.name for lang in lint.LANGS},
        f"lenguajes: {sorted(by_lang)}",
    )


def test_parsea_dependencias_maven() -> None:
    """El listado de Maven se convierte en coordenadas para OSV."""
    text = (
        "The following files have been resolved:\n"
        "   jakarta.validation:jakarta.validation-api:jar:3.1.1:compile -- module x\n"
        "   org.hibernate.validator:hibernate-validator:jar:9.0.1.Final:runtime -- module y\n"
    )

    check(
        lint.parse_maven_dependencies(text)
        == [
            ("jakarta.validation:jakarta.validation-api", "3.1.1"),
            ("org.hibernate.validator:hibernate-validator", "9.0.1.Final"),
        ],
        "parseo incorrecto",
    )


def test_consulta_osv() -> None:
    """La consulta batch usa el ecosistema Maven y la version."""
    expected = {"queries": [{"package": {"name": "g:a", "ecosystem": "Maven"}, "version": "1.0"}]}

    check(lint.osv_queries([("g:a", "1.0")]) == expected, "consulta incorrecta")


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_") and callable(test):
            test()
    print("ok")
