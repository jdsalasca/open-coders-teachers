# ADR-0020 — Tipar el runner, lock de Python y cobertura de líneas nuevas

- **Estado:** aceptada
- **Fecha:** 2026-11-17

## Contexto

Quedaban tres huecos de calidad: el runner no pasaba `mypy`, Python instalaba
solo dependencias directas sin hashes, y la cobertura se medía de forma global
sin mirar las líneas nuevas de un PR. Además, los tests TS/React/Java no
aleatorizaban el orden.

## Decisiones

1. **`mypy` sobre `tools/`**: se añade `__all__` a la fachada `lint.py` para
   reexportar explícitamente lo que usan los tests, se anotan
   `walk_files`/`cargo_metadata`/`parse_alerts` y el gate ejecuta
   `mypy tools --config-file python-teacher/pyproject.toml`.
2. **Lock de Python**: `requirements.lock` generado con
   `uv pip compile requirements.txt --generate-hashes`; CI instala con
   `pip install --require-hashes` y `pip-audit` audita el lock.
3. **Cobertura de líneas nuevas**: `diff-cover --fail-under=80` en PRs.
   - XML: Python (`coverage.xml`) y Java (JaCoCo).
   - LCOV: TypeScript, React y Rust (se añade el reporter `lcov` a vitest y
     `--lcov` a `cargo llvm-cov`).
   - `diff-cover` no mezcla XML y LCOV en una sola invocación; se ejecuta por
     formato. Go aún no exporta un formato soportado.
4. **Orden aleatorio de tests**: `sequence.shuffle` en Vitest y
   `MethodOrderer$Random`/`ClassOrderer$Random` en JUnit 5.
5. **Rust y TS/React** generan `lcov.info`; el gate global sigue exigiendo los
   mínimos por carpeta.

## Consecuencias

- El runner tiene tipos verificados y una fachada de reexportación explícita.
- Una dependencia transitiva de Python no puede cambiar sin cambiar el lock.
- Un PR que añade líneas sin tests falla aunque la cobertura global siga alta.
- Un test que depende del orden se detecta en TS/React/Java.

## Límites

- `diff-cover` solo corre en PR; un push directo a `main` no lo ejecuta.
- Go no tiene lcov en este repo; su cobertura sigue siendo global y por `-cover`.
- `diff-cover` no mezcla XML y LCOV; son dos invocaciones.
- El orden aleatorio usa una semilla distinta cada ejecución; si algo falla, se
  corrige el test, no se fija la semilla.
- `mypy` cubre `tools/`, no los seis teachers (cada uno tiene su propio gate).
