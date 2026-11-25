"""Reglas de seguridad ante nulos y errores, portables a los seis lenguajes.

Cada lenguaje tiene una forma distinta de fallar en silencio cuando falta un valor.
Estas reglas atacan esa forma concreta, no el estilo:

- ``go-panic``               panic fuera del composition root
- ``rust-unwrap``            unwrap/expect en produccion
- ``ts-non-null-assertion``  ``x!`` apaga el chequeo de nulos
- ``ts-any``                 ``any`` desactiva el tipado
- ``python-none-comparison`` ``== None`` en vez de ``is None``
"""

from __future__ import annotations

import re
from pathlib import Path

from lintlib import quality
from lintlib.solid import Unit

PANIC_RE = re.compile(r"\bpanic\s*\(")
UNWRAP_RE = re.compile(r"\.\s*(?:unwrap|expect)\s*\(")
TS_BANG_RE = re.compile(r"\w!\s*[.;,)\[]")
TS_ANY_RE = re.compile(r":\s*any\b")
PY_NONE_RE = re.compile(r"[!=]=\s*None\b")
GO_SLEEP_RE = re.compile(r"\btime\s*\.\s*Sleep\s*\(")
GO_EXEC_SHELL_RE = re.compile(r'exec\s*\.\s*Command\s*\(\s*"(?:sh|bash)"')
GO_FLOAT_RE = re.compile(r"\bfloat(?:32|64)\b")
MONEY_NAME_RE = re.compile(r"(?i)(price|amount|money|total|cost|tarifa|precio|monto)")

# El composition root puede fallar ruidosamente: es el borde del programa.
COMPOSITION = {"main.go", "main.rs", "main.py", "main.ts", "main.tsx", "App.tsx"}


def _line(text: str, position: int) -> int:
    """Linea 1-based de una posicion."""
    return text.count("\n", 0, position) + 1


def _violation(
    relative: str, line: int, category: str, rule: str, message: str
) -> quality.Violation:
    return quality.Violation(relative, line, 1, category, rule, message, "nullsafety", False)


def _is_composition(relative: str) -> bool:
    """True si la ruta es un punto de entrada del programa."""
    path = Path(relative.replace("\\", "/"))
    return path.name in COMPOSITION or "cmd/" in relative.replace("\\", "/")


def panic_violations(units: list[Unit]) -> list[quality.Violation]:
    """panic fuera del composition root."""
    out: list[quality.Violation] = []
    for unit in units:
        if _is_composition(unit.relative):
            continue
        for match in PANIC_RE.finditer(unit.text):
            out.append(
                _violation(
                    unit.relative,
                    _line(unit.text, match.start()),
                    "calidad",
                    "go-panic",
                    "panic en codigo de libreria; devuelve un error y deja que el borde decida",
                )
            )
            break
    return out


def unwrap_violations(units: list[Unit]) -> list[quality.Violation]:
    """unwrap/expect en produccion."""
    out: list[quality.Violation] = []
    for unit in units:
        if _is_composition(unit.relative):
            continue
        for match in UNWRAP_RE.finditer(unit.text):
            out.append(
                _violation(
                    unit.relative,
                    _line(unit.text, match.start()),
                    "calidad",
                    "rust-unwrap",
                    "unwrap/expect propaga un panic; propaga el error con ? o manejalo",
                )
            )
            break
    return out


def typescript_violations(units: list[Unit]) -> list[quality.Violation]:
    """Aserciones que apagan el chequeo de nulos o el tipado."""
    out: list[quality.Violation] = []
    for unit in units:
        if unit.relative.endswith(".d.ts"):
            continue
        bang = TS_BANG_RE.search(unit.text)
        if bang:
            out.append(
                _violation(
                    unit.relative,
                    _line(unit.text, bang.start()),
                    "calidad",
                    "ts-non-null-assertion",
                    "el '!' apaga strictNullChecks; valida el nulo o usa un tipo que lo contemple",
                )
            )
        for match in TS_ANY_RE.finditer(unit.text):
            out.append(
                _violation(
                    unit.relative,
                    _line(unit.text, match.start()),
                    "calidad",
                    "ts-any",
                    "'any' desactiva el tipado; usa el tipo real o 'unknown' y estrecha",
                )
            )
            break
    return out


def python_violations(units: list[Unit]) -> list[quality.Violation]:
    """Comparacion con None por igualdad."""
    out: list[quality.Violation] = []
    for unit in units:
        for match in PY_NONE_RE.finditer(unit.text):
            out.append(
                _violation(
                    unit.relative,
                    _line(unit.text, match.start()),
                    "nombres",
                    "python-none-comparison",
                    "compara con 'is None' / 'is not None'; None es un singleton",
                )
            )
            break
    return out


def go_security_violations(units: list[Unit]) -> list[quality.Violation]:
    """Dormir, shell y dinero en punto flotante."""
    out: list[quality.Violation] = []
    for unit in units:
        if _is_composition(unit.relative):
            continue
        sleep = GO_SLEEP_RE.search(unit.text)
        if sleep:
            out.append(_violation(
                unit.relative, _line(unit.text, sleep.start()), "calidad",
                "go-sleep-produccion",
                "time.Sleep bloquea la goroutine; usa un ticker, un timer o el contexto"))
        shell = GO_EXEC_SHELL_RE.search(unit.text)
        if shell:
            out.append(_violation(
                unit.relative, _line(unit.text, shell.start()), "seguridad",
                "go-exec-shell",
                "exec.Command con sh -c permite inyeccion de comandos; pasa los argumentos"))
        if MONEY_NAME_RE.search(unit.relative) or MONEY_NAME_RE.search(unit.text):
            money = GO_FLOAT_RE.search(unit.text)
            if money:
                out.append(_violation(
                    unit.relative, _line(unit.text, money.start()), "calidad",
                    "go-float-dinero",
                    "float para dinero acumula error; usa enteros en la unidad minima"))
    return out


def analyze(units: list[Unit], language: str) -> list[quality.Violation]:
    """Aplica las reglas de nulos y errores del lenguaje."""
    out: list[quality.Violation] = []
    if language == "go":
        out.extend(panic_violations(units))
        out.extend(go_security_violations(units))
    elif language == "rust":
        out.extend(unwrap_violations(units))
    elif language == "typescript":
        out.extend(typescript_violations(units))
    elif language == "python":
        out.extend(python_violations(units))
    return quality.dedupe(out)
