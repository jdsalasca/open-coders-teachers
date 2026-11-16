# ADR-0010 — IDs por el repositorio, `context` en Go y Zod en TS/React

- **Estado:** aceptada
- **Fecha:** 2026-11-16

## Contexto

El ADR-0009 resolvió la colisión de IDs con `max(id) + 1`, pero ese cálculo no
es atómico y el caso de uso seguía decidiendo el id. Además Go no demostraba
`context.Context` y TypeScript/React solo controlaban el `any`, sin validar la
forma de los datos externos.

## Decisiones

1. **El repositorio asigna el id**, no el caso de uso:
   - Python: `threading.Lock` y `len + 1` dentro del lock, con test de 50
     creaciones concurrentes.
   - Go: `sync.Mutex` en el adaptador, con test de 50 goroutines y IDs únicos.
   - Java: `AtomicInteger` y `CopyOnWriteArrayList`, con test concurrente.
   - El caso de uso (`add`/`Add`/`create` del puerto) solo valida y delega.
2. **Contrato del puerto**: `create(title)` (Python/Java) y
   `Add(ctx, title)`/`All(ctx)` (Go). Hay un contrato reutilizable por
   adaptador en las tres carpetas.
3. **Go usa `context.Context`** en el puerto y en el adaptador: comprueba
   `ctx.Err()` antes de tocar datos y propaga `context.Canceled`.
4. **Zod en TypeScript/React**: `counterSchema` valida el payload externo
   (`{ value: number }` entero no negativo); el controller y el hook reciben
   `unknown` y solo usan el resultado de `parseCounter`. Tests de payload
   válido, negativo y tipo equivocado.
5. `pydantic` queda declarado en `requirements.txt` para que `pip-audit` lo
   audite.

## Consecuencias

- Dos creaciones simultáneas no repiten id en un mismo proceso.
- Un contexto cancelado no muta el estado.
- Un payload con forma incorrecta falla en la frontera, no en la vista.
- El dominio sigue validando sus invariantes (id positivo, título no vacío).

## Límites

- La atomicidad es por proceso: con varias instancias el id debe asignarlo la
  base de datos.
- Zod valida el ejemplo, no una API real; el patrón queda demostrado.
- `max+1` desaparece del caso de uso; el adaptador en memoria usa un contador
  bajo lock/mutex/atómico.
