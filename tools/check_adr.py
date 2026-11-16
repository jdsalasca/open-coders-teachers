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


def changed_files(base: str) -> list[tuple[str, str]] | None:
    """Pares (estado, archivo) entre base y HEAD; None si git falla."""
    result = subprocess.run(  # noqa: S603 - git con argumentos controlados
        ["git", "diff", "--name-status", f"{base}...HEAD"],  # noqa: S607 - git en el PATH
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return None
    entries: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            entries.append((parts[0].strip(), parts[1].strip()))
    return entries


def main() -> int:
    """Revisa si el cambio necesita un ADR."""
    base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    entries = changed_files(base)
    if entries is None:
        print(f"[X] no pude comparar con '{base}'. ¿Hace falta git fetch?")
        return 2
    architecture = [path for _, path in entries if any(path.endswith(name) for name in ARCH_FILES)]
    adr = [
        path for status, path in entries if path.startswith("docs/adr/") and status.startswith("A")
    ]

    if architecture and not adr:
        print("[X] Cambiaste configuracion de arquitectura sin un ADR:")
        for name in architecture:
            print(f"    {name}")
        print("    Agrega un ADR NUEVO en docs/adr/NNNN-<tema>.md.")
        return 1
    if architecture:
        print(f"ADR presente para {len(architecture)} archivo(s) de arquitectura.")
    else:
        print("Sin cambios de arquitectura.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
