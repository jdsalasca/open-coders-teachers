# Rust-teacher

Rust 1.99 (edition 2024). Linters: **rustfmt** + **clippy** (`Cargo.toml`,
`clippy.toml`) y cobertura con `cargo-llvm-cov`.

```powershell
python tools/lint.py --fix Rust-teacher   # desde la raiz
cd Rust-teacher; cargo run
```

## Arquitectura hexagonal

```text
src/domain/           entidades y puertos. No conoce application ni infrastructure.
src/application/      casos de uso y DTO de salida. Solo conoce domain.
src/infrastructure/   adaptadores (memoria, web). Implementan puertos del dominio.
src/main.rs           composition root: unica pieza que conoce todas las capas.
```

`tests/layers.rs` falla si el dominio menciona `crate::application` o
`crate::infrastructure`, o si application menciona infraestructura.

## Reglas

En `Cargo.toml`:

- `missing_docs = "deny"`: todo lo publico lleva doc comment.
- `unsafe_code = "forbid"`.
- Clippy `all` como error y, ademas, `unwrap_used`, `expect_used`, `panic`,
  `todo`, `unimplemented`, `dbg_macro`, `too_many_arguments` (4),
  `too_many_lines` (40) y `cognitive_complexity` (8).
- `clippy.toml` fija los umbrales de argumentos, lineas y complejidad.

Un `#[allow]` sin `reason = "..."` lo bloquea el gate (`--slop`). Los tests
pueden usar `unwrap`/`expect` con un `#![allow]` interno justificado.

## Tests

`#[cfg(test)]` en cada modulo y pruebas de integracion en `tests/`.

- `cargo test` corre unitarios, propiedad y contrato.
- `cargo llvm-cov --fail-under-lines 60` es el gate de cobertura (60% de
  lineas, total del crate).
- `proptest` cubre titulos y unicidad de ids.
- `tests/repository_contract.rs` valida el puerto y 160 altas concurrentes.
- `tests/layers.rs` hace cumplir la direccion de las capas.

## Notas

- `println!`/`eprintln!` solo en `src/main.rs`; Semgrep lo bloquea en el resto.
- Las dependencias se auditan con OSV a partir de `Cargo.lock` (`crates.io`).
- `Cargo.lock` se versiona: el ejemplo es un binario y la build debe ser
  reproducible.
