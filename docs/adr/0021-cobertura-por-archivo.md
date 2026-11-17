# ADR-0021 — Cobertura mínima por archivo en los seis teachers

- **Estado:** aceptada
- **Fecha:** 2026-11-17

## Contexto

Los mínimos globales (60/80/50/60/60/60) permiten que un archivo con poca
cobertura quede compensado por otro. La auditoría pidió medir por componente
sin penalizar composition roots ni tests. `diff-cover` cubre líneas nuevas,
pero no archivos existentes.

## Decisiones

1. **`tools/coverage_gate.py`** lee los reportes que ya genera el runner:
   - Cobertura XML (Python).
   - JaCoCo XML (Java).
   - LCOV (TypeScript, React, Rust).
   - `coverage.out` (Go), deduplicando bloques repetidos de varios binarios.
2. **Umbrales por lenguaje**: TypeScript/React 80%, Python/Java/Rust 60%, Go
   50%. Son los mismos mínimos globales, aplicados a cada archivo.
3. **Exclusiones explícitas**: `main.py`, `Main.java`, `cmd/`, `testutil/`,
   `main.rs`, `main.ts`/`main.tsx`, tests y `__init__.py`. El composition root
   no se prueba por diseño; el resto sí.
4. **CI**: Linux y Windows ejecutan `python tools/coverage_gate.py` después del
   gate completo. Un archivo por debajo del mínimo devuelve `1`; un reporte
   ausente devuelve `2`.
5. **Tests del parser**: LCOV, deduplicación de bloques Go y exclusiones.

## Consecuencias

- Un archivo flojo falla aunque el total de la carpeta siga alto.
- Los entrypoints no penalizan la métrica.
- El gate usa los reportes ya generados; no ejecuta tests dos veces.
- Los umbrales quedan documentados en README/AGENTS.

## Límites

- No mide branches ni funciones por archivo, solo líneas.
- Go usa `coverage.out`; si cambia el formato, el parser falla visiblemente.
- Rust no tiene umbral por archivo nativo; LCOV lo aporta.
- No sustituye `diff-cover`: uno mira el archivo completo y el otro las líneas
  nuevas del PR.
- `app/main.py` y `Main` siguen sin test dedicado; están excluidos a propósito.
