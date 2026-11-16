# ADR-0009 — Null-safety, validación en fronteras e IDs únicos

- **Estado:** aceptada
- **Fecha:** 2026-11-16

## Contexto

Una auditoría con foco en calidad encontró tres huecos: IDs que podían
colisionar (`len + 1`), contratos que aceptaban nulos y validación casera en
lugar de las librerías del ecosistema.

## Decisiones

1. **ID único:** `max(id) + 1` en Python, Go y Java. No es seguro ante
   concurrencia; se documenta como límite y el repositorio podría asignarlo.
2. **Java:**
   - `Task` valida id positivo y título no vacío en su constructor compacto.
   - `TaskService` usa `Objects.requireNonNull` para el puerto.
   - La frontera web usa **Jakarta Bean Validation** (`@NotBlank`, `@Size`) con
     Hibernate Validator, y el controller invoca el `Validator`; hay tests de
     petición válida, vacía y demasiado larga.
3. **Go:** el puerto devuelve `error` en `Save`/`All`; el servicio valida el
   título (`ErrEmptyTitle`), propaga errores y calcula el id máximo. Tests de
   error, título vacío e ids dispersos.
4. **Python:** invariantes en `Task` (`__post_init__`), frontera Pydantic
   (`CreateTaskRequest`) y `TaskController`; `requirements.txt` activa
   `pip-audit`.
5. **TypeScript/React:** `no-unsafe-*` y `consistent-type-assertions: never`.
   Un `any` que venga de una API ya no se propaga en silencio.
6. **Semgrep propio en el gate normal**, no solo en `--security`.

## Consecuencias

- Un id disperso no sobrescribe tareas.
- Una dependencia nula falla al construir el servicio, no en el primer uso.
- Un payload inválido se rechaza antes de tocar el dominio.
- Un `as` o un `any` implícito rompe el lint.

## Límites

- `max+1` no es atómico; en producción el id lo asigna la base de datos.
- Bean Validation y Pydantic viven en la frontera; el dominio mantiene sus
  invariantes manuales.
- Go no demuestra `context.Context` porque el adaptador es en memoria.
- Zod no se agregó: el ejemplo no consume APIs externas.
