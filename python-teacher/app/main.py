"""Composition root: la unica pieza que conoce todas las capas."""

from app.application.service import TaskService
from app.infrastructure.memory import InMemoryTaskRepository
from app.interfaces.task_controller import TaskController


def main() -> None:
    """Crea una tarea y lista las tareas como DTO."""
    controller = TaskController(TaskService(InMemoryTaskRepository()))
    controller.create({"title": "estudiar"})
    for view in controller.list():
        print(view)


if __name__ == "__main__":
    main()
