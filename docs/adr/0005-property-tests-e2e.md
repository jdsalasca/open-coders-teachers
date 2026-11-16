# ADR-0005 — Property tests y E2E con accesibilidad real

- **Estado:** aceptada
- **Fecha:** 2026-11-16

## Contexto

Los tests de ejemplo prueban un caso concreto. La cobertura y los mutantes miden
cuánto se ejecuta, no si una propiedad se cumple para entradas arbitrarias. La
accesibilidad se validaba solo con reglas estáticas (`jsx-a11y`), que no ven el
DOM renderizado ni el contraste.

## Decisión

1. **Property-based tests** en los cinco lenguajes:
   - Python: Hypothesis (`tests/test_properties.py`).
   - TypeScript y React: fast-check (`*.property.test.ts`).
   - Go: `testing/quick` (stdlib, sin dependencia).
   - Java: jqwik (`TaskServicePropertyTest`).
2. **E2E + axe** en React: Playwright levanta Vite en `127.0.0.1:4173`, verifica
   el título y el botón, y corre `@axe-core/playwright`; cualquier violación
   rompe el test.
3. CI ejecuta E2E en Linux (instala Chromium con dependencias). Local:
   `npm run e2e` tras `npx playwright install chromium`.

## Consecuencias

- Una función pura nueva debe traer al menos una propiedad, no solo ejemplos.
- La app no puede mergear con violaciones de accesibilidad renderizada.
- El CI crece ~1 minuto por la instalación de Chromium.

## Alternativas descartadas

- **Solo property tests en Python:** el patrón se enseña en un lenguaje y se
  ignora en el resto.
- **Lighthouse CI:** mide performance; axe cubre accesibilidad de forma más
  directa y determinista.
- **Snapshot tests del DOM:** frágiles y no verifican semántica accesible.
