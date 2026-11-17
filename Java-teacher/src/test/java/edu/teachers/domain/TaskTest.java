package edu.teachers.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

/** Pruebas de las invariantes del dominio. */
class TaskTest {

  @Test
  void aceptaElMaximoDeCaracteresUnicode() {
    String title = "😀".repeat(200);

    assertEquals(title, new Task(1, title, false).title());
  }

  @Test
  void rechazaTituloLargo() {
    String title = "😀".repeat(201);

    assertThrows(IllegalArgumentException.class, () -> new Task(1, title, false));
  }

  @Test
  void rechazaTituloConEspacioNoSeparable() {
    assertThrows(IllegalArgumentException.class, () -> new Task(1, "\u00a0", false));
  }

  @Test
  void conservaEspaciosAlrededorDelTexto() {
    assertEquals("  estudiar  ", new Task(1, "  estudiar  ", false).title());
  }

  @Test
  void rechazaIdCero() {
    assertThrows(IllegalArgumentException.class, () -> new Task(0, "estudiar", false));
  }

  @Test
  void rechazaTituloNulo() {
    assertThrows(NullPointerException.class, () -> new Task(1, null, false));
  }
}
