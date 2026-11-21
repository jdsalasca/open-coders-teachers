package edu.teachers.domain;

import java.util.List;

/** Puerto de persistencia: la infraestructura asigna el id. */
public interface TaskRepositoryPort {

  /**
   * Crea una tarea con id unico.
   *
   * @param title titulo de la tarea
   * @return tarea creada
   */
  Task create(String title);

  /**
   * Devuelve todas las tareas.
   *
   * @return lista de tareas
   */
  List<Task> list();
}
