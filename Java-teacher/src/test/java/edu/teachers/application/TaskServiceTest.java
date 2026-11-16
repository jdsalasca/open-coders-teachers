package edu.teachers.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

import edu.teachers.domain.Task;
import edu.teachers.infrastructure.persistence.InMemoryTaskRepository;
import java.util.List;
import org.junit.jupiter.api.Test;

/** Pruebas del caso de uso de tareas. */
class TaskServiceTest {

  @Test
  void agregarGuardaLaTarea() {
    TaskService service = new TaskService(new InMemoryTaskRepository());

    Task task = service.add("estudiar");

    assertEquals(1, task.id());
    assertFalse(task.done());
    assertEquals(List.of(task), service.list());
  }

  @Test
  void agregarIncrementaElId() {
    TaskService service = new TaskService(new InMemoryTaskRepository());

    service.add("uno");

    assertEquals(2, service.add("dos").id());
  }

  @Test
  void listViewsDevuelveDtos() {
    TaskService service = new TaskService(new InMemoryTaskRepository());
    service.add("estudiar");

    List<TaskView> views = service.listViews();

    assertEquals(List.of(new TaskView(1, "estudiar", false)), views);
  }
}
