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
├── infrastructure/  adaptadores que implementan los puertos. Importa domain.
├── interfaces/      frontera de entrada (Pydantic + controller + DTO).
└── main.py          composition root: unica pieza que conoce todas las capas.
```

El dominio **no puede** importar `app.application`, `app.infrastructure` ni
`app.interfaces`; application no puede importar `app.interfaces` ni
infrastructure, e interfaces no puede importar infrastructure. Lo verifican
`lint-imports` (`pyproject.toml`) y `tests/test_layers.py` con AST.

La frontera Pydantic valida 1..200 caracteres (code points), rechaza títulos en
blanco y **no recorta** el texto; el dominio también exige 1..200 y conserva el
título. El controller devuelve `TaskView`, no la entidad.

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

Además: `tests/test_service.py` prueba 50 altas concurrentes (IDs únicos y
cardinalidad), `tests/test_repository_contract.py` fija el contrato del puerto y
`tests/test_layers.py` comprueba las capas con AST.

- `A`: no sombrear builtins (`id`, `list`, `type`).
- `RET`: sin `else` tras `return` ni asignaciones antes de retornar.
