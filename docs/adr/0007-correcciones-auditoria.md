# ADR-0007 — Correcciones de la auditoría externa

- **Estado:** aceptada
- **Fecha:** 2026-11-16

## Contexto

Una auditoría externa (Codex, `gpt-6.1-terra`) sobre el repo encontró diez
hallazgos. Varios eran reales y uno dejaba reglas declaradas sin ejecutar.

## Decisiones

1. **Semgrep propio se ejecuta de verdad.** El runner ya pasa
   `--config .semgrep/rules.yml` junto a `p/ci`. Se excluyen los fixtures para
   que las violaciones intencionales no bloqueen.
2. **Staging parcial se rechaza.** El lint lee el árbol de trabajo; si un archivo
   staged tiene cambios sin stagear, el commit se bloquea (antes podía aprobar
   contenido distinto al commiteado).
3. **Un cambio de configuración dispara su gate completo.** `CONFIG_LANGS` mapea
   `pom.xml`, `pyproject.toml`, `eslint.config.js`, etc. al lenguaje y ejecuta
   tests, tipos y arquitectura aunque no haya archivos de código.
4. **El gate de ADR falla cerrado.** Si `git diff` falla, sale 2; y exige un ADR
   **nuevo** (`A` en `--name-status`), no una edición cualquiera.
5. **Git roto no es verde.** `git_files` devuelve `None` y el modo repo sale 2 en
   lugar de «Nada que revisar».
6. **Pureza reforzada.** Go prohíbe `database/sql` en el dominio; Python prohíbe
   frameworks externos en `app.domain` (import-linter con paquetes externos).
7. **CI sin pasos duplicados.** `--security` ya audita dependencias; se elimina
   el `--audit` separado.
8. **Versiones fijadas y checksums.** Las herramientas Python se instalan con
   versión exacta; golangci-lint y gitleaks se verifican con `sha256sum`.
9. **E2E prueba comportamiento.** Pulsa el botón y verifica `Valor: 1`, con
   servidor propio en el puerto 4321 y sin reutilizar servidores ajenos.

## Límites aceptados

- La auditoría de dependencias de Java sigue siendo manual (OWASP), y se informa
  como tal; no se simula un resultado.
- Las reglas regex de slop son heurísticas: no entienden sintaxis.
- La inmutabilidad profunda de un bean Spring no se puede demostrar con `final`.
- La mutación sigue siendo semanal, no gate de PR.

## Consecuencias

- Un commit con staging parcial falla con instrucciones claras.
- Cambiar una config ejecuta el gate completo del proyecto (más lento, correcto).
- Linux instala versiones fijas y verifica checksums; Windows y las
  transitivas de pip siguen pendientes.
