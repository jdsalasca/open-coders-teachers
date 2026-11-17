# ADR-0018 — Modularizar el runner sin romper la entrada `lint.py`

- **Estado:** aceptada
- **Fecha:** 2026-11-17

## Contexto

`tools/lint.py` concentraba selección, ejecución, seguridad, auditoría y modo
portable en ~1900 líneas, por encima de la regla de 400 que el repo aplica a sus
teachers. La auditoría pidió extraer módulos gradualmente y conservar la
entrada, el hook y los tests existentes.

## Decisiones

1. **Paquete `tools/lintlib/`**:
   - `common.py`: constantes, `Command`, `Lang`, `LANGS`, descubrimiento de
     archivos, ejecución de comandos y utilidades de proceso.
   - `portable.py`: `Project`, descubrimiento por manifiesto/extensión,
     workspace Rust, baselines Node/Python/Go/Rust/Java/Godot, tamaño y avisos.
   - `audit.py`: gitleaks/Semgrep/gosec, mutation testing, OSV, Dependabot y
     auditoría de dependencias.
2. **`tools/lint.py` queda como fachada**: conserva `parse_args`, `main`,
   `repo_mode`, los chequeos de repo y la API que usan `test_lint.py` y el
   plugin (`ROOT`, `LANGS`, `expand`, `missing_tests`, etc.).
3. **Cambios de un módulo del runner disparan el gate completo**: cualquier
   `tools/lintlib/*.py` se trata como configuración global en
   `add_config_langs`.
4. **Sin cambios de comportamiento**: mismos códigos de salida, argumentos,
   mensajes y comandos. La extracción se valida con `test_lint.py`, el gate
   completo y CI Linux/Windows.
5. **Pruebas nuevas**: configuración de `lintlib`, descubrimiento políglota,
   workspace Rust, tamaño portable, avisos y flags de targets.

## Consecuencias

- `lint.py` baja de ~1900 a ~809 líneas; `common` ~465, `portable` ~384 y
  `audit` ~373.
- El modo portable y la auditoría se pueden probar y modificar sin tocar el CLI.
- El hook y el plugin siguen invocando `python tools/lint.py` igual que antes.

## Límites

- `lint.py` todavía contiene `repo_mode`, los chequeos de repo y el skip; la
  siguiente extracción natural es `repo.py`/`execution.py`.
- `common.py` supera 400 líneas; es cohesivo, pero se puede dividir en modelos y
  runtime si crece.
- No se movieron los tests a un paquete; siguen siendo un autochequeo simple.
- La extracción no cambia la semántica de `--staged` ni la cobertura.
