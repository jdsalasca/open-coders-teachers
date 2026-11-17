# ADR-0017 — Robustez de la API Go y selección real del gate

- **Estado:** aceptada
- **Fecha:** 2026-11-16

## Contexto

Dos auditorías nuevas encontraron fallos concretos: el apagado de Go podía
cerrar SQLite antes de que terminaran los handlers; un commit que solo borraba
código podía no ejecutar el gate del lenguaje; `missing_tests` contaba tests del
árbol (incluidos `node_modules` o no versionados); una `Page` inválida podía
llegar al repositorio y provocar un pánico; `encoding/json` sustituía UTF-8
inválido por U+FFFD; y dos instancias SQLite podían competir por la misma clave.

## Decisiones

1. **Apagado ordenado**: `cmd/api` crea el listener, arranca `Shutdown` con
   `signal.NotifyContext` y `serve` espera a que el apagado termine antes de
   devolver. El `defer repository.Close()` corre después.
2. **Loopback por defecto**: `TASKS_ADDR` vale `127.0.0.1:8080`; exponer
   `0.0.0.0` es una decisión explícita. Auth, TLS y rate limiting siguen fuera
   del ejemplo (ADR-0015).
3. **`Page` se valida dos veces**: en `Service.List` y en cada adaptador. Una
   página inválida devuelve `ErrInvalidPage`; nunca llega a `make` con un
   límite negativo. El contrato la prueba.
4. **UTF-8 antes de JSON**: el controller rechaza el payload con
   `utf8.Valid` antes de decodificar; `encoding/json` no puede sustituir bytes
   inválidos por U+FFFD.
5. **SQLite multiinstancia**: el DSN añade `_txlock=immediate` y
   `busy_timeout=5000`; dos repositorios sobre el mismo archivo serializan
   escritores y la misma clave devuelve una sola tarea. Test dedicado.
6. **Borrados en el gate**: `staged_deleted` recoge las rutas borradas,
   `languages_of` las clasifica y `expand_deleted` ejecuta el gate completo del
   lenguaje afectado. Un commit que solo borra código ya no dice “Nada que
   revisar”. Los borrados de configuración también expanden.
7. **`missing_tests` mira el índice**: usa `git ls-files --cached`, no un
   `rglob` del árbol; tests en `node_modules` o sin stagear no cuentan.
8. **TS `start` idempotente**: arrancar dos veces no duplica listeners.
9. **Rust portable**: reconoce `cdylib`, `staticlib` y `dylib` como bibliotecas
   al elegir targets de clippy.
10. **Documentación honesta**: `--staged` selecciona rutas del índice, pero las
    herramientas leen el árbol; `staged_guard` rechaza archivos parcialmente
    staged y el check obligatorio es CI.

## Consecuencias

- El apagado no pierde respuestas ni cierra la base en medio de un handler.
- Un borrado de código ejecuta tests/lint del proyecto y puede fallar.
- Una página inválida es un error, no un pánico.
- Un JSON con bytes inválidos no se crea con el texto alterado.
- La idempotencia funciona con dos procesos sobre el mismo archivo SQLite.

## Límites

- SQLite serializa escritores; sigue siendo una sola conexión por instancia y
  no demuestra rendimiento bajo carga.
- `--staged` no valida exactamente el blob del índice: el hook es una ayuda,
  no un reemplazo de CI.
- La API sigue sin auth, TLS ni rate limiting.
- `missing_tests` exige al menos un test versionado por lenguaje, no cobertura
  por archivo.
