# teachers

Cuatro carpetas de enseñanza, cada una con su linter y un runner común que
convierte el lint en retroalimentación determinista para agentes.

```
python tools/lint.py            # revisa todo
python tools/lint.py --fix      # arregla lo arreglable y revisa
python tools/lint.py --staged   # solo lo staged (lo usa el hook)
```

## Instalación (una vez por clon)

```powershell
git config core.hooksPath .githooks      # hook de pre-commit
cd typescript-teacher; npm install       # eslint + prettier + tsc
cd Java-teacher      ; mvn -q compile    # baja checkstyle/spotless
```

Requisitos globales: `ruff`, `golangci-lint`, `mvn`, `node`, `python`.
`golangci-lint`: `winget install GolangCI.golangci-lint`.

## Qué hay en cada carpeta

| Carpeta | Stack | Reglas |
|---|---|---|
| `python-teacher` | Python 3.13 + ruff | `pyproject.toml` |
| `typescript-teacher` | TS 5.9 + ESLint 10 + Prettier | `eslint.config.js` |
| `go-teacher` | Go 1.27 + golangci-lint | `.golangci.yml` |
| `Java-teacher` | Java 25 + Checkstyle + Spotless | `pom.xml`, `config/checkstyle/` |

El contrato que deben seguir los agentes está en `AGENTS.md`.
