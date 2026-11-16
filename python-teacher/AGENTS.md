# python-teacher

Python 3.13. Linters: **ruff**, **mypy**, **import-linter**.

```powershell
python tools/lint.py --fix python-teacher   # desde la raiz
```

## Arquitectura hexagonal

```text
app/
├── domain/          entidades y puertos (Protocol). No importa nada de app.
├── application/     casos de uso. Importa domain.
└── infrastructure/  adaptadores que implementan los puertos. Importa domain.
```

El dominio **no puede** importar `app.application` ni `app.infrastructure`; la
infraestructura **no puede** importar `app.application`. Lo verifica
`lint-imports` con los contratos de `pyproject.toml`.

## Reglas

`E,W,F` (formato, imports y variables sin usar), `I` (orden de imports), `N`
(nombres), `D` (docstrings), `ARG` (parametros sin usar), `PLR` (max 4
parametros, max 40 statements), `C90` (complejidad 8), `B,UP,SIM,RUF` y `S`
(bandit: `eval`, `subprocess` con shell, secretos embebidos).

`mypy` exige anotaciones (`disallow_untyped_defs`). Una funcion sin tipos es
error, no sugerencia.

## Tests

`tests/test_*.py` con pytest; cobertura minima 60% sobre `app/`. El runner corre
`pytest --cov=app --cov-fail-under=60`. Reglas `PT` para estilo de pytest y
`B011` para `assert False`.

- `A`: no sombrear builtins (`id`, `list`, `type`).
- `RET`: sin `else` tras `return` ni asignaciones antes de retornar.
