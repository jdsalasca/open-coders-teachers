package edu.teachers.infrastructure.persistence;

import edu.teachers.domain.Task;
import edu.teachers.domain.TaskRepositoryPort;
import java.util.ArrayList;
import java.util.List;

/** Adaptador en memoria del puerto de tareas. */
public class InMemoryTaskRepository implements TaskRepositoryPort {

  private final List<Task> tasks = new ArrayList<>();

  @Override
  public void save(Task task) {
    tasks.removeIf(item -> item.id() == task.id());
    tasks.add(task);
  }

  @Override
  public List<Task> all() {
    return List.copyOf(tasks);
  }
}
