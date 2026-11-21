"""Adaptador en memoria: implementa el puerto TaskRepositoryPort."""

import threading

from app.domain.task import Task, TaskRepositoryPort


class InMemoryTaskRepository(TaskRepositoryPort):
    """Repositorio volatil, seguro entre hilos."""

    def __init__(self) -> None:
        """Arranca sin tareas."""
        self._tasks: list[Task] = []
        self._lock = threading.Lock()

    def create(self, title: str) -> Task:
        """Asigna un id unico y guarda la tarea."""
        with self._lock:
            task = Task(id=len(self._tasks) + 1, title=title)
            self._tasks.append(task)
            return task

    def list(self) -> list[Task]:
        """Devuelve una copia en orden de insercion."""
        with self._lock:
            return list(self._tasks)
