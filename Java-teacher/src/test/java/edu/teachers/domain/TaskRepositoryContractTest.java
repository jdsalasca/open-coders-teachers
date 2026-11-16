package edu.teachers.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;

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
  void creaIdsUnicos() {
    TaskRepositoryPort repo = repository();

    Task first = repo.create("uno");
    Task second = repo.create("dos");

    assertNotEquals(first.id(), second.id());
    assertEquals(List.of(first, second), repo.all());
  }
}
