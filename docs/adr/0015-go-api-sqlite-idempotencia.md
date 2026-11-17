# ADR-0015 — Go como referencia HTTP, SQLite, paginación e idempotencia

- **Estado:** aceptada
- **Fecha:** 2026-11-16

## Contexto

La auditoría curricular propuso un único recorrido de referencia con HTTP,
persistencia, paginación e idempotencia, en lugar de replicar infraestructura en
los seis teachers. Go es la opción con menos piezas: `net/http` y
`database/sql` son stdlib y `modernc.org/sqlite` evita cgo en Windows.

## Decisiones

1. **API HTTP** en `internal/web` con `net/http`:
   - `POST /tasks` (201 nueva, 200 replay), `GET /tasks?limit&offset` y
     `GET /healthz`.
   - `Content-Type: application/json`, cuerpo máximo 1 MiB, errores JSON sin
     detalles internos, timeouts y apagado ordenado.
2. **SQLite** en `internal/adapters/sqlite` con `modernc.org/sqlite`:
   - tablas `tasks` e `idempotency`, WAL, `busy_timeout` y una sola conexión;
   - IDs asignados por la base (`AUTOINCREMENT`);
   - `Open` crea el esquema, `Close` cierra.
3. **Paginación** con `domain.Page` (`limit` 1..100, `offset >= 0`); la API usa
   20 por defecto y ordena por id.
4. **Idempotencia** con `Idempotency-Key` opcional de hasta 100 caracteres:
   - la clave se guarda en la misma transacción que la tarea;
   - un replay devuelve la tarea original con `200` y `Created=false`;
   - el test concurrente con la misma clave comprueba una sola fila.
5. **Contrato del puerto** en `internal/testutil`: IDs únicos, replay,
   orden y paginación; corre contra memoria y SQLite.
6. **Composición** en `cmd/api`: `TASKS_DB` (defecto `tasks.db`) y `TASKS_ADDR`
   (defecto `127.0.0.1:8080`), `signal.NotifyContext` para apagado y espera
   explícita del `Shutdown` antes de cerrar SQLite.
7. **Tests** de handler con `httptest` (201/200, JSON inválido, campos
   desconocidos, datos extra, nulo, blanco, NBSP, 200/201 emoji, 413, 415,
   405, 404, 500 sin detalle), de SQLite (reinicio y concurrencia) y fuzz de
   `NewTask`.

## Consecuencias

- El repo enseña una petición completa sin convertir los seis teachers en
  servicios.
- La idempotencia sobrevive a reinicios porque vive en SQLite.
- La API no filtra errores internos y limita cuerpo y paginación.
- Los otros teachers siguen siendo ejemplos mínimos y comparables.

## Límites

- Una sola conexión y un solo proceso: no demuestra bloqueos entre instancias.
- Sin autenticación, TLS, rate limiting ni migraciones versionadas; se
  documentan como pasos de despliegue.
- La API no se conecta al frontend React; el E2E sigue siendo local.
- Hay SBOM informativo (SPDX); licencias y procedencia siguen pendientes.
