"""Adaptador de entrada: valida payloads y llama casos de uso."""

from app.application.service import TaskService
from app.domain.task import Task
from app.interfaces.requests import CreateTaskRequest


class TaskController:
    """Convierte payloads externos en llamadas a la aplicacion."""

    def __init__(self, service: TaskService) -> None:
        """Inyecta el caso de uso."""
        self._service = service

    def create(self, payload: dict[str, object]) -> Task:
        """Valida el payload con Pydantic y crea la tarea."""
        request = CreateTaskRequest.model_validate(payload)
        return self._service.add(request.title)
