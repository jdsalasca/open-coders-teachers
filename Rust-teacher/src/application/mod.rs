//! Casos de uso y DTOs de salida.

pub mod service;
pub mod view;

pub use service::{AppError, TaskService};
pub use view::TaskView;
