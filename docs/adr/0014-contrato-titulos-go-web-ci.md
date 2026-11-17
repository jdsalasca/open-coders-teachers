# ADR-0014 — Contrato común de títulos, frontera Go y CI fail-closed

- **Estado:** aceptada
- **Fecha:** 2026-11-16

## Contexto

Tres auditorías (currículo, consistencia entre los seis teachers y cadena de
suministro) encontraron divergencias reales: el máximo de 200 solo se aplicaba
en la frontera de Python/Java/Rust, Go no tenía frontera ni DTO, Python
devolvía la entidad, Java no garantizaba el orden de los IDs bajo concurrencia
y el cliente OSV podía reportar "limpio" ante una respuesta truncada.

## Decisiones

1. **Contrato único de título**: 1..200 code points Unicode, sin recortar, no
   blanco (incluido NBSP), validado en dominio y frontera. Implementado en
   Python (`len`), Java (`codePointCount` + `@CodePointLength`), Go
   (`utf8.RuneCountInString` + `utf8.ValidString`) y Rust (`chars().count()`).
2. **Go tiene frontera de entrada** en `internal/web`: DTO `TaskView`,
   `go-playground/validator/v10` (`required`, `max=200`, `notblank`), JSON
   estricto (campos desconocidos y datos extra fallan) y tests de protocolo.
   `depguard` impide que web importe adaptadores de salida.
3. **Python devuelve DTO** (`TaskView`) y tiene composition root (`app/main.py`);
   el controller ya no expone la entidad.
4. **Java usa un repositorio `synchronized`**: el orden de la lista coincide con
   los IDs y el agotamiento sigue fallando explícito en `Integer.MAX_VALUE`.
   El dominio valida 1..200 y NBSP; la frontera añade `@Pattern("(?sU).*\\S.*")`.
5. **OSV es fail-closed**: una respuesta sin `results`, con longitud distinta al
   número de paquetes o con tipos inesperados devuelve "verificación
   incompleta" (`2`), nunca "sin vulnerabilidades". Hay tests del parser.
6. **CI y cadena de suministro**:
   - Dependabot cubre también `pip` y `cargo`.
   - `--audit` incluye `tools/node` y Maven en scope `test`.
   - Gitleaks escanea el historial en CI, además del árbol.
   - Permisos mínimos, `persist-credentials: false`, timeouts y concurrencia en
     los workflows; `cargo-llvm-cov` fijado por versión.
7. **Go añade un fuzz test** de `NewTask` que corre con `go test` y se puede
   extender con `-fuzz`.

## Consecuencias

- Un título de 201 code points falla igual en las cuatro carpetas.
- Un título de solo NBSP se rechaza en Java, Python, Go y Rust.
- Go ya no acepta UTF-8 inválido ni payloads con campos desconocidos.
- Un fallo parcial de OSV no se disfraza de éxito.
- El orden de las tareas Java es determinista.

## Límites y siguientes pasos

- La auditoría curricular propone un recorrido HTTP + SQLite + paginación +
  idempotencia en un solo teacher de referencia. No se implementó aquí para no
  duplicar infraestructura en los seis ejemplos; queda como siguiente ronda.
- Hay SBOM informativo (SPDX) en CI, pero no control de licencias ni
  atestación de procedencia.
- La protección de rama y los checks obligatorios se configuran en GitHub, no
  en el repo.
- Python mantiene dependencias directas fijadas sin hashes transitivos.
- Go y Rust usan IDs del tamaño de la plataforma; no se añadió un contador
  inyectable porque el agotamiento físico no es alcanzable en el ejemplo.
- La cobertura sigue siendo agregada por carpeta; no es comparable entre
  lenguajes con denominadores distintos.
