//! Casos de uso de tareas: dependen solo del dominio.

use thiserror::Error;

use crate::application::view::TaskView;
use crate::domain::{RepositoryError, Task, TaskRepositoryPort};

/// Errores del caso de uso.
#[derive(Debug, Error, PartialEq, Eq)]
pub enum AppError {
    /// La persistencia fallo.
    #[error(transparent)]
    Repository(#[from] RepositoryError),
}

/// Orquesta tareas sobre el puerto del dominio.
#[derive(Debug)]
pub struct TaskService<R: TaskRepositoryPort> {
    repository: R,
}

impl<R: TaskRepositoryPort> TaskService<R> {
    /// Inyecta el puerto de persistencia.
    pub fn new(repository: R) -> Self {
        Self { repository }
    }

    /// Crea una tarea; el repositorio asigna el id.
    ///
    /// # Errors
    /// Propaga [`AppError`] si la persistencia falla.
    pub fn add(&self, title: &str) -> Result<Task, AppError> {
        self.repository.create(title).map_err(AppError::from)
    }

    /// Lista las tareas guardadas.
    ///
    /// # Errors
    /// Propaga [`AppError`] si la persistencia falla.
    pub fn list(&self) -> Result<Vec<Task>, AppError> {
        self.repository.list().map_err(AppError::from)
    }

    /// Lista las tareas como DTO de salida.
    ///
    /// # Errors
    /// Propaga [`AppError`] si la persistencia falla.
    pub fn list_views(&self) -> Result<Vec<TaskView>, AppError> {
        Ok(self
            .repository
            .list()?
            .into_iter()
            .map(TaskView::from)
            .collect())
    }
}

#[cfg(test)]
mod tests {
    // Los tests fallan con panic a proposito.
    #![allow(clippy::expect_used, clippy::unwrap_used)]

    use std::sync::Mutex;
    use std::sync::atomic::{AtomicBool, Ordering};

    use super::{AppError, TaskService};
    use crate::application::TaskView;
    use crate::domain::{RepositoryError, Task, TaskRepositoryPort};

    #[derive(Default)]
    struct FakeRepository {
        fail: AtomicBool,
        tasks: Mutex<Vec<Task>>,
    }

    impl FakeRepository {
        fn failing() -> Self {
            Self {
                fail: AtomicBool::new(true),
                tasks: Mutex::new(Vec::new()),
            }
        }
    }

    impl TaskRepositoryPort for FakeRepository {
        fn create(&self, title: &str) -> Result<Task, RepositoryError> {
            if self.fail.load(Ordering::Relaxed) {
                return Err(RepositoryError::Unavailable);
            }
            let mut tasks = self.tasks.lock().expect("lock");
            let id = u64::try_from(tasks.len() + 1).expect("id");
            let task = Task::new(id, title, false)?;
            tasks.push(task.clone());
            Ok(task)
        }

        fn list(&self) -> Result<Vec<Task>, RepositoryError> {
            if self.fail.load(Ordering::Relaxed) {
                return Err(RepositoryError::Unavailable);
            }
            let tasks = self.tasks.lock().expect("lock");
            Ok(tasks.clone())
        }
    }

    #[test]
    fn agrega_una_tarea_valida() {
        let service = TaskService::new(FakeRepository::default());

        let task = service.add("estudiar").unwrap();

        assert_eq!(1, task.id());
        assert_eq!("estudiar", task.title());
    }

    #[test]
    fn propaga_el_error_del_repositorio() {
        let service = TaskService::new(FakeRepository::failing());

        assert_eq!(
            Err(AppError::Repository(RepositoryError::Unavailable)),
            service.add("estudiar")
        );
    }

    #[test]
    fn lista_las_tareas() {
        let service = TaskService::new(FakeRepository::default());
        service.add("uno").unwrap();
        service.add("dos").unwrap();

        let tasks = service.list().unwrap();

        assert_eq!(2, tasks.len());
    }

    #[test]
    fn lista_como_dtos() {
        let service = TaskService::new(FakeRepository::default());
        service.add("estudiar").unwrap();

        let views = service.list_views().unwrap();

        assert_eq!(
            vec![TaskView {
                id: 1,
                title: "estudiar".to_owned(),
                done: false
            }],
            views
        );
    }

    #[test]
    fn list_views_propaga_el_error() {
        let service = TaskService::new(FakeRepository::failing());

        assert_eq!(
            Err(AppError::Repository(RepositoryError::Unavailable)),
            service.list_views()
        );
    }
}
