"""Falla si un cambio toca la arquitectura y no agrega un ADR."""

from __future__ import annotations

import subprocess
import sys

ARCH_FILES = (
    "eslint.config.js",
    ".golangci.yml",
    "checkstyle.xml",
    ".dependency-cruiser.js",
    "stryker.conf.json",
    "pyproject.toml",
    "pom.xml",
)


def changed_files(base: str) -> list[str]:
    """Archivos cambiados entre base y HEAD."""
    result = subprocess.run(  # noqa: S603 - git con argumentos controlados
        ["git", "diff", "--name-only", f"{base}...HEAD"],  # noqa: S607 - git en el PATH
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    """Revisa si el cambio necesita un ADR."""
    base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    files = changed_files(base)
    architecture = [f for f in files if any(f.endswith(name) for name in ARCH_FILES)]
    adr = [f for f in files if f.startswith("docs/adr/")]

    if architecture and not adr:
        print("[X] Cambiaste configuracion de arquitectura sin un ADR:")
        for name in architecture:
            print(f"    {name}")
        print("    Agrega docs/adr/NNNN-<tema>.md explicando la decision.")
        return 1
    if architecture:
        print(f"ADR presente para {len(architecture)} archivo(s) de arquitectura.")
    else:
        print("Sin cambios de arquitectura.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
