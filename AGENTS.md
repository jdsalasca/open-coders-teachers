# Contrato de calidad (obligatorio para agentes)

Todo código que escribas en este repo tiene que pasar el linter **antes** de
considerar la tarea terminada. No hay excepciones y no se ignoran warnings.

## Comando

```powershell
python tools/lint.py            # revisa todo el repo
python tools/lint.py --fix      # aplica arreglos automáticos y vuelve a revisar
python tools/lint.py <archivos> # revisa solo esos archivos
```

Sale con código 1 si quedan problemas. El hook de git corre lo mismo sobre lo
que está en stage: **un commit con violaciones se rechaza** y devuelve el
reporte.

## Límites duros por lenguaje

| Regla | Python | TypeScript | Go | Java |
|---|---|---|---|---|
| Línea máxima | 100 | 100 | 100 | 100 |
| Parámetros por función | 4 | 4 | 4 | 4 |
| Líneas por función | 40 | 40 | 40 | 40 |
| Complejidad ciclomática | 8 | 8 | 8 | 8 |
| Doc obligatoria en API pública | sí | sí | sí | sí |
| Imports sin usar | error | error | error | error |
| Variables/parámetros sin usar | error | error | error | error |
| Indentación | ruff format | prettier | gofmt | spotless |
| Orden de imports | ruff (I) | simple-import-sort | gofmt/goimports | checkstyle |
| Orden de miembros en clase | — | member-ordering | — | DeclarationOrder |
| Nombres | ruff (N) | naming-convention | revive | checkstyle |

Configs donde viven las reglas:

- `python-teacher/pyproject.toml` (ruff)
- `typescript-teacher/eslint.config.js` + `.prettierrc.json`
- `go-teacher/.golangci.yml`
- `Java-teacher/config/checkstyle/checkstyle.xml` + `pom.xml`

## Cómo leer el reporte

Cada línea es `archivo:línea:columna  regla  mensaje`. Corrige la causa, no
silencies la regla. Si `--fix` ya puede resolverlo (formato, imports, comillas)
no lo toques a mano: corre `--fix` primero y revisa el diff.

## Prohibido

- `# noqa`, `// eslint-disable`, `//nolint`, `@SuppressWarnings` sin justificar
  por escrito en el mismo archivo el motivo técnico.
- Bajar límites del linter para que pase el código.
- Commits con `--no-verify`.
