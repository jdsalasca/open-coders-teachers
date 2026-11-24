package edu.teachers.application;

import edu.teachers.domain.Task;

/**
 * DTO de salida de la aplicacion: no expone la entidad de dominio.
 *
 * @param id identificador
 * @param title titulo
 * @param done si esta completada
 */
public record TaskView(int id, String title, boolean done) {

  /**
   * Convierte una entidad en DTO.
   *
   * @param task entidad de dominio
   * @return vista de la tarea
   */
  public static TaskView from(final Task task) {
    return new TaskView(task.id(), task.title(), task.done());
  }
}
