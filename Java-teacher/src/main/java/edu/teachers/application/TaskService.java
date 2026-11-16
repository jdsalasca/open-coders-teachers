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
  public TaskService(TaskRepositoryPort repository) {
    this.repository = Objects.requireNonNull(repository, "repository");
  }

  /**
   * Crea una tarea con id unico y la guarda.
   *
   * @param title titulo de la tarea
   * @return tarea creada
   */
  public Task add(String title) {
    int nextId = repository.all().stream().mapToInt(Task::id).max().orElse(0) + 1;
    Task task = new Task(nextId, title, false);
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
