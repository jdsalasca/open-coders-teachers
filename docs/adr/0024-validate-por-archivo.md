# ADR-0024 — Reporte determinista por archivo (`--validate`)

- **Estado:** aceptada
- **Fecha:** 2026-11-17

## Contexto

El runner ejecutaba seis ecosistemas y devolvía la salida cruda de cada
herramienta. Un agente tenía que leer formatos distintos (JSON de Ruff, unix de
ESLint, XML de Checkstyle, JSON lines de Clippy, `path:line` de Go) y adivinar
qué defecto pertenecía a qué archivo y a qué aspecto. Los ejemplos y documentos
no resolvían eso: hacía falta una ruta determinista, repetible y barata.

## Decisión

`python tools/lint.py <ruta> --validate` ejecuta variantes estructuradas de los
linters y normaliza cada hallazgo en una violación con:

- `path`, `line`, `column`, `category`, `rule`, `message`, `tool` y `fixable`.

Categorías: `calidad`, `capas`, `nombres`, `acoplamiento`, `srp`,
`complejidad`, `imports`, `formato`, `tests` y `cobertura`.

Decisiones concretas:

1. **Salidas estructuradas donde existen**: Ruff JSON, ESLint JSON, Stylelint
   JSON, golangci-lint JSON, Clippy JSON lines, dependency-cruiser JSON, TSC,
   mypy y los XML que dejan Checkstyle, PMD y SpotBugs en `target/`.
2. **Fallback textual determinista**: `path:line:col` y listas de archivos para
   Prettier, rustfmt, Spotless, pytest, Vitest, Go test y ls-lint. Si una
   herramienta no da archivo y línea, se reporta la carpeta; no se inventa.
3. **Categoría por regla y herramienta**, no por IA: `N802`, `TypeName`,
   `naming-convention` y `revive` son `nombres`; `depcruise`, `depguard`,
   `lint-imports` y ArchUnit son `capas`; `C901`, `cyclop` y `complexity` son
   `complejidad`; `max-lines` y `FileLength` son `srp`; `simple-import-sort`,
   `gci` y `CustomImportOrder` son `imports`.
4. **`--json`** devuelve `total`, `summary` y `violations`, para que un agente
   filtre por archivo o categoría sin parsear texto.
5. **`--validate --fix`** aplica primero los arreglos seguros de cada
   herramienta y vuelve a validar. Nombres, complejidad, capas y SRP quedan como
   `manual`.
6. **Sin cambios en el gate**: `python tools/lint.py` y el hook siguen igual.
   `--validate` es una vista del mismo gate, no un gate paralelo.

## Consecuencias

- Un agente puede pedir el reporte de una carpeta o archivo y corregir por
  prioridad: capas, nombres, complejidad, imports.
- `--json` permite integrar el reporte en cualquier automatización.
- La clasificación es reproducible: la misma versión de la herramienta y la
  misma regla producen la misma categoría.
- El runner gana un módulo (`tools/lintlib/quality.py`) y tests de parser.

## Límites

- La cobertura de parsers es finita: una herramienta nueva necesita su parser y
  su test antes de prometer el reporte.
- Una regla desconocida cae en `calidad`; no se adivina la categoría.
- `--validate` no aplica a proyectos externos (`--project`) ni a `--audit`,
  `--security` o `--mutation`.
- Algunas herramientas solo permiten reportar a nivel de carpeta (por ejemplo,
  `lint-imports` o un fallo de build de Maven sin archivo).
- No sustituye la revisión de diseño: SRP, acoplamiento y nombres siguen
  necesitando criterio humano; el reporte los hace visibles, no los resuelve.
