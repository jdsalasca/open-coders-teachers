"""Contrato del puerto: todo adaptador debe cumplirlo."""

from app.domain.task import Task, TaskRepositoryPort
from app.infrastructure.memory import InMemoryTaskRepository


def verificar_contrato(repository: TaskRepositoryPort) -> None:
    """Comportamiento minimo que cualquier adaptador debe respetar."""
    repository.save(Task(id=1, title="uno"))
    assert repository.all() == [Task(id=1, title="uno")]

    repository.save(Task(id=1, title="dos"))
    assert repository.all() == [Task(id=1, title="dos")]

    assert repository.all() is not repository.all()


def test_memoria_cumple_el_contrato() -> None:
    """El adaptador en memoria respeta el puerto."""
    verificar_contrato(InMemoryTaskRepository())
