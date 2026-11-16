//! Verifica que las capas no se importen hacia el lado equivocado.

const DOMAIN: &str = include_str!("../src/domain/task.rs");
const SERVICE: &str = include_str!("../src/application/service.rs");
const VIEW: &str = include_str!("../src/application/view.rs");

#[test]
fn el_dominio_no_conoce_aplicacion_ni_infraestructura() {
    for forbidden in ["crate::application", "crate::infrastructure"] {
        assert!(!DOMAIN.contains(forbidden), "domain importa {forbidden}");
    }
}

#[test]
fn la_aplicacion_no_conoce_infraestructura() {
    for source in [SERVICE, VIEW] {
        assert!(
            !source.contains("crate::infrastructure"),
            "application importa infraestructura"
        );
    }
}
