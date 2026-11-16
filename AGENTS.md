# Contrato de calidad (obligatorio para agentes)

Todo código que escribas en este repo tiene que pasar el linter **antes** de
considerar la tarea terminada. No hay excepciones y no se ignoran warnings.

## Comando

```powershell
python tools/lint.py             # revisa todo el repo
python tools/lint.py --fix       # aplica arreglos automáticos y vuelve a revisar
python tools/lint.py --audit     # vulnerabilidades en dependencias (requiere red)
python tools/lint.py <carpeta>   # revisa una carpeta (ej. React-teacher)
python tools/lint.py <archivos>  # revisa solo esos archivos
```

Sale con código 1 si quedan problemas. El hook de git corre lo mismo sobre lo
que está en stage: **un commit con violaciones se rechaza** y devuelve el
reporte.

## Límites duros por lenguaje

| Regla | Python | TypeScript | React | Go | Java |
|---|---|---|---|---|---|
| Línea máxima | 100 | 100 | 100 | 100 | formatter |
| Parámetros por función | 4 | 4 | 4 | 4 | 4 |
| Líneas por función | 40 stmts | 40 | 40 | 40 | 40 |
| Complejidad ciclomática | 8 | 8 | 8 | 8 | 8 |
| Doc obligatoria en API pública | sí | sí | sí | sí | sí |
| Imports sin usar | error | error | error | error | error |
| Variables/parámetros sin usar | error | error | error | error | error |
| Tipos | mypy | tsc | tsc | compilador | compilador |
| Indentación | ruff format | prettier | prettier | gofmt | spotless |
| Orden de imports | ruff (I) | simple-import-sort | simple-import-sort | gofmt | google-java-format |
| Orden de miembros en clase | — | member-ordering | member-ordering | — | DeclarationOrder |
| Nombres | ruff (N) | naming-convention | naming-convention | revive | checkstyle |
| Duplicación | — | — | stylelint | dupl | — |
| Dependencias | — | — | knip | — | — |

Configs donde viven las reglas:

- `python-teacher/pyproject.toml` (ruff + mypy)
- `typescript-teacher/eslint.config.js` + `tsconfig.json`
- `React-teacher/eslint.config.js` + `stylelint.config.js` + `knip.json`
- `go-teacher/.golangci.yml`
- `Java-teacher/config/checkstyle/checkstyle.xml` + `pom.xml`

## Arquitectura: las capas no se rompen

Cada carpeta tiene una arquitectura declarada y **el linter la verifica**. Si el
import va hacia el lado equivocado, el commit falla.

| Carpeta | Capas permitidas | Verifica |
|---|---|---|
| `python-teacher` | `domain` ← `application` ← `infrastructure` | `lint-imports` |
| `go-teacher` | `internal/domain` ← `internal/app` ← `internal/adapters` | `depguard` |
| `Java-teacher` | `domain` ← `application` ← `infrastructure` | ArchUnit |
| `typescript-teacher` | `model` aislado; `controller` → `model` y `view`; `view` → `model` | `depcruise` |
| `React-teacher` | `model` ← `viewmodel` ← `view` (la vista no importa el modelo) | `depcruise` |

Reglas de dependencia:

- El dominio **no** conoce casos de uso, adaptadores, frameworks ni bases de
  datos. Habla con el exterior solo por puertos (interfaces/Protocols).
- La infraestructura implementa los puertos del dominio; no llama casos de uso.
- El composition root (`main.go`, `Main.java`, `main.ts`, `main.tsx`) es la
  única pieza que conoce todas las capas.
- Prohibido crear ciclos entre módulos.

## Reglas propias de React

- **Estilos solo en `.scss`.** Un archivo `.css` en `React-teacher` es error.
  El estilo inline (`style={{ ... }}`) también.
- **Sin duplicados**: `declaration-block-no-duplicate-properties`,
  `no-duplicate-selectors`, `shorthand-property-no-redundant-values`.
- **`@use`, nunca `@import`** en SCSS.
- **Tokens**: colores, espacios y radios salen de `src/styles/_tokens.scss`.
- **Dependencias**: `knip` falla con dependencias sin usar o imports que no
  están declarados en `package.json`.

## Cómo leer el reporte

Cada línea es `archivo:línea:columna  regla  mensaje`. Corrige la causa, no
silencies la regla. Si `--fix` ya puede resolverlo (formato, imports, comillas)
no lo toques a mano: corre `--fix` primero y revisa el diff.

## Prohibido

- `# noqa`, `// eslint-disable`, `//nolint`, `@SuppressWarnings` sin justificar
  por escrito en el mismo archivo el motivo técnico.
- Bajar límites del linter para que pase el código.
- `style={{ ... }}` o archivos `.css` en React.
- Commits con `--no-verify`.
