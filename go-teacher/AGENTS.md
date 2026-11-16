# go-teacher

Go 1.27. Linter: **golangci-lint** (`.golangci.yml`) + `gofmt`.

```powershell
python tools/lint.py --fix go-teacher    # desde la raiz
go run ./cmd/api
```

## Arquitectura hexagonal

```text
cmd/api/              composition root: unica pieza que conoce todo
internal/domain/      entidades y puertos (interfaces). No importa app ni adapters.
internal/app/         casos de uso. Importa domain.
internal/adapters/    implementan puertos. Importan domain, nunca app.
```

`depguard` bloquea los imports que rompen esa direccion, con el mensaje
`el dominio no conoce los casos de uso` o equivalente.

## Reglas

`unused`, `unparam`, `ineffassign`, `errcheck`, `govet`, `staticcheck`,
`revive` (exported, var-naming, arg-limit 4, cognitive 8, unused-parameter),
`funlen` (40 lineas / 40 statements), `cyclop` (8), `dupl` (bloques de 100+
tokens), `lll` (100), `gocritic`, `misspell`, `nakedret`, `gosec`,
`errorlint`, `modernize` y `depguard`.

Todo lo exportado lleva doc comment que empieza con el nombre del simbolo.

## Tests

`*_test.go` en el mismo paquete. El runner corre `go test ./...` con perfil de
cobertura y exige 50% total; un paquete sin tests no suma.

- `gochecknoinits`, `gochecknoglobals`, `forcetypeassert`, `interfacebloat`,
  `nilnil`, `predeclared`, `containedctx`, `errname`; `gci` ordena imports.
