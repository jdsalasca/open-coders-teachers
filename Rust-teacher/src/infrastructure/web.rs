//! Frontera de entrada: JSON validado antes de tocar el dominio.

use serde::Deserialize;
use validator::{Validate, ValidationError, ValidationErrors};

use crate::application::{AppError, TaskService, TaskView};
use crate::domain::TaskRepositoryPort;

/// Peticion de creacion de tarea.
#[derive(Debug, Deserialize, Validate)]
pub struct CreateTaskRequest {
    /// Titulo obligatorio, no vacio y de hasta 200 caracteres.
    #[validate(length(min = 1, max = 200), custom(function = "validate_not_blank"))]
    pub title: String,
}

fn validate_not_blank(title: &str) -> Result<(), ValidationError> {
    if title.trim().is_empty() {
        return Err(ValidationError::new("blank"));
    }
    Ok(())
}

/// Errores de la frontera web.
#[derive(Debug, thiserror::Error)]
pub enum WebError {
    /// El payload no es JSON valido.
    #[error("payload invalido: {0}")]
    Json(#[from] serde_json::Error),
    /// Los datos no cumplen las reglas de validacion.
    #[error("datos invalidos: {0}")]
    Invalid(#[from] ValidationErrors),
    /// El caso de uso fallo.
    #[error(transparent)]
    Application(#[from] AppError),
}

/// Adaptador de entrada: valida DTOs y expone DTOs, nunca entidades.
#[derive(Debug)]
pub struct TaskController<R: TaskRepositoryPort> {
    service: TaskService<R>,
}

impl<R: TaskRepositoryPort> TaskController<R> {
    /// Inyecta el caso de uso.
    pub fn new(service: TaskService<R>) -> Self {
        Self { service }
    }

    /// Valida un payload JSON y crea la tarea.
    ///
    /// # Errors
    /// Devuelve [`WebError`] si el JSON o los datos no son validos o si falla la persistencia.
    pub fn create_from_json(&self, payload: &str) -> Result<TaskView, WebError> {
        let request: CreateTaskRequest = serde_json::from_str(payload)?;
        self.create(request)
    }

    /// Valida una peticion ya deserializada y crea la tarea.
    ///
    /// # Errors
    /// Devuelve [`WebError`] si los datos no son validos o si falla la persistencia.
    pub fn create(&self, request: CreateTaskRequest) -> Result<TaskView, WebError> {
        request.validate()?;
        let task = self.service.add(&request.title)?;
        Ok(TaskView::from(task))
    }

    /// Lista las tareas como DTO.
    ///
    /// # Errors
    /// Devuelve [`WebError`] si falla la persistencia.
    pub fn list(&self) -> Result<Vec<TaskView>, WebError> {
        self.service.list_views().map_err(WebError::from)
    }
}

#[cfg(test)]
mod tests {
    // Los tests fallan con panic a proposito.
    #![allow(clippy::expect_used, clippy::unwrap_used)]

    use super::{TaskController, WebError};
    use crate::application::TaskService;
    use crate::infrastructure::memory::InMemoryTaskRepository;

    fn controller() -> TaskController<InMemoryTaskRepository> {
        TaskController::new(TaskService::new(InMemoryTaskRepository::default()))
    }

    #[test]
    fn crea_con_un_payload_valido() {
        let view = controller()
            .create_from_json(r#"{"title":"estudiar"}"#)
            .unwrap();

        assert_eq!(1, view.id);
        assert_eq!("estudiar", view.title);
        assert!(!view.done);
    }

    #[test]
    fn rechaza_json_invalido() {
        assert!(matches!(
            controller().create_from_json("{"),
            Err(WebError::Json(_))
        ));
    }

    #[test]
    fn rechaza_titulo_en_blanco() {
        assert!(matches!(
            controller().create_from_json(r#"{"title":"   "}"#),
            Err(WebError::Invalid(_))
        ));
    }

    #[test]
    fn rechaza_titulo_largo() {
        let payload = format!(r#"{{"title":"{}"}}"#, "x".repeat(201));

        assert!(matches!(
            controller().create_from_json(&payload),
            Err(WebError::Invalid(_))
        ));
    }

    #[test]
    fn lista_devuelve_dtos() {
        let controller = controller();
        controller
            .create_from_json(r#"{"title":"estudiar"}"#)
            .unwrap();

        let views = controller.list().unwrap();

        assert_eq!(1, views.len());
        assert_eq!("estudiar", views[0].title);
    }

    #[test]
    fn serializa_el_dto() {
        let view = controller()
            .create_from_json(r#"{"title":"estudiar"}"#)
            .unwrap();

        let json = serde_json::to_value(view).unwrap();

        assert_eq!("estudiar", json["title"]);
    }
}
