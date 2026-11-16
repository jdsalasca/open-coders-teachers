# ADR-0002 — Patrones verificados y gate de ADR

- **Estado:** aceptada
- **Fecha:** 2026-11-16

## Contexto

El repo declara usar hexagonal, MVC y MVVM, pero un patrón solo existe si algo
impide implementarlo mal. Además, cambiar una config de arquitectura es una
decisión de diseño que quedaba invisible en la historia.

## Decisión

1. El dominio es puro: Java solo depende de `java..` y `..domain..`; Go solo de
   stdlib y `internal/domain`; los adaptadores implementan puertos.
2. Toda clase `*Repository` no-interfaz vive en `infrastructure` (ArchUnit).
3. Los tests de contrato (`test_repository_contract.py`) se ejecutan contra cada
   adaptador, no contra uno solo.
4. Un cambio en `eslint.config.js`, `.golangci.yml`, `checkstyle.xml`,
   `.dependency-cruiser.js`, `stryker.conf.json`, `pyproject.toml` o `pom.xml`
   exige un ADR nuevo, verificado por `tools/check_adr.py` en PRs.
5. Los antipatrones de patrón que no se pueden automatizar (Singleton, Service
   Locator, God Object) quedan en `resources/patterns/` como revisión manual.

## Consecuencias

- Un PR que cambia las capas sin explicar por qué falla en CI.
- Los patrones dejan de ser una convención oral y pasan a ser configuración
  ejecutable.
- Más burocracia en cambios de arquitectura: intencional.

## Alternativas descartadas

- **Solo documentar los patrones:** un agente no lee un diagrama si no bloquea.
- **PMD para todo:** PMD no lee bytecode de Java 25 y duplicaría Checkstyle.
- **Reglas semánticas de patrón (Singleton, Service Locator):** falsos positivos
  altos; se documentan como revisión manual.
