package edu.teachers.infrastructure.persistence;

import edu.teachers.domain.Task;
import edu.teachers.domain.TaskRepositoryPort;
import java.util.ArrayList;
import java.util.List;

/** Adaptador en memoria, seguro entre hilos. */
public class InMemoryTaskRepository implements TaskRepositoryPort {

  private static final String IDS_EXHAUSTED = "se agotaron los ids";

  private final List<Task> tasks = new ArrayList<>();
  private int nextId;

  /** Crea un repositorio vacio. */
  public InMemoryTaskRepository() {}

  /**
   * Crea un repositorio con el contador en un valor concreto, para tests de limite.
   *
   * @param initialId valor inicial del contador
   */
  InMemoryTaskRepository(int initialId) {
    nextId = initialId;
  }

  /**
   * Crea una tarea. Si el titulo es invalido no se agrega nada, pero el contador puede dejar un
   * hueco: los ids no garantizan continuidad.
   */
  @Override
  public synchronized Task create(String title) {
    if (nextId == Integer.MAX_VALUE) {
      throw new IllegalStateException(IDS_EXHAUSTED);
    }
    int id = ++nextId;
    Task task = new Task(id, title, false);
    tasks.add(task);
    return task;
  }

  @Override
  public synchronized List<Task> list() {
    return List.copyOf(tasks);
  }
}
