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
    if (title.isBlank()) {
      throw new IllegalArgumentException("el titulo no puede estar vacio");
    }
  }
}
