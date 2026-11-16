# go-teacher

Go 1.27. Linter: **golangci-lint** (`.golangci.yml`) + `gofmt`.

```powershell
python tools/lint.py --fix go-teacher    # desde la raiz
```

Reglas activas: `unused`, `unparam`, `ineffassign`, `errcheck`, `govet`,
`staticcheck`, `revive` (exported, var-naming, arg-limit 4, cognitive 8,
unused-parameter), `funlen` (40 lineas / 40 statements), `cyclop` (8),
`dupl` (bloques duplicados de 100+ tokens), `lll` (100), `gocritic`,
`misspell`, `nakedret`.

Todo lo exportado lleva doc comment que empieza con el nombre del simbolo.
