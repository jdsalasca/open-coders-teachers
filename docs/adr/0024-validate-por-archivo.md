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
7. **Proyectos externos**: `--project <ruta> --validate` reutiliza el
   descubrimiento portable y los mismos parsers. Rust usa un baseline de diseño
   (`many_single_char_names`, `too_many_lines`, `cognitive_complexity`,
   `too_many_arguments`, `module_name_repetitions`, imports comodín, `unwrap`/
   `expect`/`panic`) con umbrales en `tools/rust/clippy.toml` (40 líneas, 8 de
   complejidad, 4 parámetros). Los casts numéricos quedan fuera del baseline
   externo para no ahogar el reporte; el teacher de Rust los cubre con
   `pedantic`.
8. **Java externo**: Checkstyle y PMD con configs portables
   (`tools/java/checkstyle.xml`, `tools/java/pmd.xml`) y un analizador propio
   (`tools/lintlib/java_quality.py`) que exige dominio sin JPA/Spring/Lombok,
   capas hacia dentro (`service` no importa `web`/`repo`, `web` no importa
   `repo`), DTOs sin tipos del dominio, `@RestController`/`@Service`,
   inyección por constructor, mappers fuera del servicio y tests unitarios por
   servicio. Checkstyle/PMD requieren Maven; Gradle conserva el analizador y
   Semgrep.
9. **Resto de lenguajes**: `tools/lintlib/architecture.py` aplica las mismas
   reglas de capas a Python, Go, Rust y TypeScript/React (`domain` no importa
   application/infrastructure/web; `application` no importa infraestructura ni
   web; `model`/`lib`/`components` no importan capas superiores). El dominio no
   importa frameworks (SQLAlchemy/Django/FastAPI/Pydantic, GORM/Gin/Echo,
   Serde/Axum/Tokio/SQLx). `tools/lintlib/test_quality.py` exige tests, limita
   su tamaño y casos, y exige al menos una aserción; `tools/lintlib/ts_quality.py`
   exige JSDoc en exports. Rust añade `missing_docs`.
10. **Solo el diff**: `--base <rama>` (alias `--changed`) usa el merge-base
    `rama...HEAD` y limita el reporte a los archivos tocados. Funciona en el
    repo y en `--project`; `--fix` respeta el alcance. Un cambio de manifiesto
    o configuración vuelve a auditar el proyecto completo. Sin `--base` el
    análisis es completo. El wrapper `tools/quality.ps1` expone
    `-Project`, `-Base`, `-Fix` y `-Json`.
11. **DIP y puertos operacionales**: `tools/lintlib/abstractions.py` exige
    abstracciones de 1..4 métodos con nombre de verbo, sin interfaces de
    framework (`JpaRepository`/`CrudRepository`). En Java y TypeScript detecta
    servicios/controladores que dependen de clases concretas de
    infraestructura/adapters/repo; en Python, Go y Rust la dirección de capas
    impide esa dependencia. El gate del repo aplica las mismas reglas a los
    teachers; los puertos `all()` se renombraron a `list()`.

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
- En proyectos externos, `--validate` usa el baseline portable: no ejecuta los
  tests ni la cobertura del proyecto, ni los plugins de Maven. Para el gate
  completo hay que usar el runner del proyecto. Los tests se revisan de forma
  estática (existencia, tamaño, casos y aserciones), no se ejecutan.
- `--validate` no aplica a `--audit`, `--security` ni `--mutation`; para
  proyectos externos sí aplica junto a `--project`.
- Checkstyle/PMD de Java externo asumen Maven; Gradle solo recibe el
  analizador de arquitectura y Semgrep.
- La arquitectura portable reconoce capas por nombre (`domain`, `application`,
  `infrastructure`, `web`, `api`, `adapters`, `repo`, `model`, `view`,
  `controller`, `viewmodel`, `pages`, `components`, `lib`). Un proyecto con
  otros nombres no recibe esas reglas; no se adivina la capa.
- Algunas herramientas solo permiten reportar a nivel de carpeta (por ejemplo,
  `lint-imports` o un fallo de build de Maven sin archivo).
- No sustituye la revisión de diseño: SRP, acoplamiento y nombres siguen
  necesitando criterio humano; el reporte los hace visibles, no los resuelve.
