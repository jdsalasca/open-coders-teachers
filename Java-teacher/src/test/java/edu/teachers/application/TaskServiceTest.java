package edu.teachers.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;

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
  void usaMaxMasUnoConIdsDispersos() {
    InMemoryTaskRepository repository = new InMemoryTaskRepository();
    repository.save(new Task(1, "uno", false));
    repository.save(new Task(3, "tres", false));
    TaskService service = new TaskService(repository);

    Task task = service.add("cuatro");

    assertEquals(4, task.id());
  }

  @Test
  void rechazaTituloVacio() {
    TaskService service = new TaskService(new InMemoryTaskRepository());

    assertThrows(IllegalArgumentException.class, () -> service.add("   "));
  }

  @Test
  void rechazaRepositorioNulo() {
    assertThrows(NullPointerException.class, () -> new TaskService(null));
  }

  @Test
  void listViewsDevuelveDtos() {
    TaskService service = new TaskService(new InMemoryTaskRepository());
    service.add("estudiar");

    List<TaskView> views = service.listViews();

    assertEquals(List.of(new TaskView(1, "estudiar", false)), views);
  }
}
