package edu.teachers.application;

import edu.teachers.domain.Task;
import edu.teachers.domain.TaskRepositoryPort;
import java.util.List;
import java.util.Objects;

/** Casos de uso de tareas: depende solo del dominio. */
public class TaskService {

  private final TaskRepositoryPort repository;

  /**
   * Inyecta el puerto de persistencia.
   *
   * @param repository puerto del dominio, obligatorio
   */
  public TaskService(final TaskRepositoryPort repository) {
    this.repository = Objects.requireNonNull(repository, "repository");
  }

  /**
   * Crea una tarea; el repositorio asigna el id.
   *
   * @param title titulo de la tarea
   * @return tarea creada
   */
  public Task add(final String title) {
    return repository.create(title);
  }

  /**
   * Lista las tareas guardadas.
   *
   * @return tareas existentes
   */
  public List<Task> list() {
    return repository.list();
  }

  /**
   * Lista las tareas como DTO de aplicacion.
   *
   * @return vistas de las tareas
   */
  public List<TaskView> listViews() {
    return repository.list().stream().map(TaskView::from).toList();
  }
}
