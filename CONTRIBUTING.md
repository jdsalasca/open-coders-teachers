# Cómo contribuir

## Antes de tocar nada

```powershell
pwsh tools/setup.ps1
python tools/lint.py
```

El repo se valida a sí mismo: si tu cambio en una config rompe el
autochequeo, no está listo.

## Añadir una regla

1. **Config del lenguaje** (`pyproject.toml`, `eslint.config.js`,
   `.golangci.yml`, `checkstyle.xml`).
2. **Canario**: agrega una violación al fixture de
   `tools/fixtures/<lenguaje>/` y verifica que el linter la reporta.
3. **Autochequeo** (si aplica): `tools/test_lint.py` debe seguir pasando.
4. **Documentación**: actualiza `AGENTS.md` y, si el principio viene de un
   libro, `resources/antipatterns/books.md`.
5. `python tools/lint.py --fix` y después `python tools/lint.py`.

Una regla sin canario es una regla que se puede romper en silencio. El caso del
repo de React que "no encontró nada" es el recordatorio: un linter que devuelve
cero sin mirar es peor que no tener linter.

## Commits

Mensajes convencionales (los valida `.githooks/commit-msg`):

```
feat(react): agrega reglas de accesibilidad
fix(python): corrige el contrato de capas
docs: explica el modo portable
```

Tipos: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`,
`ci`, `chore`, `revert`.

## Prohibido

- `--no-verify` sin aprobación humana explícita.
- Bajar umbrales de cobertura o de linter para que pase un cambio.
- Silenciar reglas con `noqa`/`eslint-disable`/`nolint` sin un motivo escrito.
