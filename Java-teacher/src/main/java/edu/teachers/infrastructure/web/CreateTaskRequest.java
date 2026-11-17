package edu.teachers.infrastructure.web;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import org.hibernate.validator.constraints.CodePointLength;

/**
 * Peticion de creacion de tarea, validada en la frontera.
 *
 * @param title titulo obligatorio de hasta 200 caracteres (code points)
 */
public record CreateTaskRequest(
    @NotBlank @Pattern(regexp = "(?sU).*\\S.*") @CodePointLength(min = 1, max = 200)
        String title) {}
