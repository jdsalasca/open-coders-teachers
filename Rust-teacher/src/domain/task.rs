//! Tarea del dominio y puerto de persistencia.

use thiserror::Error;

/// Errores de las invariantes del dominio.
#[derive(Debug, Error, PartialEq, Eq)]
pub enum DomainError {
    /// El identificador no es positivo.
    #[error("el id debe ser positivo")]
    InvalidId,
    /// El titulo esta vacio o solo tiene espacios.
    #[error("el titulo no puede estar vacio")]
    EmptyTitle,
    /// El titulo supera [`MAX_TITLE_LENGTH`] caracteres.
    #[error("el titulo supera los 200 caracteres")]
    TitleTooLong,
}

/// Maximo de caracteres (code points) del titulo.
pub const MAX_TITLE_LENGTH: usize = 200;

/// Errores que puede devolver la infraestructura.
#[derive(Debug, Error, PartialEq, Eq)]
pub enum RepositoryError {
    /// La persistencia no esta disponible.
    #[error("el repositorio no esta disponible")]
    Unavailable,
    /// La tarea no cumple las invariantes del dominio.
    #[error(transparent)]
    Domain(#[from] DomainError),
}

/// Una tarea del dominio.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Task {
    id: u64,
    title: String,
    done: bool,
}

impl Task {
    /// Crea una tarea validando las invariantes.
    ///
    /// # Errors
    /// Devuelve [`DomainError`] si el id es cero o el titulo esta en blanco.
    pub fn new(id: u64, title: &str, done: bool) -> Result<Self, DomainError> {
        if id == 0 {
            return Err(DomainError::InvalidId);
        }
        if title.trim().is_empty() {
            return Err(DomainError::EmptyTitle);
        }
        if title.chars().count() > MAX_TITLE_LENGTH {
            return Err(DomainError::TitleTooLong);
        }
        Ok(Self {
            id,
            title: title.to_owned(),
            done,
        })
    }

    /// Identificador unico.
    #[must_use]
    pub fn id(&self) -> u64 {
        self.id
    }

    /// Titulo de la tarea, sin recortar.
    #[must_use]
    pub fn title(&self) -> &str {
        &self.title
    }

    /// Indica si la tarea esta completada.
    #[must_use]
    pub fn done(&self) -> bool {
        self.done
    }
}

/// Puerto de persistencia: lo implementa la infraestructura.
pub trait TaskRepositoryPort: Send + Sync {
    /// Crea una tarea con id unico asignado por el repositorio.
    ///
    /// # Errors
    /// Devuelve [`RepositoryError`] si la persistencia falla o el titulo es invalido.
    fn create(&self, title: &str) -> Result<Task, RepositoryError>;

    /// Devuelve una copia de todas las tareas.
    ///
    /// # Errors
    /// Devuelve [`RepositoryError`] si la persistencia falla.
    fn all(&self) -> Result<Vec<Task>, RepositoryError>;
}

#[cfg(test)]
mod tests {
    // Los tests fallan con panic a proposito.
    #![allow(clippy::expect_used, clippy::unwrap_used)]

    use super::{DomainError, MAX_TITLE_LENGTH, Task};

    #[test]
    fn crea_una_tarea_valida() {
        let task = Task::new(1, "estudiar", false).unwrap();

        assert_eq!(1, task.id());
        assert_eq!("estudiar", task.title());
        assert!(!task.done());
    }

    #[test]
    fn rechaza_id_cero() {
        assert_eq!(Err(DomainError::InvalidId), Task::new(0, "estudiar", false));
    }

    #[test]
    fn rechaza_titulo_en_blanco() {
        assert_eq!(Err(DomainError::EmptyTitle), Task::new(1, "   ", false));
    }

    #[test]
    fn conserva_el_titulo_sin_recortar() {
        let task = Task::new(1, "  estudiar  ", false).unwrap();

        assert_eq!("  estudiar  ", task.title());
    }

    #[test]
    fn acepta_el_maximo_de_caracteres() {
        let title = "😀".repeat(MAX_TITLE_LENGTH);

        let task = Task::new(1, &title, false).unwrap();

        assert_eq!(title, task.title());
    }

    #[test]
    fn rechaza_titulo_largo() {
        let title = "😀".repeat(MAX_TITLE_LENGTH + 1);

        assert_eq!(Err(DomainError::TitleTooLong), Task::new(1, &title, false));
    }

    #[test]
    fn rechaza_espacio_no_separable() {
        assert_eq!(Err(DomainError::EmptyTitle), Task::new(1, "\u{a0}", false));
    }
}
