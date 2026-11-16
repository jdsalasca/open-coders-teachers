"""Pruebas del caso de uso y del adaptador en memoria."""

from concurrent.futures import ThreadPoolExecutor

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


def test_add_rechaza_titulo_vacio() -> None:
    """Un titulo en blanco es un error de dominio."""
    with pytest.raises(ValueError, match="titulo"):
        _service().add("   ")


def test_task_rechaza_id_invalido() -> None:
    """El id debe ser positivo."""
    with pytest.raises(ValueError, match="id"):
        Task(id=0, title="uno")


def test_ids_unicos_en_concurrente() -> None:
    """Cincuenta creaciones en paralelo no repiten id ni pierden tareas."""
    service = _service()
    with ThreadPoolExecutor(max_workers=8) as pool:
        tasks = list(pool.map(lambda index: service.add(f"t{index}"), range(50)))

    stored = service.list_all()
    assert len({task.id for task in tasks}) == 50
    assert len(stored) == 50
    assert {task.title for task in stored} == {f"t{index}" for index in range(50)}
