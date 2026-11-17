"""Adaptador de entrada: valida payloads y llama casos de uso."""

from app.application.service import TaskService
from app.interfaces.requests import CreateTaskRequest
from app.interfaces.views import TaskView


class TaskController:
    """Convierte payloads externos en llamadas a la aplicacion."""

    def __init__(self, service: TaskService) -> None:
        """Inyecta el caso de uso."""
        self._service = service

    def create(self, payload: dict[str, object]) -> TaskView:
        """Valida el payload con Pydantic y devuelve un DTO."""
        request = CreateTaskRequest.model_validate(payload)
        return TaskView.from_domain(self._service.add(request.title))

    def list(self) -> list[TaskView]:
        """Lista las tareas como DTO."""
        return [TaskView.from_domain(task) for task in self._service.list_all()]
