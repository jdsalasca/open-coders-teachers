package edu.teachers.infrastructure.persistence;

import edu.teachers.domain.TaskRepositoryContractTest;
import edu.teachers.domain.TaskRepositoryPort;

/** El adaptador en memoria cumple el contrato del puerto. */
class InMemoryTaskRepositoryTest extends TaskRepositoryContractTest {

  @Override
  protected TaskRepositoryPort repository() {
    return new InMemoryTaskRepository();
  }
}
