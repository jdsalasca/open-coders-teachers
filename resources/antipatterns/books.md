# De los libros al linter

Cada principio de los libros canónicos, convertido (o no) en una regla
determinista. Si dice **manual**, ningún linter lo puede ver: está en el
catálogo de antipatrones para la revisión humana.

## Clean Code — Robert C. Martin

| Principio | Regla determinista | Dónde | Estado |
|---|---|---|---|
| Nombres que revelan intención (cap. 2) | `N` (ruff), `naming-convention`, `revive var-naming`, `TypeName`/`MethodName` | todas | automático |
| Evitar desinformación (`lista`, `data`, `tmp`) | naming + revisión de prefijos (`data`, `tmp` no están prohibidos por nombre) | manual | manual |
| Funciones pequeñas (cap. 3) | `funlen`, `max-lines-per-function`, `MethodLength`, `PLR0915` | todas | automático |
| Una sola cosa por función | `complexity` 8, `cyclop`, `C901` | todas | automático |
| Pocos argumentos | `max-params` 4, `PLR0913`, `ParameterNumber`, `revive argument-limit` | todas | automático |
| Sin argumentos bandera (`true`/`false`) | — | — | manual |
| Sin efectos secundarios | — | — | manual |
| Separar comandos de consultas | — | — | manual |
| Preferir excepciones a códigos de error | `errcheck` (Go), `throw` literal prohibido | Go, TS | parcial |
| No devolver `null` | `nilnil` (Go), `strictNullChecks` (TS) | Go, TS | parcial |
| Comentarios que explican el porqué | `D` (Python), jsdoc, Javadoc | todas | parcial (exige doc, no calidad) |
| Formato consistente | ruff format, Prettier, gofmt, Spotless | todas | automático |

## Refactoring — Martin Fowler

| Code smell | Regla determinista | Dónde | Estado |
|---|---|---|---|
| Long Method | ver Clean Code | todas | automático |
| Long Parameter List | ver Clean Code | todas | automático |
| Duplicate Code | `dupl`, `jscpd`, `no-duplicate-selectors` | Go, Node, SCSS | automático |
| Dead Code | `F401`/`F841`, `unused`, `knip`, `UnusedImports` | todas | automático |
| Large Class | `FileLength`, `ClassFanOutComplexity`, `interfacebloat` | Java, Go | parcial |
| Divergent Change / Shotgun Surgery | — | — | manual |
| Feature Envy | — | — | manual |
| Data Clumps | — | — | manual |
| Primitive Obsession | — | — | manual |
| Switch Statements | `MissingSwitchDefault`, `switch-exhaustiveness-check` | Java, TS | parcial |
| Speculative Generality | `unused`, `knip` | todas | parcial |
| Message Chains / Middle Man | — | — | manual |

## Code Complete — Steve McConnell

| Principio | Regla determinista | Dónde | Estado |
|---|---|---|---|
| Rutinas cortas | ver Clean Code | todas | automático |
| Complejidad ciclomática ≤ 8 | `complexity`, `cyclop`, `CyclomaticComplexity`, `C901` | todas | automático |
| Anidamiento ≤ 3 | `max-depth`, `NestedIfDepth`/`NestedForDepth`, `cyclop` | TS, React, Java, Go | automático |
| Números mágicos | — (los tokens SCSS cubren estilos) | — | manual |
| Variables con alcance mínimo | `no-shadow`, `HiddenField`, `predeclared`, `A` | todas | automático |
| Aserciones y manejo de errores | `errcheck`, `errorlint`, `EmptyBlock`, `no-empty`, `S` | todas | automático |
| Documentar cada rutina | `D`, jsdoc + `require-description`, `MissingJavadoc*` + `SummaryJavadoc` | todas | automático |
| Evitar `goto`/flujo enrevesado | `superfluous-else`, `early-return` (revive) | Go | parcial |

## Effective Java — Joshua Bloch

| Principio | Regla determinista | Dónde | Estado |
|---|---|---|---|
| Minimizar la visibilidad | `VisibilityModifier` | Java | automático |
| `equals` y `hashCode` juntos | `EqualsHashCode` | Java | automático |
| No capturar `Exception`/`Throwable` | `IllegalCatch`, `IllegalThrows` | Java | automático |
| No ignorar excepciones | `EmptyBlock`, `S110` (Python) | Java, Python | automático |
| Inmutabilidad | `record` + `final`, `readonly` (TS), `frozen` (Python) | todas | parcial (el tipo lo permite) |
| Interfaz pequeña | `interfacebloat` | Go | automático |
| Documentar la API pública | `MissingJavadocMethod`/`Type`, `SummaryJavadoc`, `NonEmptyAtclauseDescription` | Java | automático |
| No reasignar parámetros | `ParameterAssignment`, `no-param-reassign` | Java, TS | automático |

## Clean Architecture — Robert C. Martin

| Principio | Regla determinista | Dónde | Estado |
|---|---|---|---|
| Regla de dependencias (hacia adentro) | `import-linter`, `depguard`, ArchUnit, `dependency-cruiser` | las 5 carpetas | automático |
| Sin ciclos | `sin-ciclos` (depcruise), compilador | TS, React, Go, Java | automático |
| Puertos y adaptadores | contratos de capas + composición en `main` | Python, Go, Java | automático (estructura) |
| Lógica fuera de la vista | `vista-sin-modelo`, `modelo-aislado` | React, TS | automático |

## Accesibilidad (WCAG 2.2, no es un libro pero es estándar)

| Principio | Regla determinista | Dónde | Estado |
|---|---|---|---|
| Texto alternativo en imágenes | `jsx-a11y/alt-text` | React | automático |
| Todo control tiene etiqueta | `jsx-a11y/label-has-associated-control`, `anchor-is-valid` | React | automático |
| Roles y ARIA válidos | `jsx-a11y/role-*`, `aria-*` | React | automático |
| Navegación por teclado | `jsx-a11y/no-noninteractive-tabindex`, `click-events-have-key-events` | React | automático |
| Contraste | `scripts/check-design-contrast` (manual) | — | manual |

## The Pragmatic Programmer — Hunt & Thomas

| Principio | Regla determinista | Dónde | Estado |
|---|---|---|---|
| DRY | `dupl`, `jscpd`, Stylelint | Go, Node, SCSS | automático |
| No dejar ventanas rotas | CI + hook bloqueante | todo el repo | automático |
| No codificar secretos | `gitleaks` + `ruff S` + `gosec` | todo el repo | automático |
| Ortogonalidad | capas + `knip` | todas | parcial |

## TDD — Kent Beck

| Principio | Regla determinista | Dónde | Estado |
|---|---|---|---|
| Un test antes del código | cobertura mínima por carpeta | 5 carpetas | automático (piso) |
| Tests rápidos y aislados | runners nativos | 5 carpetas | automático |
| Refactorizar con la red verde | hook corre tests en cada commit | 5 carpetas | automático |
| Test que realmente afirma | `B011` (`assert False`), revisión | Python | parcial |

## Lo que ningún linter ve

Argumentos bandera, efectos secundarios, envidia de características, obsesión
por primitivos, números mágicos, cadenas de mensajes, clase intermediaria,
cambios divergentes, generalidad especulativa y la calidad de un comentario.
Están en [`code.md`](code.md) y [`architecture.md`](architecture.md) para que
la revisión humana sepa dónde mirar.
