# ADR-0016 — Baseline portable a partir de proyectos reales

- **Estado:** aceptada
- **Fecha:** 2026-11-16

## Contexto

Se revisaron ~65 proyectos de `Programming-personal` (Rust, TypeScript/React,
Python, Java, Godot, algunos políglotas) para ver qué errores se repiten fuera
de los teachers. Los más comunes: `unwrap`/`expect`/`panic` en Rust, `any` y
`console.log` en TS/React, `except Exception` y `Any` en Python, `System.out`/
`printStackTrace`/`catch (Exception)` en Java, scripts Godot de miles de líneas
sin tests y archivos gigantes en todos los lenguajes. Además, el modo portable
tenía dos bugs: escaneaba `venv/` y mezclaba lenguajes en roots políglotas.

## Decisiones

1. **Descubrimiento por extensión y manifiesto**: `owner_of` prefiere el
   manifiesto del lenguaje del archivo. Un root con `package.json` y
   `requirements.txt` produce dos proyectos; `requirements.txt`,
   `build.gradle(.kts)` y `project.godot` se reconocen como manifiestos.
2. **Workspace Rust**: los crates miembros se funden en el root para ejecutar
   clippy una vez y no repetir avisos.
3. **Artefactos fuera**: `venv`, `env`, `site-packages`, `.tox`, `.nox`,
   `.tmp`, `.godot`, `jdk`, `.toolchains`, `vendor` y `third_party` no se
   escanean.
4. **Rust estricto en portable**: `cargo clippy` sobre lib/bin/example con
   `unwrap_used`, `expect_used`, `panic`, `todo`, `unimplemented` y `dbg_macro`
   como error. Los tests no se incluyen.
5. **TS/React**: `no-console` (permitiendo scripts/CLI/commands/config),
   `eqeqeq`, `no-var`, `prefer-const`, `no-eval`, `no-implied-eval`, además de
   `no-explicit-any`, `react/no-array-index-key` y `react/no-danger`.
6. **Python**: `T20` (prints), `BLE` (except ciego), `A` (builtins) y las reglas
   existentes; `T20` se ignora en scripts/CLI/tests.
7. **Java**: Semgrep `p/java` + reglas propias para `System.out` fuera de
   `Main`/`Application`, `printStackTrace` y `catch (Exception)`.
8. **Godot**: `gdlint` y `gdformat --check` cuando hay `project.godot`.
9. **Tamaño e higiene**: fuentes de más de 400 líneas (sin tests ni generados)
   fallan; faltar tests, CI o README se avisa sin bloquear.
10. **Tests del runner**: descubrimiento políglota, fusión de workspace,
    tamaño portable, avisos y flags de targets.

## Consecuencias

- Auditar el árbol completo con `--project` ya no mezcla Python con Node ni
  pierde los scripts Godot.
- Un `unwrap` o un `catch (Exception)` en un proyecto externo se ve en el
  reporte, aunque el proyecto no tenga la config del teacher.
- Los archivos gigantes se detectan antes de que el agente los haga más
  grandes.
- El reporte incluye avisos de higiene que no bloquean pero orientan.

## Límites

- El código vendido (por ejemplo `side-projects/codex`) se sigue escaneando si
  no está en una carpeta ignorada; el ruido es esperable.
- No hay escaneo de secretos en portable; para eso está `--security` en el repo.
- No hay baseline específico de C/C++, C# ni Kotlin; se agrupan como Java o se
  ignoran.
- `gdlint` puede fallar con sintaxis Godot nueva; el reporte lo muestra como
  hallazgo, no como "limpio".
- El tamaño excluye tests y generados; un archivo de test gigante no falla.
- Los avisos de tests/CI/README buscan en ancestros hasta el root auditado.
