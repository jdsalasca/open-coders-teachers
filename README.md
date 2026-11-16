# open-coders-teachers

Cinco carpetas de enseñanza, cada una con el linter de su ecosistema y **un solo
runner** que convierte el lint en retroalimentación determinista para agentes de
IA.

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?logo=typescript&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Go](https://img.shields.io/badge/Go-1.27-00ADD8?logo=go&logoColor=white)
![Java](https://img.shields.io/badge/Java-25-ED8B00?logo=openjdk&logoColor=white)
[![lint](https://github.com/jdsalasca/open-coders-teachers/actions/workflows/ci.yml/badge.svg)](https://github.com/jdsalasca/open-coders-teachers/actions/workflows/ci.yml)

> El problema no es que la IA escriba código rápido. Es que lo escribe con
> variables muertas, funciones de 200 líneas, cinco parámetros, nombres
> inventados, estilos duplicados y capas rotas. Aquí cada uno de esos defectos
> es un error que se ve antes del commit.

## Arranque rápido

```powershell
git clone https://github.com/jdsalasca/open-coders-teachers.git
cd open-coders-teachers
pwsh tools/setup.ps1          # instala dependencias y activa el hook
python tools/lint.py          # revisa todo
python tools/lint.py --audit  # vulnerabilidades en dependencias
```

`tools/setup.ps1` activa `.githooks/pre-commit`, hace `npm install` en las dos
carpetas de Node y compila el proyecto Maven una vez para cachear los plugins.

## Cómo funciona

```mermaid
flowchart LR
  A["git commit"] --> B["pre-commit hook"]
  B --> C["tools/lint.py --staged"]
  C --> D{"¿pasa?"}
  D -- "sí" --> E["commit"]
  D -- "no" --> F["reporte: archivo:línea regla mensaje"]
  F --> G["el agente corrige"]
  G --> A
```

Un único punto de entrada, `tools/lint.py`, detecta el lenguaje por carpeta y
extensión, y ejecuta lo que corresponda:

| Comando | Qué hace |
|---|---|
| `python tools/lint.py` | revisa todo el repo (incluye archivos sin trackear) |
| `python tools/lint.py --fix` | aplica arreglos automáticos y vuelve a revisar |
| `python tools/lint.py --staged` | solo lo que está en el índice (lo usa el hook) |
| `python tools/lint.py --audit` | vulnerabilidades conocidas en dependencias |
| `python tools/lint.py --security` | secretos, patrones inseguros y dependencias |
| `python tools/lint.py --skip "motivo"` | permite el próximo commit sin linters (un solo uso) |
| `python tools/lint.py --fix --unsafe` | arreglos que pueden cambiar comportamiento |
| `python tools/lint.py --project <ruta>` | audita un proyecto externo (manifiesto) |
| `python tools/lint.py React-teacher` | una carpeta |
| `python tools/lint.py src/App.tsx` | un archivo |

Códigos de salida: `0` limpio, `1` problemas, `2` falta una herramienta.

## Testing y TDD

Primero el test que falla, después el código que lo hace pasar. El runner
ejecuta las pruebas de las cinco carpetas en cada commit y **falla si la
cobertura baja del mínimo**:

| Carpeta | Runner | Mínimo | Archivo |
|---|---|---|---|
| `python-teacher` | pytest + pytest-cov | 60% | `tests/test_*.py` |
| `typescript-teacher` | vitest + v8 | 80% | `src/**/*.test.ts` |
| `React-teacher` | vitest + v8 + jsdom | 80% | `src/**/*.test.tsx?` |
| `go-teacher` | `go test` + `go tool cover` | 50% | `*_test.go` |
| `Java-teacher` | JUnit 5 + JaCoCo | 60% | `*Test.java` |

```powershell
cd typescript-teacher; npm run test    # vitest + cobertura
cd React-teacher;       npm run test
cd python-teacher;      pytest --cov=app
cd go-teacher;          go test ./... -cover
cd Java-teacher;        mvn test
```

## Estructura

```
open-coders-teachers/
├── python-teacher/      ruff + mypy + import-linter + pytest   hexagonal
├── typescript-teacher/  ESLint 10 + tsc + depcruise + vitest   MVC
├── React-teacher/       ESLint + Stylelint + knip + vitest     MVVM
├── go-teacher/          golangci-lint + depguard + go test     hexagonal
├── Java-teacher/        Checkstyle + Spotless + ArchUnit + JaCoCo hexagonal
├── tools/
│   ├── lint.py          runner único
│   ├── test_lint.py     autochequeo del runner
│   └── setup.ps1        instalación en un clon nuevo
├── resources/
│   └── antipatterns/    catálogo: síntoma, arreglo y regla que lo caza
├── .githooks/           hook de pre-commit
└── AGENTS.md            contrato que siguen los agentes
```

## Arquitectura por capas

Cada carpeta demuestra una arquitectura y **la hace cumplir**. Si el agente
importa hacia el lado equivocado, el commit falla.

```mermaid
flowchart LR
  subgraph hex["Hexagonal (Python, Go, Java)"]
    I[Infrastructure] --> A[Application] --> D[Domain]
  end
  subgraph mvc["MVC (TypeScript)"]
    C[Controller] --> V[View]
    C --> M[Model]
    V --> M
  end
  subgraph mvvm["MVVM (React)"]
    VW[View] --> VM[ViewModel] --> MO[Model]
  end
```

| Carpeta | Capas | Herramienta | Regla |
|---|---|---|---|
| `python-teacher` | `domain` ← `application` ← `infrastructure` | `import-linter` | `pyproject.toml` |
| `go-teacher` | `internal/domain` ← `internal/app` ← `internal/adapters` | `depguard` | `.golangci.yml` |
| `Java-teacher` | `domain` ← `application` ← `infrastructure` | ArchUnit | `ArchitectureTest` |
| `typescript-teacher` | `model` ← `view`, `controller` → ambos | `dependency-cruiser` | `.dependency-cruiser.js` |
| `React-teacher` | `model` ← `viewmodel` ← `view` | `dependency-cruiser` | `.dependency-cruiser.js` |

La infraestructura implementa puertos del dominio; el composition root
(`main.go`, `Main.java`, `main.ts`, `main.tsx`) es la única pieza que conoce
todas las capas.

## Qué caza cada carpeta

| Defecto típico de la IA | Python | TypeScript | React | Go | Java |
|---|---|---|---|---|---|
| Imports / variables sin usar | ruff `F` | `no-unused-vars` | `no-unused-vars` | `unused`, `unparam` | `UnusedImports`, `UnusedLocalVariable` |
| Función demasiado larga | `PLR0915` | `max-lines-per-function` | `max-lines-per-function` | `funlen` | `MethodLength` |
| Demasiados parámetros | `PLR0913` | `max-params` | `max-params` | `revive argument-limit` | `ParameterNumber` |
| Nombres malos | ruff `N` | `naming-convention` | `naming-convention` | `revive var-naming` | `TypeName`, `MethodName`, … |
| Sin documentación | ruff `D` | `jsdoc/require-jsdoc` | `jsdoc/require-jsdoc` | `revive exported` | `MissingJavadoc*` |
| Orden de miembros | — | `member-ordering` | `member-ordering` | — | `DeclarationOrder` |
| Anidamiento profundo | `C901` | `max-depth` | `max-depth` | `cyclop` | `NestedIfDepth` |
| Código duplicado | — | `jscpd` | `jscpd` + Stylelint | `dupl` | — |
| Estilos duplicados | — | — | Stylelint | — | — |
| Rompe capas | `import-linter` | `dependency-cruiser` | `dependency-cruiser` | `depguard` | ArchUnit |
| Dependencias circulares | — | `dependency-cruiser` | `dependency-cruiser` | compilador | compilador |
| Dependencias muertas | — | — | `knip` | — | — |
| Vulnerabilidades (código) | ruff `S` | ESLint | ESLint | `gosec` | `IllegalCatch` |
| Vulnerabilidades (deps) | `pip-audit` | `npm audit` | `npm audit` | `govulncheck` | OWASP (manual) |
| Sin tests / poca cobertura | pytest-cov | vitest | vitest | `go tool cover` | JaCoCo |
| Promesas sin `await` | — | `no-floating-promises` | `no-floating-promises` | — | — |
| Tipos | `mypy` | `tsc` | `tsc` + sin tipos vagos | compilador | compilador |
| Indentación | `ruff format` | Prettier | Prettier | `gofmt` | Spotless |

## Auditar un proyecto externo

```powershell
python tools/lint.py --project C:\ruta\al\proyecto
python tools/lint.py --project C:\ruta\al\proyecto --fix
```

También detecta la ruta externa si se la pasas directo (`python tools/lint.py
C:\ruta`). El modo portable **descubre proyectos por manifiesto**, sin importar
el nombre de las carpetas:

| Manifiesto | Baseline |
|---|---|
| `package.json` | ESLint + Stylelint + dependency-cruiser (ciclos) |
| `go.mod` | golangci-lint (sin reglas de capas) |
| `pyproject.toml` | ruff |
| `pom.xml` | avisa que no hay baseline portable |

Antes, apuntar el runner a un monorepo React devolvía `Nada que revisar` y
salía con 0: solo conocía sus cinco carpetas. Ahora, si encuentra archivos pero
ningún manifiesto, **falla con código 2** en vez de fingir que está limpio.

El baseline portable aplica reglas de calidad, no opiniones de estilo:
`no-unused-vars`, `no-explicit-any`, `max-params: 4`, `max-lines-per-function:
40`, `complexity: 8`, `max-depth: 3`, reglas de React, `eslint-plugin-security`,
duplicados de SCSS y ciclos entre módulos. Los tests quedan exentos de los
límites de tamaño.

Límites conocidos: no ejecuta `tsc` ni los tests del proyecto externo (necesita
sus dependencias), y Java solo se advierte. Un resultado `2` significa "no pude
verificar", nunca "está limpio".

## Seguridad

```powershell
python tools/lint.py --security   # gitleaks + semgrep + gosec + auditoría de deps
python tools/lint.py --audit      # solo dependencias
```

| Capa | Herramienta | Qué busca |
|---|---|---|
| Secretos | `gitleaks` | claves, tokens y credenciales filtradas |
| Patrones inseguros | `semgrep --config p/ci` | inyección, deserialización, supply-chain en CI |
| Go | `gosec` | crypto débil, path traversal, TLS inseguro |
| Python | `ruff S` (bandit) | `eval`, `subprocess` con shell, secretos |
| Node | `eslint-plugin-security` | `eval`, regex DoS, object injection |
| Dependencias | `npm audit`, `govulncheck`, `pip-audit` | CVEs conocidas |

Semgrep corre también en CI, y de hecho encontró dos problemas reales en el
propio workflow (actions con tag movible y `curl | sh`): ambos se corrigieron
fijando los SHA y descargando el binario antes de instalarlo.

## Skip de emergencia

Si un agente necesita saltarse el hook, **primero pide permiso al humano** y
explica qué reglas va a permitir y por qué:

```powershell
python tools/lint.py --skip "motivo concreto"
git commit -m "..."    # pasa una vez, con aviso no bloqueante
```

El permiso caduca en 10 minutos, es de un solo uso y queda en
`.git/lint-skip.log`. El aviso recuerda explícitamente que hay que pedir
confirmación humana antes de hacerlo.

## Antipatrones

El catálogo vive en [`resources/antipatterns/`](resources/antipatterns/README.md):
síntoma, por qué duele, cómo se arregla y **qué regla lo bloquea**. Los que no
se pueden automatizar están marcados como *manual* para que la revisión humana
sepa dónde mirar.

- [`code.md`](resources/antipatterns/code.md): método largo, banderas
  booleanas, números mágicos, duplicación, clases todopoderosas.
- [`architecture.md`](resources/antipatterns/architecture.md): violación de
  capas, ciclos, dominio anémico, service locator.
- [`frontend.md`](resources/antipatterns/frontend.md): estilos inline,
  duplicados, `useEffect` para estado derivado, índice como key.
- [`testing.md`](resources/antipatterns/testing.md): tests que no prueban nada,
  orden implícito, mocks de todo, `assert` desactivado.

## Reglas de React (SCSS)

- Estilos **solo** en `.scss` modules: un `.css` en `React-teacher` es error.
- `style={{ ... }}` está prohibido por ESLint.
- `declaration-block-no-duplicate-properties`, `no-duplicate-selectors` y
  `shorthand-property-no-redundant-values` cazan estilos repetidos.
- `@use` en lugar de `@import`; tokens centralizados en `src/styles/_tokens.scss`.
- `knip` falla con dependencias sin usar o imports no declarados.
- La vista no importa el modelo: consume el viewmodel (`src/viewmodel/`).

## Vista del proyecto React

![React teacher](docs/react-teacher.png)

## Requisitos

| Herramienta | Instalación |
|---|---|
| Python 3.13 + `ruff`, `mypy`, `import-linter`, `pip-audit` | `uv tool install ruff mypy import-linter pip-audit` |
| Node 24+ | `winget install OpenJS.NodeJS.LTS` |
| Go 1.27 + `golangci-lint` + `govulncheck` | `winget install GoLang.Go` / `winget install GolangCI.golangci-lint` / `go install golang.org/x/vuln/cmd/govulncheck@latest` |
| Java 25 + Maven | `winget install EclipseAdoptium.Temurin.25.JDK` / `winget install Apache.Maven` |

## Añadir un lenguaje

1. Crea la carpeta con su config de lint.
2. Agrega un `Lang(...)` en `tools/lint.py` con sus comandos `check` y `fix`.
3. Escribe su `AGENTS.md` con los límites y la arquitectura.
4. `python tools/test_lint.py` y `python tools/lint.py`.

## Notas

- El hook se activa con `git config core.hooksPath .githooks`; `setup.ps1` lo
  hace por ti.
- `--no-verify` está prohibido por el contrato: si el linter tiene razón, se
  arregla el código.
- React usa ESLint 9 porque `eslint-plugin-react` aún no soporta ESLint 10.
  No unifiques versiones sin revisar los peer deps.
- `--audit` requiere red. No corre en el hook: es una revisión periódica.
- La cobertura es un piso, no una meta: un test que ejecuta código sin afirmar
  nada sube el número y no la confianza.

## Licencia

MIT.
