package edu.teachers.domain;

import java.util.Objects;

/**
 * Tarea del dominio.
 *
 * @param id identificador unico
 * @param title titulo de la tarea
 * @param done si ya esta completada
 */
public record Task(int id, String title, boolean done) {

  /** Valida las invariantes del dominio. */
  public Task {
    if (id < 1) {
      throw new IllegalArgumentException("el id debe ser positivo");
    }
    Objects.requireNonNull(title, "title");
    if (title.codePoints().allMatch(Task::isSpace)) {
      throw new IllegalArgumentException("el titulo no puede estar vacio");
    }
    if (title.codePointCount(0, title.length()) > 200) {
      throw new IllegalArgumentException("el titulo supera los 200 caracteres");
    }
  }

  private static boolean isSpace(int codePoint) {
    return Character.isWhitespace(codePoint) || Character.isSpaceChar(codePoint);
  }
}
