package edu.teachers.infrastructure.web;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * Peticion de creacion de tarea, validada en la frontera.
 *
 * @param title titulo obligatorio de hasta 200 caracteres
 */
public record CreateTaskRequest(@NotBlank @Size(max = 200) String title) {}
