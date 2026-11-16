//! DTO de salida de una tarea.

use serde::Serialize;

use crate::domain::Task;

/// Vista de una tarea: el controller nunca devuelve la entidad.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct TaskView {
    /// Identificador unico.
    pub id: u64,
    /// Titulo de la tarea.
    pub title: String,
    /// Indica si ya esta completada.
    pub done: bool,
}

impl From<Task> for TaskView {
    fn from(task: Task) -> Self {
        Self {
            id: task.id(),
            title: task.title().to_owned(),
            done: task.done(),
        }
    }
}
