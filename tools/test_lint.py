"""Autochequeo del runner: deteccion de lenguaje y carpetas existentes."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import lint


class LangForTest(unittest.TestCase):
    """Comprueba que cada carpeta se asocie a su lenguaje."""

    def test_detecta_cada_lenguaje(self) -> None:
        """Extensiones validas en la carpeta correcta."""
        self.assertEqual(lint.lang_for("python-teacher/src/app.py"), "python")
        self.assertEqual(lint.lang_for("typescript-teacher/src/app.tsx"), "typescript")
        self.assertEqual(lint.lang_for("go-teacher/main.go"), "go")
        self.assertEqual(lint.lang_for("Java-teacher/src/main/java/App.java"), "java")

    def test_react(self) -> None:
        """React comparte TS y ademas acepta SCSS."""
        self.assertEqual(lint.lang_for("React-teacher/src/App.tsx"), "react")
        self.assertEqual(lint.lang_for("React-teacher/src/App.module.scss"), "react")
        self.assertIsNone(lint.lang_for("React-teacher/src/App.css"))

    def test_ignora_extension_y_carpeta_equivocadas(self) -> None:
        """No adivina lenguaje por extension suelta ni por mayusculas."""
        self.assertIsNone(lint.lang_for("AGENTS.md"))
        self.assertIsNone(lint.lang_for("python-teacher/notas.txt"))
        self.assertIsNone(lint.lang_for("Go-teacher/main.go"))
        self.assertIsNone(lint.lang_for("typescript-teacher/app.py"))

    def test_expand_ignora_generados(self) -> None:
        """Una carpeta se expande sin entrar en node_modules ni dist."""
        files = lint.expand(["React-teacher"])
        self.assertTrue(files)
        self.assertFalse(
            [f for f in files if "node_modules" in f or f.startswith("React-teacher/dist")]
        )

    def test_clasifica_css_prohibido(self) -> None:
        """Un .css en React-teacher se reporta como prohibido."""
        by_lang, banned = lint.classify(["React-teacher/src/App.css", "React-teacher/src/App.tsx"])
        self.assertEqual(list(by_lang), ["react"])
        self.assertEqual(len(banned), 1)

    def test_cada_carpeta_configurada_existe(self) -> None:
        """Las carpetas de LANGS existen en disco."""
        for lang in lint.LANGS:
            with self.subTest(lang=lang.name):
                self.assertTrue((lint.ROOT / lang.folder).is_dir(), lang.folder)


if __name__ == "__main__":
    unittest.main()
