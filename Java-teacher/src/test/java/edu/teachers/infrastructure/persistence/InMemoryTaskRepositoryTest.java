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
    List<Task> tasks = repo.all();

    assertThrows(UnsupportedOperationException.class, () -> tasks.add(new Task(9, "x", false)));
  }

  @Test
  void unaEntradaInvalidaNoAgregaYDejaHueco() {
    InMemoryTaskRepository repo = new InMemoryTaskRepository();

    assertThrows(IllegalArgumentException.class, () -> repo.create("   "));
    Task valid = repo.create("uno");

    assertEquals(2, valid.id());
    assertEquals(1, repo.all().size());
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
      assertTrue(repo.all().size() == 50);
    } finally {
      pool.shutdown();
    }
  }
}
