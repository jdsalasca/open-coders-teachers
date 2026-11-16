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

    def test_ignora_extension_y_carpeta_equivocadas(self) -> None:
        """No adivina lenguaje por extension suelta ni por mayusculas."""
        self.assertIsNone(lint.lang_for("AGENTS.md"))
        self.assertIsNone(lint.lang_for("python-teacher/notas.txt"))
        self.assertIsNone(lint.lang_for("Go-teacher/main.go"))
        self.assertIsNone(lint.lang_for("typescript-teacher/app.py"))

    def test_cada_carpeta_configurada_existe(self) -> None:
        """Las carpetas de LANGS existen en disco."""
        for lang in lint.LANGS:
            with self.subTest(lang=lang.name):
                self.assertTrue((lint.ROOT / lang.folder).is_dir(), lang.folder)


if __name__ == "__main__":
    unittest.main()
