"""Adaptador en memoria: implementa el puerto TaskRepositoryPort."""

from app.domain.task import Task, TaskRepositoryPort


class InMemoryTaskRepository(TaskRepositoryPort):
    """Repositorio volatil para ejemplos y pruebas."""

    def __init__(self) -> None:
        """Arranca sin tareas."""
        self._tasks: list[Task] = []

    def save(self, task: Task) -> None:
        """Reemplaza por id o agrega al final."""
        self._tasks = [item for item in self._tasks if item.id != task.id]
        self._tasks.append(task)

    def all(self) -> list[Task]:
        """Devuelve una copia en orden de insercion."""
        return list(self._tasks)
