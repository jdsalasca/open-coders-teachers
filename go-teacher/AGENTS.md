# go-teacher

Go 1.27.4 (CI 1.27). Linter: **golangci-lint** (`.golangci.yml`) + `gofmt`.
Es el **teacher de referencia**: API HTTP + SQLite + paginación + idempotencia.

```powershell
cd go-teacher
$env:TASKS_DB = "tasks.db"
go run ./cmd/api                     # escucha en :8080
python tools/lint.py --fix go-teacher
```

## Arquitectura hexagonal

```text
cmd/api/              composition root: config, SQLite, servidor HTTP
internal/domain/      entidades, paginacion y puertos. No importa app, web ni adapters.
internal/app/         casos de uso. Importa domain.
internal/web/         adaptador de entrada: valida DTOs, HTTP y errores publicos.
internal/adapters/    adaptadores de salida (memoria, sqlite): implementan puertos.
```

`depguard` bloquea los imports que rompen esa direccion: dominio solo stdlib y
dominio; adaptadores de salida no importan app; web no importa adaptadores.

## API HTTP

| Metodo | Ruta | Respuesta |
|---|---|---|
| `POST` | `/tasks` | `201` nueva, `200` replay idempotente, `400/413/415` |
| `GET` | `/tasks?limit=20&offset=0` | `200` con `items`, `limit` y `offset` |
| `GET` | `/healthz` | `200 {"status":"ok"}` |

- `Content-Type: application/json` obligatorio; cuerpo máximo 1 MiB.
- `Idempotency-Key` opcional (máx. 100): la misma clave devuelve la tarea
  original con `200` y no duplica.
- `limit` debe estar entre 1 y 100; `offset` no puede ser negativo.
- Errores públicos: JSON `{"error":"..."}` sin filtrar detalles internos.
- Timeouts de lectura/escritura y apagado ordenado con `SIGINT`.
- Configuración: `TASKS_DB` (defecto `tasks.db`) y `TASKS_ADDR` (defecto `:8080`).

## Persistencia

SQLite con `modernc.org/sqlite` (puro Go, sin cgo). Dos tablas: `tasks` e
`idempotency` (clave primaria + FK). WAL, `busy_timeout` y una sola conexión
para evitar bloqueos en el ejemplo. Al reiniciar, las tareas y las claves
persisten. El contrato del puerto vive en `internal/testutil` y corre contra
memoria y SQLite.

## Reglas

`unused`, `unparam`, `ineffassign`, `errcheck`, `govet`, `staticcheck`,
`revive` (exported, var-naming, arg-limit 4, cognitive 8, unused-parameter),
`funlen` (40 lineas / 40 statements), `cyclop` (8), `dupl` (bloques de 100+
tokens), `lll` (100), `gocritic`, `misspell`, `nakedret`, `gosec`,
`errorlint`, `modernize` y `depguard`.

Todo lo exportado lleva doc comment que empieza con el nombre del simbolo.
`Task` tiene campos privados y getters (`ID()`, `Title()`, `Done()`): el valor
cero no es valido y `NewTask` es la unica via de construccion. El titulo se
conserva sin recortar, debe ser UTF-8 valido, no puede ser blanco y admite hasta
200 runas (`ErrTitleTooLong`).

`internal/web` usa `go-playground/validator/v10` (`required`, `max=200`,
`notblank`) y devuelve `TaskView`, nunca `Task`. JSON estricto: campos
desconocidos y datos extra fallan.

## Tests

`*_test.go` en el mismo paquete. El runner corre `go test ./...` con perfil de
cobertura y exige 50% total; un paquete sin tests no suma. Fuera de Windows
añade `-race` (en Windows exige cgo/gcc y se omite).

- `internal/testutil` fija el contrato: IDs únicos, idempotencia, orden y
  paginación; corre contra memoria y SQLite.
- `internal/adapters/sqlite` prueba persistencia tras reinicio y concurrencia
  con la misma clave.
- `internal/web` prueba 201/200, JSON inválido, campo desconocido, datos extra,
  nulo, blanco, NBSP, 200/201 emoji, 413, 415, 405, 404, paginación y error
  interno sin detalle.
- `FuzzNewTask` corre con `go test` y con `go test -fuzz=FuzzNewTask`.
