"""Contrato del puerto: todo adaptador debe cumplirlo."""

from app.domain.task import TaskRepositoryPort
from app.infrastructure.memory import InMemoryTaskRepository


def verificar_contrato(repository: TaskRepositoryPort) -> None:
    """Comportamiento minimo que cualquier adaptador debe respetar."""
    first = repository.create("uno")
    second = repository.create("dos")

    assert first.id != second.id
    assert [task.id for task in repository.list()] == [first.id, second.id]
    assert repository.list() is not repository.list()


def test_memoria_cumple_el_contrato() -> None:
    """El adaptador en memoria respeta el puerto."""
    verificar_contrato(InMemoryTaskRepository())
