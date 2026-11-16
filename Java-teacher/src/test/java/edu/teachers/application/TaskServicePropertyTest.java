package edu.teachers.application;

import static org.junit.jupiter.api.Assertions.assertEquals;

import edu.teachers.infrastructure.persistence.InMemoryTaskRepository;
import net.jqwik.api.ForAll;
import net.jqwik.api.Property;
import net.jqwik.api.constraints.NotBlank;
import net.jqwik.api.constraints.StringLength;

/** Propiedades del caso de uso. */
class TaskServicePropertyTest {

  @Property
  void elTituloSiempreSeConserva(@ForAll @NotBlank @StringLength(max = 40) String title) {
    TaskService service = new TaskService(new InMemoryTaskRepository());

    assertEquals(title, service.add(title).title());
  }
}
