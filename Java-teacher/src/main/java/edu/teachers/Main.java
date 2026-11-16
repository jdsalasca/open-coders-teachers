package edu.teachers;

import edu.teachers.application.TaskService;
import edu.teachers.domain.Task;
import edu.teachers.infrastructure.InMemoryTaskRepository;

/** Composition root: la unica clase que conoce las tres capas. */
public final class Main {

  private Main() {}

  /**
   * Arranca el ejemplo.
   *
   * @param args argumentos de linea de comandos
   */
  public static void main(String[] args) {
    TaskService service = new TaskService(new InMemoryTaskRepository());
    Task task = service.add("estudiar");
    System.out.println(task);
  }
}
