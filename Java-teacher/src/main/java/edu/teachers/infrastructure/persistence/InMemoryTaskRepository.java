package edu.teachers.infrastructure.persistence;

import edu.teachers.domain.Task;
import edu.teachers.domain.TaskRepositoryPort;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicInteger;

/** Adaptador en memoria, seguro entre hilos. */
public class InMemoryTaskRepository implements TaskRepositoryPort {

  private static final String IDS_EXHAUSTED = "se agotaron los ids";

  private final List<Task> tasks = new CopyOnWriteArrayList<>();
  private final AtomicInteger nextId = new AtomicInteger();

  /** Crea un repositorio vacio. */
  public InMemoryTaskRepository() {}

  /**
   * Crea un repositorio con el contador en un valor concreto, para tests de limite.
   *
   * @param initialId valor inicial del contador
   */
  InMemoryTaskRepository(int initialId) {
    nextId.set(initialId);
  }

  /**
   * Crea una tarea. Si el titulo es invalido no se agrega nada, pero el contador puede dejar un
   * hueco: los ids no garantizan continuidad.
   */
  @Override
  public Task create(String title) {
    int id =
        nextId.updateAndGet(
            current -> {
              if (current == Integer.MAX_VALUE) {
                throw new IllegalStateException(IDS_EXHAUSTED);
              }
              return current + 1;
            });
    Task task = new Task(id, title, false);
    tasks.add(task);
    return task;
  }

  @Override
  public List<Task> all() {
    return List.copyOf(tasks);
  }
}
