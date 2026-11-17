# ADR-0019 — Endurecer los linters de los teachers y del propio runner

- **Estado:** aceptada
- **Fecha:** 2026-11-17

## Contexto

El runner ya se lintaba a mano, pero el gate no pasaba `ruff` sobre `tools/` ni
validaba los workflows. En los teachers faltaban reglas para errores comunes:
Go no tenía `nilerr`, `noctx`, `contextcheck`, `rowserrcheck` ni
`sqlclosecheck`; Python no tenía `BLE`/`T20`; Java PMD no cazaba `System.out`,
`printStackTrace` ni `catch (Exception)`; y los tests Go no se ejecutaban con
orden aleatorio.

## Decisiones

1. **El gate lintela el runner**: `ruff check` y `ruff format --check` sobre
   `tools/` (con `tools/fixtures` excluido). El autochequeo sigue corriendo.
2. **Workflows con `actionlint`**: se instala en CI Linux y Windows y se ejecuta
   sobre `.github/workflows/`. Un cambio de workflow ahora es código validado.
3. **Go** añade `nilerr`, `noctx`, `contextcheck`, `rowserrcheck` y
   `sqlclosecheck`; `go test` corre con `-shuffle=on`.
4. **Python** añade `BLE` (except ciego) y `T20` (prints), con `T20` ignorado en
   `app/main.py` y `tools/**`.
5. **Java PMD** añade `SystemPrintln`, `AvoidPrintStackTrace` y
   `AvoidCatchingGenericException`; `Main` queda excluido de PMD por ser el
   composition root que imprime el ejemplo.
6. **Acciones**: `actionlint` y la lista de herramientas de `setup.ps1` se
   actualizan; el README documenta que el gate cubre tools y workflows.

## Consecuencias

- Un error de sintaxis o de expresión en un workflow falla el gate.
- El propio runner ya no puede quedar con imports/formatos sucios.
- Go detecta errores silenciados, contextos no heredados y recursos SQL sin
  cerrar.
- Python detecta `except` ciego y prints accidentales; Java detecta prints,
  stack traces y capturas genéricas.

## Límites

- `actionlint` es una herramienta externa: si falta, el runner devuelve `2`, no
  “limpio”.
- PMD excluye `Main` entero, no solo la regla de print.
- No se añadió `mypy` sobre `tools/` porque la fachada reexporta nombres y
  `no_implicit_reexport` exigiría un `__all__` completo; queda como siguiente
  paso.
- `-shuffle=on` usa una semilla aleatoria; si un test depende del orden, el
  fallo es real y debe corregirse, no fijar la semilla.
- Las reglas nuevas no sustituyen revisión humana ni cubren todos los
  antipatrones.
