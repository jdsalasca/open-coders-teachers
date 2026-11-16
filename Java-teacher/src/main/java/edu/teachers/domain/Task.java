package edu.teachers.domain;

/**
 * Tarea del dominio.
 *
 * @param id identificador unico
 * @param title titulo de la tarea
 * @param done si ya esta completada
 */
public record Task(int id, String title, boolean done) {}
