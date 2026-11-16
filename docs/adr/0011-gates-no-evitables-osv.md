# ADR-0011 — Gates no evitables, auditoría Maven con OSV y límites numéricos

- **Estado:** aceptada
- **Fecha:** 2026-11-16

## Contexto

Una cuarta auditoría con foco en determinismo encontró cuatro huecos:

1. Un cambio de configuración staged junto a código del mismo lenguaje no
   expandía el gate al proyecto completo (`add_config_langs` se saltaba la
   expansión si el lenguaje ya estaba presente).
2. Las reglas de Semgrep y el propio runner no disparaban nada al cambiarse.
3. La auditoría Maven dependía de Dependabot; en CI el token no puede leer
   alertas y se imprimía "verificación omitida" como si estuviera cubierta.
4. Los contadores podían pasar del entero seguro y el contexto Go solo se
   comprobaba antes de esperar el mutex.

## Decisiones

1. **Un config siempre expande a su proyecto**, aunque el lote ya tenga código
   de ese lenguaje. `.semgrep/rules.yml`, `.markdownlint.json`, `.ls-lint.yml`,
   los workflows y `tools/*.py` expanden a las cinco carpetas.
2. **El gate completo incluye repo checks**: en modo normal, al cambiar un
   config se ejecutan también Semgrep, markdownlint, enlaces y ls-lint sobre
   todo el repo. Cambiar `tools/*.py` añade `python tools/test_lint.py` al
   gate. Con `--fix` no se expande el lote de repo para no reformatear docs y
   JSON ajenos al cambio.
3. **Maven se audita con OSV** (`api.osv.dev/v1/querybatch`) usando las
   dependencias runtime de `mvn dependency:list`. Si OSV o Maven no responden,
   el resultado es `2` ("no pude verificar"), nunca "limpio". Dependabot queda
   como complemento.
4. **El contador satura en `Number.MAX_SAFE_INTEGER`** y Zod ya rechaza enteros
   inseguros. Tests de límite en TS y React.
5. **Go re-comprueba `ctx.Err()` después de adquirir el mutex**, con tests que
   cancelan mientras el lock está tomado.
6. **Java fija el contrato de huecos**: una entrada inválida no agrega tarea,
   pero puede consumir un id. Es el comportamiento de una secuencia de base de
   datos y queda documentado y testeado.
7. **Windows verifica el checksum de golangci-lint**, igual que Linux.

## Consecuencias

- Stagear un config ya no permite saltarse el proyecto completo.
- La auditoría de dependencias Java funciona sin token de GitHub.
- Un contador en el límite no produce valores imprecisos.
- Una cancelación durante la espera del mutex no muta el estado.

## Límites

- OSV consulta vulnerabilidades publicadas; no sustituye una revisión de
  configuración ni de código.
- La cobertura sigue siendo agregada por carpeta: no garantiza calidad por
  archivo.
- Los IDs de Java pueden tener huecos; la unicidad y la concurrencia sí están
  garantizadas por proceso.
