"""Casos de uso de tareas."""

from app.domain.task import Task, TaskRepository


class TaskService:
    """Orquesta el dominio recibiendo el puerto por inyeccion."""

    def __init__(self, repository: TaskRepository) -> None:
        """Guarda el puerto, no una implementacion concreta."""
        self._repository = repository

    def add(self, title: str) -> Task:
        """Crea una tarea nueva y la persiste."""
        task = Task(id=len(self._repository.all()) + 1, title=title)
        self._repository.save(task)
        return task

    def list_all(self) -> list[Task]:
        """Devuelve las tareas existentes."""
        return self._repository.all()
