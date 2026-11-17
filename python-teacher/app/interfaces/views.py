"""DTO de salida de una tarea."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.task import Task


@dataclass(frozen=True)
class TaskView:
    """Vista de una tarea: el controller no devuelve la entidad."""

    id: int
    title: str
    done: bool

    @classmethod
    def from_domain(cls, task: Task) -> TaskView:
        """Convierte una entidad del dominio en DTO."""
        return cls(id=task.id, title=task.title, done=task.done)
