package edu.teachers.infrastructure.web;

import edu.teachers.application.TaskService;
import edu.teachers.application.TaskView;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.ConstraintViolationException;
import jakarta.validation.Validator;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/** Adaptador de entrada: valida DTOs y expone DTOs, nunca entidades. */
public class TaskController {

  private final TaskService service;
  private final Validator validator;

  /**
   * Inyecta el caso de uso y el validador.
   *
   * @param service servicio de tareas
   * @param validator validador de Bean Validation
   */
  public TaskController(TaskService service, Validator validator) {
    this.service = Objects.requireNonNull(service, "service");
    this.validator = Objects.requireNonNull(validator, "validator");
  }

  /**
   * Crea una tarea validando la peticion.
   *
   * @param request datos de entrada
   * @return tarea creada como DTO
   */
  public TaskView create(CreateTaskRequest request) {
    Set<ConstraintViolation<CreateTaskRequest>> violations = validator.validate(request);
    if (!violations.isEmpty()) {
      throw new ConstraintViolationException(violations);
    }
    return TaskView.from(service.add(request.title()));
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
