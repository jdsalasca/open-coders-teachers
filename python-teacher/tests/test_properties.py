"""Propiedades del dominio y del adaptador."""

from hypothesis import given
from hypothesis import strategies as st

from app.application.service import TaskService
from app.domain.task import Task
from app.infrastructure.memory import InMemoryTaskRepository


@given(st.text(max_size=40))
def test_add_conserva_el_titulo(title: str) -> None:
    """La tarea guardada conserva el titulo recibido."""
    service = TaskService(InMemoryTaskRepository())
    assert service.add(title).title == title


@given(st.lists(st.integers(min_value=1, max_value=1000), unique=True, max_size=20))
def test_repositorio_conserva_todas_las_tareas(ids: list[int]) -> None:
    """Guardar ids distintos deja exactamente esas tareas."""
    repository = InMemoryTaskRepository()
    for identifier in ids:
        repository.save(Task(id=identifier, title=f"t{identifier}"))
    assert {task.id for task in repository.all()} == set(ids)
