"""Canario de capas: el dominio y la aplicacion no miran hacia arriba."""

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"


def _imports(path: Path) -> set[str]:
    """Modulos importados por un archivo, sin ejecutarlo."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _assert_no_imports(folder: str, forbidden: tuple[str, ...]) -> None:
    """Falla si algun archivo de la carpeta importa un modulo prohibido."""
    for path in (APP / folder).rglob("*.py"):
        for name in _imports(path):
            assert not name.startswith(forbidden), f"{path} importa {name}"


def test_dominio_no_importa_capas_superiores() -> None:
    """El dominio no conoce application, infrastructure ni interfaces."""
    _assert_no_imports("domain", ("app.application", "app.infrastructure", "app.interfaces"))


def test_aplicacion_no_importa_adaptadores() -> None:
    """La aplicacion no conoce infrastructure ni interfaces."""
    _assert_no_imports("application", ("app.infrastructure", "app.interfaces"))
