# Contrato de calidad (obligatorio para agentes)

Todo código que escribas en este repo tiene que pasar el linter **antes** de
considerar la tarea terminada. No hay excepciones y no se ignoran warnings.

## Comando

```powershell
python tools/lint.py             # revisa todo el repo
python tools/lint.py --fix       # aplica arreglos automáticos y vuelve a revisar
python tools/lint.py --fix --unsafe  # incluye arreglos que cambian comportamiento
python tools/lint.py --audit     # vulnerabilidades en dependencias (requiere red)
python tools/lint.py --security  # secretos, patrones inseguros y dependencias
python tools/lint.py --project "ruta"  # audita un proyecto externo
python tools/lint.py --json      # resumen estructurado
python tools/lint.py --mutation  # mutation testing (Stryker)
python tools/lint.py --fast <archivo>  # un archivo, sin tests ni capas
python tools/lint.py --skip "motivo"  # permite el próximo commit sin linters
python tools/lint.py <carpeta>   # revisa una carpeta (ej. React-teacher)
python tools/lint.py <archivos>  # revisa solo esos archivos
```

Sale con código 1 si quedan problemas. El hook de git corre lo mismo sobre lo
que está en stage: **un commit con violaciones se rechaza** y devuelve el
reporte. CI (`.github/workflows/ci.yml`) corre lo mismo en cada push a `main`
y en cada pull request.

## Lint en cada edición

El plugin `.opencode/plugins/lint-on-edit.ts` corre `--fast` sobre el archivo que
acabas de escribir y pega el reporte en el resultado de la herramienta. Si el
reporte aparece, corrígelo antes de seguir; el commit volverá a verificar todo.

## Patrones y ADR

Los patrones que usa el repo están en `resources/patterns/README.md`. Si cambias
una config de arquitectura (`eslint.config.js`, `.golangci.yml`,
`checkstyle.xml`, `.dependency-cruiser.js`, `stryker.conf.json`,
`pyproject.toml`, `pom.xml`), agrega un ADR en `docs/adr/` o el PR falla.

## Proyectos externos

`--project <ruta>` detecta proyectos por `package.json`, `go.mod`,
`pyproject.toml` o `pom.xml` y aplica el baseline portable. Si el reporte dice
que un proyecto no se pudo verificar, **no lo reportes como limpio**: dilo.

## Skip de emergencia (solo con permiso humano)

Si un commit es urgente y el linter está bloqueando por algo que no puedes
arreglar en ese momento:

1. **Pide confirmación al humano antes de hacerlo.** Explícale qué reglas vas a
   permitir, qué archivos entran y por qué no puedes corregirlos ahora.
2. Solo con su aprobación explícita:

```powershell
python tools/lint.py --skip "motivo concreto del skip"
git commit -m "..."        # el hook muestra el aviso y deja pasar ESTE commit
```

El permiso es de **un solo uso**, caduca en 10 minutos y queda registrado en
`.git/lint-skip.log`. El aviso que imprime el hook es no bloqueante y dice:
*"Pide confirmación del skip al humano, dile lo que vas a permitir y el porqué
antes de hacerlo."* No es una autorización retroactiva: si el agente lo usó sin
preguntar, el commit se revisa y se corrige igual.

## TDD: primero el test

1. Escribe el test que falla (nombre en español, una intención por test).
2. Escribe el mínimo código que lo hace pasar.
3. Refactoriza; el test sigue verde.

Un cambio sin test no está terminado. El runner ejecuta las pruebas de las
cinco carpetas y **falla si la cobertura baja del mínimo**:

| Carpeta | Runner | Mínimo |
|---|---|---|
| `python-teacher` | pytest + pytest-cov | 60% líneas (`app/`) |
| `typescript-teacher` | vitest + v8 | 80% líneas (`model`, `controller`) |
| `React-teacher` | vitest + v8 + jsdom | 80% líneas (`model`, `viewmodel`) |
| `go-teacher` | `go test` + `go tool cover` | 50% total |
| `Java-teacher` | JUnit 5 + JaCoCo | 60% líneas |

Nombres de archivo: `test_*.py`, `*.test.ts`, `*.test.tsx`, `*_test.go`,
`*Test.java`.

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
| Orden de imports | ruff (I) | simple-import-sort | simple-import-sort | gci | google-java-format |
| Orden de miembros en clase | — | member-ordering | member-ordering | — | DeclarationOrder |
| Nombres | ruff (N, A) | naming-convention | naming-convention | revive, predeclared | checkstyle |
| Doc con descripción real | D + Google | jsdoc/require-description | jsdoc/require-description | revive exported | SummaryJavadoc |
| Sin reasignar parámetros | — | no-param-reassign | no-param-reassign | — | ParameterAssignment |
| Sin `init`/globales | — | — | — | gochecknoinits, gochecknoglobals | StaticVariableName |
| Duplicación | — | jscpd | jscpd + stylelint | dupl | — |
| Accesibilidad | — | — | `jsx-a11y` | — | — |
| Archivo/Clase grande | 400 líneas | 400 | 400 | 500 | FileLength 500, ClassFanOutComplexity |
| Dependencias | — | — | knip | — | — |

Configs donde viven las reglas:

- `python-teacher/pyproject.toml` (ruff + mypy + import-linter + pytest)
- `typescript-teacher/eslint.config.js` + `tsconfig.json` + `vitest.config.ts`
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
- **Sin tipos vagos**: `{}`, `Object` y `Function` están prohibidos; define la
  forma real. `any` también es error.
- **Dependencias**: `knip` falla con dependencias sin usar o imports que no
  están declarados en `package.json`.
- **Funciones duplicadas**: `jscpd` falla con clones de 70+ tokens.
- **Accesibilidad**: `jsx-a11y` (alt, labels, roles, tabindex).
- **Sin APIs deprecadas**: `no-deprecated` (con tipos) y `staticcheck` en Go.
- **DTOs en la API**: un controller nunca devuelve entidades de dominio (Java).
- **Puertos con nombre**: interfaces de dominio terminan en `Port`; adaptadores en `Repository`.
- **Docs**: markdownlint y enlaces locales se validan en cada commit.
- **Nombres**: `ls-lint` (py/go snake_case, java/tsx PascalCase).
- **Java**: PMD caza metodos/campos privados sin usar (`UnusedPrivate*`).
- **Property tests**: una propiedad por funcion pura (Hypothesis, fast-check, quick, jqwik).
- **E2E**: `npm run e2e` en React (Playwright + axe) antes de tocar la vista.
- **Politica propia**: `.semgrep/rules.yml` detecta patrones concretos (fetch/axios en la vista, storage fuera de capa, env filtrado, prints); un alias o API equivalente puede escapar.
- **Java**: compila a bytecode 21 (JDK 25) para que PIT y SpotBugs funcionen.
- **Dependencias**: `--audit` usa npm/govulncheck/pip-audit y OSV para Maven; Dependabot es el complemento cuando el token puede leer alertas.
- **Null-safety**: `Objects.requireNonNull` (Java), errores (Go), Pydantic (Python), `no-unsafe-*` (TS).
- **Validación**: Bean Validation en el controller Java, Pydantic en la frontera Python, Zod en TypeScript/React; el dominio mantiene invariantes.
- **IDs**: los asigna el repositorio (`AtomicInteger`, lock o mutex) y nunca el caso de uso; en producción los asigna la base de datos.

## Cómo leer el reporte

Cada línea es `archivo:línea:columna  regla  mensaje`. Corrige la causa, no
silencies la regla. Si `--fix` ya puede resolverlo (formato, imports, comillas)
no lo toques a mano: corre `--fix` primero y revisa el diff.

## Prohibido

- `# noqa`, `// eslint-disable`, `//nolint`, `@SuppressWarnings` sin justificar
  por escrito en el mismo archivo el motivo técnico.
- Bajar límites del linter o de cobertura para que pase el código.
- `style={{ ... }}` o archivos `.css` en React.
- Commits con `--no-verify`.
- Tests apagados (`.only`, `.skip`, `@Disabled`, `pytest.mark.skip`).
- Supresiones (`noqa`, `eslint-disable`, `nolint`) sin un motivo tras ` - ` o `--`.
- Mensajes de commit fuera de `tipo(scope): resumen` (los valida commitlint).
