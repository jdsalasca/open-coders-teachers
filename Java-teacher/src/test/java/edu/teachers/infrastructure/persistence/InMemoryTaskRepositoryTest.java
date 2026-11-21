package edu.teachers.infrastructure.persistence;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import edu.teachers.domain.Task;
import edu.teachers.domain.TaskRepositoryContractTest;
import edu.teachers.domain.TaskRepositoryPort;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.stream.IntStream;
import org.junit.jupiter.api.Test;

/** El adaptador en memoria cumple el contrato y es concurrente. */
class InMemoryTaskRepositoryTest extends TaskRepositoryContractTest {

  @Override
  protected TaskRepositoryPort repository() {
    return new InMemoryTaskRepository();
  }

  @Test
  void devuelveListaInmutable() {
    TaskRepositoryPort repo = new InMemoryTaskRepository();
    repo.create("uno");
    List<Task> tasks = repo.list();

    assertThrows(UnsupportedOperationException.class, () -> tasks.add(new Task(9, "x", false)));
  }

  @Test
  void unaEntradaInvalidaNoAgregaYDejaHueco() {
    InMemoryTaskRepository repo = new InMemoryTaskRepository();

    assertThrows(IllegalArgumentException.class, () -> repo.create("   "));
    Task valid = repo.create("uno");

    assertEquals(2, valid.id());
    assertEquals(1, repo.list().size());
  }

  @Test
  void permiteElUltimoId() {
    InMemoryTaskRepository repo = new InMemoryTaskRepository(Integer.MAX_VALUE - 1);

    Task task = repo.create("uno");

    assertEquals(Integer.MAX_VALUE, task.id());
  }

  @Test
  void rechazaElAgotamientoDeIds() {
    InMemoryTaskRepository repo = new InMemoryTaskRepository(Integer.MAX_VALUE);

    assertThrows(IllegalStateException.class, () -> repo.create("uno"));
    assertTrue(repo.list().isEmpty());
  }

  @Test
  void creaIdsUnicosEnConcurrente() throws Exception {
    InMemoryTaskRepository repo = new InMemoryTaskRepository();
    ExecutorService pool = Executors.newFixedThreadPool(8);
    try {
      List<Future<Task>> futures =
          IntStream.range(0, 50)
              .mapToObj(index -> pool.submit(() -> repo.create("t" + index)))
              .toList();

      Set<Integer> ids = new HashSet<>();
      for (Future<Task> future : futures) {
        ids.add(future.get().id());
      }
      assertEquals(50, ids.size());
      List<Task> all = repo.list();
      assertEquals(50, all.size());
      for (int index = 0; index < all.size(); index++) {
        assertEquals(index + 1, all.get(index).id());
      }
    } finally {
      pool.shutdown();
    }
  }
}
