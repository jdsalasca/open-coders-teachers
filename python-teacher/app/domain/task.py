"""Entidad Task y puerto de persistencia."""

from dataclasses import dataclass
from typing import Protocol

MAX_TITLE_LENGTH = 200


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
        if len(self.title) > MAX_TITLE_LENGTH:
            raise ValueError("el titulo supera los 200 caracteres")


class TaskRepositoryPort(Protocol):
    """Puerto: el repositorio asigna el id y lista tareas."""

    def create(self, title: str) -> Task:
        """Crea una tarea con id unico."""

    def list(self) -> list[Task]:
        """Devuelve todas las tareas."""
