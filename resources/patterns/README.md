# Patrones del repo y cómo se verifican

Cada patrón que este repo enseña tiene una regla que impide implementarlo mal.
Si el patrón no aparece aquí, es una convención oral: no cuenta.

## Patrones estructurales

| Patrón | Dónde vive | Cómo se verifica |
|---|---|---|
| **Ports & Adapters** (hexagonal) | `domain` define puertos `*Port`; `infrastructure` los implementa | `import-linter` (Python), `depguard` (Go), ArchUnit (Java), `tests/layers.rs` (Rust) |
| **Repository** | `TaskRepositoryPort` es el puerto; `InMemoryTaskRepository` el adaptador | ArchUnit: puertos terminan en `Port`; adaptadores viven en `infrastructure` y terminan en `Repository` |
| **Composition Root** | `main.go`, `Main.java`, `main.ts`, `main.tsx`, `main.rs` | convención: solo el root conoce todas las capas |
| **MVC** | `model` / `view` / `controller` | `dependency-cruiser`: `view` no importa `controller`; `model` aislado |
| **MVVM** | `model` / `viewmodel` / `view` | `dependency-cruiser`: `view` no importa `model`; `viewmodel` no importa `view` |
| **Contract Test** | Python (`tests/test_repository_contract.py`), Go (`internal/testutil`), Java (`TaskRepositoryContractTest`), Rust (`tests/repository_contract.rs`) | el mismo test corre contra cada adaptador nuevo |
| **DTO de salida** | `TaskView` en `application`; `TaskController` lo devuelve | ArchUnit: `..infrastructure.web..` no depende de `..domain..`; Rust: `TaskView` en `application` |
| **DTO de entrada validado** | `CreateTaskRequest` con Bean Validation; Pydantic en Python; serde + validator en Rust | el controller invoca el validador; tests de payload inválido |
| **Singleton sin estado** | beans `@Service`/`@Component`/`@RestController` | ArchUnit (se activa con Spring): solo campos `final` |

## Reglas de diseño que se hacen cumplir

| Principio | Regla determinista | Dónde |
|---|---|---|
| **DIP**: el dominio no conoce frameworks ni infraestructura | dominio solo `java..`/`..domain..` (ArchUnit), solo stdlib+dominio (depguard), capas (import-linter), `tests/layers.rs` (Rust) | Java, Go, Python, Rust |
| **SRP**: una clase, una razón de cambio | `FileLength`, `ClassFanOutComplexity`, 400 líneas (TS/Python/Rust) | todas |
| **OCP**: extender sin tocar `switch` | `exhaustive` (Go), `switch-exhaustiveness-check` (TS), `MissingSwitchDefault` (Java), `match` exhaustivo (Rust) | Go, TS, Java, Rust |
| **ISP**: interfaces pequeñas | `interfacebloat` máx. 10 | Go |
| **No exponer el dominio en la API** | `web_sin_dominio` (controllers usan DTOs) | Java, Rust |
| **Beans singleton sin estado** | `beans_sin_estado` (solo campos finales) | Java + Spring |
| **LSP / composición sobre herencia** | `max-classes-per-file: 1`, jerarquías planas | TS, React |
| **DRY** | `dupl`, `jscpd`, CPD, Stylelint | TS/React, Go, Java |
| **KISS**: sin anidamiento ni métodos largos | profundidad 3, 40 líneas, complejidad 8 | todas |

Las métricas de tamaño, complejidad y exhaustividad son **señales**, no pruebas
de SRP, OCP o LSP: un método de 40 líneas puede violar SRP igual. Lo que sí se
demuestra son las dependencias prohibidas y los ciclos.

## Antipatrones de patrón

| Antipatrón | Síntoma | Estado |
|---|---|---|
| **Singleton** | estado global accesible desde cualquier lado | manual (Go: `gochecknoglobals` lo dificulta) |
| **Service Locator** | `Container.get(X)` dentro de un método | manual |
| **God Object** | clase con 20 métodos y 15 campos | parcial (`ClassFanOutComplexity`, `FileLength`) |
| **Anemic Domain** | entidades sin comportamiento y lógica en servicios | manual |
| **Leaky Abstraction** | el dominio importa `sqlalchemy`, `jakarta.persistence`, `database/sql` | automático (capas y pureza del dominio) |
| **Singleton con estado** | un bean de Spring guarda datos de una petición | automático (solo campos finales) |
| **Yo-Yo** | herencia de 4+ niveles | manual |
| **Poltergeist** | clases que solo delegan | manual |
| **Golden Hammer** | la misma solución para todo | manual |
| **Primitive Obsession** | `String` para email, `int` para id de pedido | manual |

Los que no se automatizan están en el catálogo de antipatrones para que la
revisión humana sepa qué mirar. Ningún linter detecta un Singleton mal usado
sin falsos positivos.

## Añadir un patrón

1. Implementa un ejemplo mínimo en la carpeta que corresponda.
2. Escribe la regla que impide la versión incorrecta (capa, nombre, tamaño).
3. Añade un canario que falle si la regla deja de funcionar.
4. Documenta aquí la fila y en `AGENTS.md`.
