# Antipatrones de código

## Método largo

**Síntoma:** una función que no cabe en una pantalla y hace tres cosas.
**Por qué duele:** no se puede nombrar (si necesita "y" en el nombre, son dos),
no se puede probar por separado y el agente la alarga en cada iteración.
**Arreglo:** extraer pasos con nombre propio; el método público coordina.
**Regla:** `funlen` (Go), `MethodLength` (Java), `max-lines-per-function` (TS,
React), `PLR0915` (Python).

## Demasiados parámetros

**Síntoma:** `crear(a, b, c, d, e, f)`.
**Por qué duele:** el orden se olvida, los tipos se confunden y cada llamada
depende de la firma exacta.
**Arreglo:** agrupar en un objeto/record con nombre (`CreateUserRequest`).
**Regla:** `PLR0913`/`PLR0917` (Python), `revive argument-limit` (Go),
`ParameterNumber` (Java), `max-params` (TS, React).

## Bandera booleana como parámetro

**Síntoma:** `guardar(datos, true)`.
**Por qué duele:** en la llamada no se sabe qué significa `true`; el cuerpo del
método termina con un `if` que parte dos comportamientos.
**Arreglo:** dos funciones (`guardarBorrador`, `publicar`) o un enum.
**Regla:** manual. Ningún linter distingue una bandera legítima de una que
esconde dos métodos.

## Anidamiento profundo

**Síntoma:** `if` dentro de `if` dentro de `for` dentro de `if`.
**Por qué duele:** cada nivel multiplica los casos que hay que mantener en la
cabeza; el agente añade un nivel más en vez de salir temprano.
**Arreglo:** guard clauses (`if (!valido) return;`) y funciones pequeñas.
**Regla:** `max-depth: 3` (TS, React), `C901`/`PLR0912` (Python), `cyclop` (Go),
`CyclomaticComplexity` (Java).

## Código muerto

**Síntoma:** imports, variables, campos o funciones que nadie usa.
**Por qué duele:** el lector (o el siguiente agente) cree que ese código
importa; crece el ruido y se copia a otros archivos.
**Arreglo:** borrar. No comentar "por si acaso": git ya guarda la historia.
**Regla:** `F401`/`F841`/`ARG` (Python), `no-unused-vars` (TS, React),
`unused`/`unparam` (Go), `UnusedImports`/`UnusedLocalVariable` (Java),
`knip` (React, archivos y exports).

## Duplicación

**Síntoma:** el mismo bloque copiado con otro nombre de variable.
**Por qué duele:** un arreglo hay que hacerlo N veces y siempre se olvida una.
**Arreglo:** extraer una función o un componente; si son datos, un token.
**Regla:** `dupl` (Go), `no-duplicate-selectors` +
`declaration-block-no-duplicate-properties` (React). Java y Python: manual
(o `pmd:cpd-check` / revisión de PR).

## Números mágicos

**Síntoma:** `if (intentos > 3)`, `sleep(250)`.
**Por qué duele:** el número no explica la regla de negocio y se repite.
**Arreglo:** constante con nombre (`MAX_INTENTOS`, `$space-md`).
**Regla:** manual en código; en SCSS los valores viven en `_tokens.scss`.

## Nombres que no dicen nada

**Síntoma:** `data`, `tmp`, `x`, `procesar2`, `Foo`.
**Por qué duele:** obliga a leer el cuerpo para saber qué es; el agente lo
reutiliza para otra cosa.
**Arreglo:** nombre por intención (`usuariosPendientes`, no `lista`).
**Regla:** `N` (Python), `naming-convention` (TS, React), `revive var-naming`
(Go), `TypeName`/`MethodName`/`ConstantName` (Java).

## Obsesión por primitivos

**Síntoma:** `String` para un email, `int` para un id de pedido, `List<String>`
para una dirección.
**Por qué duele:** cualquier string es válido, la validación se repite en cada
capa y se mezclan dos ids distintos.
**Arreglo:** value object (`Email`, `OrderId`) que valida al construirse.
**Regla:** manual; el sistema de tipos lo permite, el diseño no.

## Clase todopoderosa

**Síntoma:** una clase con 20 métodos y 15 campos que toca todo.
**Por qué duele:** no se puede probar sin media aplicación; cualquier cambio
rompe algo lejano.
**Arreglo:** separar por responsabilidad (repositorio, servicio, mapper).
**Regla:** parcial. `ClassFanOutComplexity` (Java) y el límite de 40 líneas por
método empujan en esa dirección; la decisión de partir la clase es manual.

## Envidia de características

**Síntoma:** un método que lee cinco campos de otra clase y ninguno de la suya.
**Por qué duele:** la lógica está en el lugar equivocado; la clase dueña de los
datos no puede cambiar sin romper a un tercero.
**Arreglo:** mover el método a la clase que tiene los datos.
**Regla:** manual.

## Acoplamiento temporal oculto

**Síntoma:** `abrir()`, `leer()`, `cerrar()` donde llamar en otro orden rompe
todo, pero la firma no lo dice.
**Por qué duele:** el agente genera llamadas en el orden que le parece.
**Arreglo:** una sola función que haga el ciclo completo, o un tipo que solo
exista en el estado válido.
**Regla:** manual.
