# ADR-0023 — SpotBugs, integración Go con SQLite y E2E de TypeScript

- **Estado:** aceptada
- **Fecha:** 2026-11-17

## Contexto

Tres huecos de verificación quedaban abiertos:

1. Java tenía Checkstyle, PMD, ArchUnit, Spotless y JaCoCo, pero ningún análisis
   de bytecode que cazara nulls, recursos sin cerrar, concurrencia o `equals`
   mal implementados.
2. Los tests de `internal/web` usaban dobles en memoria y los de SQLite probaban
   el adaptador aislado; faltaba el recorrido real HTTP -> controller -> service
   -> SQLite.
3. La UI de TypeScript se revisó con screenshot manual: sin E2E ni axe, una
   regresión de contraste o de interacción pasaba desapercibida.

## Decisiones

1. **SpotBugs en Java** con `spotbugs-maven-plugin` 4.9.8.2, esfuerzo `Max` y
   umbral `Medium` sobre bytecode 21. Corre en el gate (`spotbugs:check`) y en
   CI. No se sube a `Low`: el default mantiene la señal alta y evita ruido.
2. **Test de integración en Go** (`internal/web/integration_test.go`) que abre
   SQLite en `t.TempDir()`, crea una tarea, repite la clave de idempotencia,
   lista y verifica que la base se cierra. Se apoya en los helpers `serve`,
   `post`, `get` y `decode` de `handler_test.go`.
3. **E2E con axe en TypeScript**: `playwright.config.ts` levanta Vite en el
   puerto 5175, `e2e/smoke.spec.ts` comprueba render, clic, contador y cero
   violaciones de accesibilidad. CI reutiliza el Chromium instalado para React.
4. **Contraste corregido**: `$muted` pasa de `#64748b` a `#56677b` para superar
   4.5:1 sobre `#f4f7fb`.

## Consecuencias

- Java detecta bugs de bytecode que las reglas de estilo no ven.
- El cableado HTTP/SQLite queda cubierto por un test que usa la base real.
- Las dos UIs frontend tienen E2E con axe y el screenshot de TypeScript queda
  actualizado.
- El gate crece en tiempo: SpotBugs y los dos E2E solo corren en su paso de CI,
  no en cada edición (`--fast` sigue siendo local y rápido).

## Límites

- SpotBugs no sustituye a PIT: uno busca patrones de bug, el otro mide si los
  tests detectan cambios.
- La integración Go usa un archivo temporal, no un servidor externo; no cubre
  concurrencia multiinstancia (eso lo cubre `internal/adapters/sqlite`).
- El E2E de TypeScript es un smoke test: interacción y accesibilidad, no una
  suite funcional completa.
- El screenshot sigue siendo revisión manual; no hay regresión visual
  automática.
