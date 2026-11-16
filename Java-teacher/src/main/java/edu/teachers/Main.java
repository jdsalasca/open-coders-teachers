package edu.teachers;

import edu.teachers.application.TaskService;
import edu.teachers.application.TaskView;
import edu.teachers.infrastructure.persistence.InMemoryTaskRepository;
import edu.teachers.infrastructure.web.CreateTaskRequest;
import edu.teachers.infrastructure.web.TaskController;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import java.util.List;

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
    Validator validator = Validation.buildDefaultValidatorFactory().getValidator();
    TaskController controller = new TaskController(service, validator);
    controller.create(new CreateTaskRequest("estudiar"));
    List<TaskView> views = controller.list();
    System.out.println(views);
  }
}
