# python-teacher

Python 3.13. Linters: **ruff** (`pyproject.toml`) y **mypy** (tipos).

```powershell
python tools/lint.py --fix python-teacher   # desde la raiz
```

Reglas activas: `E,W,F` (formato, imports y variables sin usar), `I` (orden de
imports), `N` (nombres), `D` (docstrings), `ARG` (parametros sin usar), `PLR`
(max 4 parametros, max 40 statements), `C90` (complejidad 8), `B,UP,SIM,RUF`.

`mypy` exige anotaciones de tipo (`disallow_untyped_defs`). Una funcion sin
tipos es error, no sugerencia.

Lo que ruff no arregla solo, se arregla escribiendo mejor: una funcion de mas
de 40 lineas se parte en funciones con nombre propio, no se le baja el limite.
