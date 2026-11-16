package edu.teachers.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.List;
import org.junit.jupiter.api.Test;

/** Contrato que todo adaptador de TaskRepositoryPort debe cumplir. */
public abstract class TaskRepositoryContractTest {

  /**
   * Crea el adaptador bajo prueba.
   *
   * @return instancia limpia del puerto
   */
  protected abstract TaskRepositoryPort repository();

  @Test
  void guardaYLista() {
    TaskRepositoryPort repo = repository();
    Task task = new Task(1, "uno", false);

    repo.save(task);

    assertEquals(List.of(task), repo.all());
  }

  @Test
  void reemplazaPorId() {
    TaskRepositoryPort repo = repository();
    repo.save(new Task(1, "uno", false));

    repo.save(new Task(1, "dos", true));

    assertEquals(List.of(new Task(1, "dos", true)), repo.all());
  }
}
