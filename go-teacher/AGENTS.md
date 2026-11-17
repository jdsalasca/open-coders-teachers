# go-teacher

Go 1.26 (CI 1.27). Linter: **golangci-lint** (`.golangci.yml`) + `gofmt`.

```powershell
python tools/lint.py --fix go-teacher    # desde la raiz
go run ./cmd/api
```

## Arquitectura hexagonal

```text
cmd/api/              composition root: unica pieza que conoce todo
internal/domain/      entidades y puertos (interfaces). No importa app, web ni adapters.
internal/app/         casos de uso. Importa domain.
internal/web/         adaptador de entrada: valida DTOs y llama casos de uso.
internal/adapters/    adaptadores de salida: implementan puertos, nunca llaman app.
```

`depguard` bloquea los imports que rompen esa direccion: dominio solo stdlib y
dominio; adaptadores de salida no importan app; web no importa adaptadores.

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

`internal/web` es la frontera de entrada: usa `go-playground/validator/v10`
(`required`, `max=200`, `notblank`) y devuelve `TaskView`, nunca `Task`.

## Tests

`*_test.go` en el mismo paquete. El runner corre `go test ./...` con perfil de
cobertura y exige 50% total; un paquete sin tests no suma. Fuera de Windows
añade `-race` (en Windows exige cgo/gcc y se omite).

`internal/testutil` define el contrato del puerto; el adaptador en memoria se
prueba con 160 altas concurrentes (IDs únicos y cardinalidad) y con un contexto
que se cancela mientras espera el mutex. `internal/web` prueba JSON inválido,
campo desconocido, datos extra, nulo, blanco, NBSP, 200/201 emoji y propagación
del error del repositorio. `FuzzNewTask` corre con `go test` y con
`go test -fuzz=FuzzNewTask`.

- `gochecknoinits`, `gochecknoglobals`, `forcetypeassert`, `interfacebloat`,
  `nilnil`, `predeclared`, `containedctx`, `errname`; `gci` ordena imports.
