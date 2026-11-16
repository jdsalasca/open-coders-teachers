# ADR-0012 — Sexto teacher: Rust con arquitectura hexagonal

- **Estado:** aceptada
- **Fecha:** 2026-11-16

## Contexto

El repo enseña cinco ecosistemas y faltaba Rust, donde los antipatrones
cambian de forma: `unwrap`/`expect` en lugar de nulos, `panic` en lugar de
errores, `unsafe` y `println!` fuera del composition root. También faltaba una
auditoría de dependencias para crates.io.

## Decisiones

1. **Crate único `Rust-teacher`**, edition 2024, toolchain fijada en
   `rust-toolchain.toml` (1.99 + clippy, rustfmt, llvm-tools-preview).
2. **Hexagonal**: `src/domain` (entidad + trait `TaskRepositoryPort`),
   `src/application` (caso de uso + DTO `TaskView`) y `src/infrastructure`
   (memoria + web). `src/main.rs` es el composition root.
3. **Capas verificadas** con `tests/layers.rs`: prohíbe que `domain` mencione
   `crate::application`/`crate::infrastructure` y que `application` mencione
   infraestructura.
4. **Errores tipados** con `thiserror`; el puerto devuelve
   `Result<Task, RepositoryError>` y el dominio valida id positivo y título no
   vacío. `unwrap`, `expect`, `panic`, `todo` y `unsafe` son lint error.
5. **Validación en la frontera** con `serde` (JSON) + `validator` (longitud y
   no-blanco); el controller valida antes de llamar al caso de uso.
6. **IDs por el repositorio**: `Mutex<Vec<Task>>`, id `len + 1` dentro del lock,
   tests de contrato y 160 altas concurrentes.
7. **Gates**: `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings` y
   `cargo llvm-cov --fail-under-lines 60`. `clippy.toml` fija 4 parámetros, 40
   líneas y complejidad 8. `missing_docs` obliga a documentar la API pública.
8. **Duplicación**: no se añadió `jscpd` para Rust; queda como límite (el resto
   de lenguajes sí lo tienen).
9. **Dependencias**: OSV con `ecosystem: crates.io` a partir de `Cargo.lock`;
   se versiona el lock para builds reproducibles.
10. **Semgrep**: `println!`/`eprintln!` solo en `main.rs`.
11. **CI**: toolchain instalada con `dtolnay/rust-toolchain` y
    `cargo-llvm-cov` con `taiki-e/install-action`, ambas fijadas por SHA.

## Consecuencias

- Un `unwrap` o un `panic` rompen el commit.
- El dominio no puede importar capas superiores ni frameworks de la web.
- La cobertura de Rust entra en el mismo gate que las otras cinco carpetas.
- `--audit` revisa Maven y crates.io sin token de GitHub.

## Límites

- `cargo llvm-cov` mide líneas totales del crate, incluido `main.rs`; no hay
  umbral por archivo.
- No hay mutation testing de Rust (`cargo-mutants`) ni análisis de duplicación.
- El adaptador es en memoria; la concurrencia se garantiza por proceso, no
  entre instancias.
- `serde` + `validator` viven en la frontera; el dominio mantiene sus
  invariantes a mano.
