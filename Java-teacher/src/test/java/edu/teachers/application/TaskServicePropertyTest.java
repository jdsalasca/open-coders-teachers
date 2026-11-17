package edu.teachers.application;

import static org.junit.jupiter.api.Assertions.assertEquals;

import edu.teachers.infrastructure.persistence.InMemoryTaskRepository;
import net.jqwik.api.Arbitraries;
import net.jqwik.api.Arbitrary;
import net.jqwik.api.ForAll;
import net.jqwik.api.Property;
import net.jqwik.api.Provide;

/** Propiedades del caso de uso. */
class TaskServicePropertyTest {

  @Property
  void elTituloSiempreSeConserva(@ForAll("titulosValidos") String title) {
    TaskService service = new TaskService(new InMemoryTaskRepository());

    assertEquals(title, service.add(title).title());
  }

  @Provide
  Arbitrary<String> titulosValidos() {
    return Arbitraries.strings()
        .withCharRange('a', 'z')
        .withCharRange('A', 'Z')
        .withCharRange('0', '9')
        .withChars(' ', '-', '_')
        .ofMinLength(1)
        .ofMaxLength(40)
        .filter(TaskServicePropertyTest::tieneTexto);
  }

  private static boolean tieneTexto(String value) {
    return value
        .codePoints()
        .anyMatch(
            codePoint -> !Character.isWhitespace(codePoint) && !Character.isSpaceChar(codePoint));
  }
}
