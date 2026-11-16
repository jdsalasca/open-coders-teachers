# ADR-0001 — Calidad determinista por lenguaje

- **Estado:** aceptada
- **Fecha:** 2026-11-16

## Contexto

Los agentes generan código a gran velocidad y con defectos repetidos: variables
muertas, métodos largos, capas rotas, estilos duplicados, tests apagados. La
revisión humana no escala y los linters aislados no se ejecutan.

## Decisión

1. Cada lenguaje tiene su linter canónico, configurado en su carpeta.
2. Un único runner (`tools/lint.py`) detecta el lenguaje y ejecuta lo que
   corresponde, con salida legible y JSON.
3. Un hook de pre-commit bloquea el commit si algo falla; CI corre lo mismo en
   Linux y Windows.
4. El runner **nunca** devuelve 0 si no pudo verificar: `2` significa "no pude".
5. Cada regla crítica tiene un canario que demuestra que sigue cazando.
6. La arquitectura se declara por carpeta (hexagonal, MVC, MVVM) y se verifica
   con `import-linter`, `depguard`, ArchUnit y `dependency-cruiser`.

## Consecuencias

- Más fricción al commitear: es intencional.
- Los umbrales son política, no verdad absoluta; se ajustan con justificación.
- Las decisiones no automatizables quedan en `resources/antipatterns/` como
  revisión manual, en lugar de fingir cobertura.

## Alternativas descartadas

- **Un linter propio en Rust:** cada ecosistema ya tiene reglas y autofix; el
  valor estaba en orquestar, no en reimplementar.
- **Solo documentación:** un agente no la lee si no bloquea.
- **Solo CI:** el feedback llega tarde y el commit ya está hecho.
