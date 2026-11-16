"""Casos de uso de tareas."""

from app.domain.task import Task, TaskRepositoryPort


class TaskService:
    """Orquesta el dominio recibiendo el puerto por inyeccion."""

    def __init__(self, repository: TaskRepositoryPort) -> None:
        """Guarda el puerto, no una implementacion concreta."""
        self._repository = repository

    def add(self, title: str) -> Task:
        """Crea una tarea con id unico y la persiste."""
        existing = self._repository.all()
        next_id = max((task.id for task in existing), default=0) + 1
        task = Task(id=next_id, title=title)
        self._repository.save(task)
        return task

    def list_all(self) -> list[Task]:
        """Devuelve las tareas existentes."""
        return self._repository.all()
