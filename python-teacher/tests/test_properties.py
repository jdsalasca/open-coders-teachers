"""Propiedades del dominio y del adaptador."""

from hypothesis import given
from hypothesis import strategies as st

from app.application.service import TaskService
from app.infrastructure.memory import InMemoryTaskRepository

TITLE = st.text(min_size=1, max_size=40).filter(lambda value: value.strip() != "")


@given(TITLE)
def test_add_conserva_el_titulo(title: str) -> None:
    """La tarea guardada conserva el titulo recibido."""
    service = TaskService(InMemoryTaskRepository())
    assert service.add(title).title == title


@given(st.lists(TITLE, max_size=20))
def test_repositorio_conserva_las_tareas(titles: list[str]) -> None:
    """Cada tarea se guarda con un id unico y su titulo."""
    repository = InMemoryTaskRepository()
    created = [repository.create(title) for title in titles]

    assert [task.title for task in repository.all()] == titles
    assert len({task.id for task in created}) == len(created)
