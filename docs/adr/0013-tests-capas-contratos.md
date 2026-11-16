# ADR-0013 — Endurecer tests, capas y contratos en Java, Go y Python

- **Estado:** aceptada
- **Fecha:** 2026-11-16

## Contexto

Una auditoría enfocada en Java, Go y Python encontró cuatro huecos: borrar los
tests de una carpeta podía dejar el gate sin nada que ejecutar, el dominio
Python podía importar `app.interfaces`, `Task` en Go exponía sus campos y el
contador Java desbordaba tras `Integer.MAX_VALUE`. Además, el contrato de
títulos difería entre las tres carpetas.

## Decisiones

1. **El runner exige tests por lenguaje**: `Lang.test_glob` y
   `missing_tests()` fallan el gate si una carpeta se queda sin al menos un
   archivo de test. Cubre el caso de borrar `tests/` en el mismo commit.
2. **Go con `-race`** fuera de Windows: el runner añade `-race` en Linux/macOS.
   En Windows se omite porque exige cgo/gcc.
3. **Python cierra las capas**: `app.interfaces` entra en los contratos de
   `import-linter` y un test con AST (`tests/test_layers.py`) verifica
   domain/application. La frontera Pydantic rechaza blancos y **no recorta**;
   el dominio conserva el título.
4. **Go encapsula `Task`**: campos privados, getters `ID`/`Title`/`Done`,
   constructor `NewTask(id, title, done)`. El valor cero no es válido y el
   título admite hasta 200 runas (`ErrTitleTooLong`).
5. **La cancelación Go se prueba de verdad**: un `probeContext` avisa cuándo el
   adaptador comprueba el contexto; el test cancela mientras el mutex está
   tomado y exige que no haya mutación.
6. **Java no desborda IDs**: `updateAndGet` lanza `IllegalStateException` al
   llegar a `Integer.MAX_VALUE`; tests del último ID y del agotamiento.
7. **Límite Unicode común**: 1..200 code points, sin recortar, en las tres
   carpetas. Java usa `@CodePointLength` (no `@Size`, que cuenta UTF-16),
   Python valida con Pydantic y Go con `utf8.RuneCountInString`.
8. **Contratos concurrentes completos**: Python y Go comprueban cardinalidad y
   contenido, no solo IDs únicos.

## Consecuencias

- Un commit que borre todos los tests de una carpeta falla el gate.
- `domain` no puede mirar hacia `interfaces` en Python.
- Un `Task` Go no se puede construir ni mutar por campos.
- El contador Java falla explícito en el límite, sin IDs negativos.
- Los títulos con emoji cuentan igual en las tres carpetas.

## Límites

- `-race` no corre en Windows sin cgo/gcc; el CI Linux sí lo ejecuta.
- El gate de tests exige al menos un archivo por lenguaje, no una cobertura
  mínima por archivo.
- La normalización Unicode no se aplica: se conserva el texto original.
- Una entrada inválida sigue consumiendo un ID Java (hueco documentado).
