package edu.teachers.infrastructure.web;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import edu.teachers.application.TaskService;
import edu.teachers.application.TaskView;
import edu.teachers.infrastructure.persistence.InMemoryTaskRepository;
import jakarta.validation.ConstraintViolationException;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import org.junit.jupiter.api.Test;

/** Pruebas de la frontera web con Bean Validation. */
class TaskControllerTest {

  private final Validator validator = Validation.buildDefaultValidatorFactory().getValidator();
  private final TaskController controller =
      new TaskController(new TaskService(new InMemoryTaskRepository()), validator);

  @Test
  void creaUnaTareaValida() {
    TaskView view = controller.create(new CreateTaskRequest("estudiar"));

    assertEquals("estudiar", view.title());
  }

  @Test
  void rechazaPeticionNula() {
    assertThrows(NullPointerException.class, () -> controller.create(null));
  }

  @Test
  void conservaEspacios() {
    TaskView view = controller.create(new CreateTaskRequest("  estudiar  "));

    assertEquals("  estudiar  ", view.title());
  }

  @Test
  void aceptaDoscientosCaracteresUnicode() {
    String title = "😀".repeat(200);

    TaskView view = controller.create(new CreateTaskRequest(title));

    assertEquals(title, view.title());
  }

  @Test
  void rechazaDoscientosUnoCaracteresUnicode() {
    CreateTaskRequest request = new CreateTaskRequest("😀".repeat(201));

    assertThrows(ConstraintViolationException.class, () -> controller.create(request));
  }

  @Test
  void rechazaTituloEnBlanco() {
    CreateTaskRequest request = new CreateTaskRequest("   ");

    assertThrows(ConstraintViolationException.class, () -> controller.create(request));
  }

  @Test
  void rechazaEspacioNoSeparable() {
    CreateTaskRequest request = new CreateTaskRequest("\u00a0");

    assertThrows(ConstraintViolationException.class, () -> controller.create(request));
  }

  @Test
  void rechazaTituloLargo() {
    CreateTaskRequest request = new CreateTaskRequest("x".repeat(201));

    assertThrows(ConstraintViolationException.class, () -> controller.create(request));
  }
}
