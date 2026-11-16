package edu.teachers.infrastructure.persistence;

import edu.teachers.domain.Task;
import edu.teachers.domain.TaskRepositoryPort;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicInteger;

/** Adaptador en memoria, seguro entre hilos. */
public class InMemoryTaskRepository implements TaskRepositoryPort {

  private final List<Task> tasks = new CopyOnWriteArrayList<>();
  private final AtomicInteger nextId = new AtomicInteger();

  @Override
  public Task create(String title) {
    Task task = new Task(nextId.incrementAndGet(), title, false);
    tasks.add(task);
    return task;
  }

  @Override
  public List<Task> all() {
    return List.copyOf(tasks);
  }
}
