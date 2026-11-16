package edu.teachers.application;

import edu.teachers.domain.Task;
import edu.teachers.domain.TaskRepositoryPort;
import java.util.List;

/** Casos de uso de tareas: depende solo del dominio. */
public class TaskService {

  private final TaskRepositoryPort repository;

  /**
   * Inyecta el puerto de persistencia.
   *
   * @param repository puerto del dominio
   */
  public TaskService(TaskRepositoryPort repository) {
    this.repository = repository;
  }

  /**
   * Crea una tarea nueva y la guarda.
   *
   * @param title titulo de la tarea
   * @return tarea creada
   */
  public Task add(String title) {
    Task task = new Task(repository.all().size() + 1, title, false);
    repository.save(task);
    return task;
  }

  /**
   * Lista las tareas guardadas.
   *
   * @return tareas existentes
   */
  public List<Task> list() {
    return repository.all();
  }

  /**
   * Lista las tareas como DTO de aplicacion.
   *
   * @return vistas de las tareas
   */
  public List<TaskView> listViews() {
    return repository.all().stream().map(TaskView::from).toList();
  }
}
