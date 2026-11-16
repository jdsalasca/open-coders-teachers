"""Entidad Task y puerto de persistencia."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Task:
    """Una tarea del dominio."""

    id: int
    title: str
    done: bool = False

    def __post_init__(self) -> None:
        """Valida las invariantes del dominio."""
        if self.id < 1:
            raise ValueError("el id debe ser positivo")
        if not self.title.strip():
            raise ValueError("el titulo no puede estar vacio")


class TaskRepositoryPort(Protocol):
    """Puerto: el repositorio asigna el id y lista tareas."""

    def create(self, title: str) -> Task:
        """Crea una tarea con id unico."""

    def all(self) -> list[Task]:
        """Devuelve todas las tareas."""
