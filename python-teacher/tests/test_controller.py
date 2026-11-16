"""Pruebas de la frontera de validacion."""

import pytest
from pydantic import ValidationError

from app.application.service import TaskService
from app.infrastructure.memory import InMemoryTaskRepository
from app.interfaces.task_controller import TaskController


def _controller() -> TaskController:
    """Controlador con el adaptador en memoria."""
    return TaskController(TaskService(InMemoryTaskRepository()))


def test_crea_con_payload_valido() -> None:
    """Un payload correcto crea la tarea."""
    task = _controller().create({"title": "estudiar"})
    assert task.title == "estudiar"


def test_conserva_espacios() -> None:
    """La frontera valida sin recortar el titulo."""
    task = _controller().create({"title": "  estudiar  "})
    assert task.title == "  estudiar  "


def test_rechaza_titulo_vacio() -> None:
    """Pydantic rechaza un titulo en blanco antes de llegar al dominio."""
    with pytest.raises(ValidationError):
        _controller().create({"title": "   "})


def test_rechaza_titulo_largo() -> None:
    """El maximo de 200 se valida en la frontera."""
    with pytest.raises(ValidationError):
        _controller().create({"title": "x" * 201})


def test_acepta_200_caracteres_unicode() -> None:
    """El limite cuenta caracteres, no unidades UTF-16."""
    task = _controller().create({"title": "😀" * 200})
    assert len(task.title) == 200


def test_rechaza_201_caracteres_unicode() -> None:
    """Un caracter mas tambien se rechaza con Unicode."""
    with pytest.raises(ValidationError):
        _controller().create({"title": "😀" * 201})
