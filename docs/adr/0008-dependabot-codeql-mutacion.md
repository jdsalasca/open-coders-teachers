# ADR-0008 — Dependabot, CodeQL Java y mutación en PRs

- **Estado:** aceptada
- **Fecha:** 2026-11-16

## Contexto

La auditoría externa señaló que la revisión de dependencias de Java era manual y
que la mutación no bloqueaba PRs. Además, `upload-artifact` v5 seguía usando
Node 20.

## Decisión

1. **Dependabot como auditor de dependencias.** Se habilitaron las alertas de
   vulnerabilidad del repositorio y `--audit` consulta
   `repos/{owner}/{repo}/dependabot/alerts?state=open` con `gh`. Cubre npm,
   Maven, Go y Actions sin descargar la base NVD. Java deja de ser manual.
2. **CodeQL Java** con autobuild (bytecode 21).
3. **Mutación en PRs**: el workflow corre Stryker y PIT cuando el PR toca
   `typescript-teacher/src`, `React-teacher/src` o `Java-teacher/src`; el
   schedule semanal se mantiene.
4. **upload-artifact v6** para salir de Node 20.

## Consecuencias

- Un PR con una dependencia vulnerable falla en `--security` (Dependabot).
- Un PR que toca código mutado por debajo del 80% falla.
- El CI depende de `GH_TOKEN` para consultar alertas; el job declara
  `security-events: read`.
- CodeQL Java puede fallar si el autobuild no soporta el JDK; en ese caso se
  quita del matrix sin afectar al resto.

## Límites

- Dependabot refleja el grafo de dependencias de GitHub, no el entorno local.
- La mutación por PR corre los tres proyectos, no solo el cambiado; es barato
  (Stryker ~10 s, PIT ~5 s) y evita lógica de detección.
- Las reglas regex de slop siguen siendo heurísticas.
