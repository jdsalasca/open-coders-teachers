//! Adaptador en memoria: implementa el puerto de tareas.

use std::sync::Mutex;

use crate::domain::{RepositoryError, Task, TaskRepositoryPort};

/// Repositorio volatil, seguro entre hilos.
#[derive(Debug, Default)]
pub struct InMemoryTaskRepository {
    tasks: Mutex<Vec<Task>>,
}

impl TaskRepositoryPort for InMemoryTaskRepository {
    fn create(&self, title: &str) -> Result<Task, RepositoryError> {
        let mut tasks = self
            .tasks
            .lock()
            .map_err(|_| RepositoryError::Unavailable)?;
        let next = tasks.len() + 1;
        let id = u64::try_from(next).map_err(|_| RepositoryError::Unavailable)?;
        let task = Task::new(id, title, false)?;
        tasks.push(task.clone());
        Ok(task)
    }

    fn all(&self) -> Result<Vec<Task>, RepositoryError> {
        let tasks = self
            .tasks
            .lock()
            .map_err(|_| RepositoryError::Unavailable)?;
        Ok(tasks.clone())
    }
}

#[cfg(test)]
mod tests {
    // Los tests fallan con panic a proposito.
    #![allow(clippy::expect_used, clippy::unwrap_used)]

    use super::InMemoryTaskRepository;
    use crate::domain::{DomainError, RepositoryError, TaskRepositoryPort};

    #[test]
    fn no_agrega_una_tarea_invalida() {
        let repository = InMemoryTaskRepository::default();

        let error = repository.create("   ").unwrap_err();

        assert_eq!(RepositoryError::Domain(DomainError::EmptyTitle), error);
        assert!(repository.all().unwrap().is_empty());
    }

    #[test]
    fn devuelve_una_copia() {
        let repository = InMemoryTaskRepository::default();
        repository.create("uno").unwrap();

        let mut tasks = repository.all().unwrap();
        tasks.clear();

        assert_eq!(1, repository.all().unwrap().len());
    }
}
