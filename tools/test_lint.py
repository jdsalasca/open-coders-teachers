"""Autochequeo del runner: deteccion de lenguaje, clasificacion y carpetas."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import lint


def check(condition: bool, message: str = "") -> None:
    """Falla el autochequeo si la condicion no se cumple."""
    if not condition:
        raise AssertionError(message)


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


def test_cada_carpeta_configurada_existe() -> None:
    """Las carpetas de LANGS existen en disco."""
    for lang in lint.LANGS:
        check((lint.ROOT / lang.folder).is_dir(), lang.folder)


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_") and callable(test):
            test()
    print("ok")
