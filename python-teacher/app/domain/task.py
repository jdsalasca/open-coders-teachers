"""Entidad Task y puerto de persistencia."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Task:
    """Una tarea del dominio."""

    id: int
    title: str
    done: bool = False


class TaskRepositoryPort(Protocol):
    """Puerto: lo que la aplicacion necesita para guardar tareas."""

    def save(self, task: Task) -> None:
        """Guarda o actualiza una tarea."""

    def all(self) -> list[Task]:
        """Devuelve todas las tareas."""
