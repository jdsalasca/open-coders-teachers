"""Composition root: la unica pieza que conoce todas las capas."""

from app.application.service import TaskService
from app.infrastructure.memory import InMemoryTaskRepository
from app.interfaces.task_controller import TaskController
from app.interfaces.views import TaskView


def _print_views(views: list[TaskView]) -> None:
    """Imprime una tabla simple y legible."""
    print("Tareas")
    print("-----")
    for view in views:
        estado = "hecha" if view.done else "pendiente"
        print(f"{view.id:>2}  {view.title:<20}  {estado}")


def main() -> None:
    """Crea una tarea y lista las tareas como DTO."""
    controller = TaskController(TaskService(InMemoryTaskRepository()))
    controller.create({"title": "estudiar"})
    _print_views(controller.list())


if __name__ == "__main__":
    main()
