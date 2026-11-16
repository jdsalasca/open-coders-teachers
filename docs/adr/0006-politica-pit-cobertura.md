# ADR-0006 — Política propia, PIT y artefactos de cobertura

- **Estado:** aceptada
- **Fecha:** 2026-11-16

## Contexto

Semgrep solo aplicaba reglas genéricas (`p/ci`). La mutación cubría TypeScript y
React, no Java. El CI no publicaba cobertura. PIT y SpotBugs no leen bytecode de
Java 25 (`Unsupported class file major version 69`).

## Decisión

1. **Reglas Semgrep propias** en `.semgrep/rules.yml`:
   - la vista no llama `fetch`/`axios`;
   - `localStorage`/`sessionStorage` fuera de su capa;
   - `process.env` solo en el composition root;
   - `System.out` solo en `Main` (Java);
   - `print`/`fmt.Print` solo en entrypoints.
   Se ejecutan junto a `p/ci` en `--security` y en CI.
2. **Java compila a bytecode 21** con JDK 25 (`maven.compiler.release=21`).
   Es el LTS de los cursos y permite PIT (y en el futuro SpotBugs).
3. **PIT** con umbral 80 de mutación y 80 de cobertura sobre clases mutadas.
   Corre en `--mutation` y semanalmente en CI.
4. **CodeQL** agrega Go con autobuild.
5. **Artefactos de cobertura** en CI: `coverage.xml` (Python), `coverage.html`
   (Go), `coverage/` (Vitest) y `target/site/jacoco` (Java).

## Consecuencias

- Un acceso a datos en la vista falla en `--security`, no en revisión.
- La mutación ahora cubre tres de cinco lenguajes (Java, TS, React).
- El bytecode es 21 aunque el JDK sea 25; se documenta en el README.
- El CI publica cobertura sin depender de un servicio externo.

## Alternativas descartadas

- **Mantener Java 25 y renunciar a PIT:** se pierde la señal de mutación en el
  lenguaje con más reglas de arquitectura.
- **CodeQL también para Java:** el soporte de Java 25/21 con autobuild es
  incierto; se deja para cuando sea estable.
- **Codecov:** requiere token y servicio externo; los artefactos bastan.
