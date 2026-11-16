"""Pruebas del caso de uso y del adaptador en memoria."""

import pytest

from app.application.service import TaskService
from app.domain.task import Task
from app.infrastructure.memory import InMemoryTaskRepository


def _service() -> TaskService:
    """Servicio con el adaptador real en memoria."""
    return TaskService(InMemoryTaskRepository())


def test_add_guarda_la_tarea() -> None:
    """La tarea creada queda persistida."""
    service = _service()
    task = service.add("estudiar")
    assert service.list_all() == [task]


def test_add_usa_max_mas_uno() -> None:
    """Con ids dispersos no colisiona: 1 y 3 dan 4."""
    repository = InMemoryTaskRepository()
    repository.save(Task(id=1, title="uno"))
    repository.save(Task(id=3, title="tres"))

    task = TaskService(repository).add("cuatro")

    assert task.id == 4


def test_add_rechaza_titulo_vacio() -> None:
    """Un titulo en blanco es un error de dominio."""
    with pytest.raises(ValueError, match="titulo"):
        _service().add("   ")


def test_task_rechaza_id_invalido() -> None:
    """El id debe ser positivo."""
    with pytest.raises(ValueError, match="id"):
        Task(id=0, title="uno")


def test_save_reemplaza_por_id() -> None:
    """Guardar dos veces el mismo id deja una sola tarea."""
    repository = InMemoryTaskRepository()
    repository.save(Task(id=1, title="uno"))
    repository.save(Task(id=1, title="dos"))
    assert repository.all() == [Task(id=1, title="dos")]
