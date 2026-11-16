package edu.teachers.infrastructure.web;

import edu.teachers.application.TaskService;
import edu.teachers.application.TaskView;
import java.util.List;

/** Adaptador de entrada: expone DTOs, nunca entidades de dominio. */
public class TaskController {

  private final TaskService service;

  /**
   * Inyecta el caso de uso.
   *
   * @param service servicio de tareas
   */
  public TaskController(TaskService service) {
    this.service = service;
  }

  /**
   * Lista las tareas como DTO.
   *
   * @return vistas de tareas
   */
  public List<TaskView> list() {
    return service.listViews();
  }
}
