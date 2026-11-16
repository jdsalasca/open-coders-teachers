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


def test_rechaza_titulo_vacio() -> None:
    """Pydantic rechaza un titulo en blanco antes de llegar al dominio."""
    with pytest.raises(ValidationError):
        _controller().create({"title": "   "})


def test_rechaza_titulo_largo() -> None:
    """El maximo de 200 se valida en la frontera."""
    with pytest.raises(ValidationError):
        _controller().create({"title": "x" * 201})
