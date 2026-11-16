//! Entidades y puertos del negocio.

pub mod task;

pub use task::{DomainError, RepositoryError, Task, TaskRepositoryPort};
