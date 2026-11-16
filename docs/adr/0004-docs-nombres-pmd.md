# ADR-0004 — Docs, nombres y código muerto Java

- **Estado:** aceptada
- **Fecha:** 2026-11-16

## Contexto

El repo tiene 21 documentos, pero ninguno se validaba: enlaces rotos, tablas mal
formadas y bloques sin lenguaje pasaban. Los nombres de archivo dependían del
criterio de cada agente. En Java solo se detectaba duplicación (CPD), no código
muerto.

## Decisión

1. **Docs**: `markdownlint` + `tools/check_links.py` (enlaces locales y anclas)
   corren en cada commit y en CI, sobre los `.md` cambiados.
2. **Nombres**: `ls-lint` impone `snake_case` en Python/Go, `PascalCase` en
   Java y componentes `.tsx`. Los puntos de entrada (`main.tsx`) están exentos.
3. **Java**: PMD con `UnusedPrivateMethod`, `UnusedPrivateField`,
   `TooManyMethods` y `EmptyCatchBlock`, además de CPD.
4. **Contract tests** del puerto en Go (`internal/testutil`) y Java (test
   abstracto), no solo en Python.
5. La cobertura Go se mide con `-coverpkg=./internal/...`: instrumenta los
   paquetes internos (incluido el contrato) y excluye el composition root.

## Consecuencias

- Un enlace roto o un documento mal formado bloquea el commit.
- Renombrar un archivo fuera de convención falla.
- PMD y Checkstyle se complementan: uno mira bytecode-agnóstico de fuente, el
  otro formato/estructura.
- El umbral de cobertura Go ahora refleja código interno real.

## Alternativas descartadas

- **cspell**: los documentos están en español y genera falsos positivos masivos.
- **PMD completo**: demasiadas reglas ruidosas; se eligió un ruleset mínimo.
- **Validar anclas con red**: frágil y lento; se validan solo enlaces locales.
