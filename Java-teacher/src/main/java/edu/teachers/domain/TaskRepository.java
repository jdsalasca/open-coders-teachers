package edu.teachers.domain;

import java.util.List;

/** Puerto de persistencia: lo implementa la infraestructura. */
public interface TaskRepository {

  /**
   * Guarda o actualiza una tarea.
   *
   * @param task tarea a guardar
   */
  void save(Task task);

  /**
   * Devuelve todas las tareas.
   *
   * @return lista de tareas
   */
  List<Task> all();
}
