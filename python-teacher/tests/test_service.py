"""Pruebas del caso de uso y del adaptador en memoria."""

from app.application.service import TaskService
from app.domain.task import Task
from app.infrastructure.memory import InMemoryTaskRepositoryPort


def _service() -> TaskService:
    """Servicio con el adaptador real en memoria."""
    return TaskService(InMemoryTaskRepositoryPort())


def test_add_guarda_la_tarea() -> None:
    """La tarea creada queda persistida."""
    service = _service()
    task = service.add("estudiar")
    assert service.list_all() == [task]


def test_add_incrementa_el_id() -> None:
    """El segundo id es 2."""
    service = _service()
    service.add("uno")
    assert service.add("dos").id == 2


def test_save_reemplaza_por_id() -> None:
    """Guardar dos veces el mismo id deja una sola tarea."""
    repository = InMemoryTaskRepositoryPort()
    repository.save(Task(id=1, title="uno"))
    repository.save(Task(id=1, title="dos"))
    assert repository.all() == [Task(id=1, title="dos")]
