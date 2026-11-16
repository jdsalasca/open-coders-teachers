# Antipatrones de testing

## Test que no prueba nada

**Síntoma:** `assert result is not None`, `expect(x).toBeDefined()`, un test sin
asserts.
**Por qué duele:** pasa siempre, incluso cuando el código está roto; da falsa
sensación de cobertura.
**Arreglo:** afirmar el valor esperado concreto (y al menos un caso borde).
**Regla:** parcial. La cobertura (60-80%) y `B011`/`no-conditional-expect`
empujan, pero la calidad del assert es manual.

## Test dependiente del orden

**Síntoma:** el segundo test necesita lo que creó el primero.
**Por qué duele:** falla al correr solo, en paralelo o al azar; el agente lo
"arregla" reordenando.
**Arreglo:** cada test crea su propio estado.
**Regla:** manual.

## Test gigante

**Síntoma:** un test que recorre todo el flujo con 40 asserts.
**Por qué duele:** cuando falla no se sabe qué parte se rompió.
**Arreglo:** un comportamiento por test, nombre que lo describa.
**Regla:** parcial. Las mismas reglas de tamaño aplican a los archivos de test
en Java (`MethodLength`); en el resto es manual.

## Mock de todo

**Síntoma:** mockear el repositorio, el reloj, el logger y tres servicios para
probar una suma.
**Por qué duele:** el test verifica que los mocks se llaman, no que el negocio
funcione.
**Arreglo:** probar el dominio puro sin mocks; mockear solo el borde (puerto).
**Regla:** manual; el diseño por puertos lo hace fácil.

## `assert` desactivado en producción

**Síntoma:** `assert False` o lógica de negocio dentro de un `assert`.
**Por qué duele:** `python -O` borra los asserts y la validación desaparece.
**Arreglo:** `raise AssertionError()` en tests, excepciones reales en código.
**Regla:** `B011` (Python).

## Cobertura sin intención

**Síntoma:** tests que ejecutan líneas sin afirmar nada, solo para subir el %.
**Por qué duele:** el número sube y la confianza no.
**Arreglo:** cubrir ramas con casos que puedan fallar.
**Regla:** el umbral mínimo (60-80%) es el piso, no la meta.

## Test que toca la red o el reloj

**Síntoma:** el test llama a una API real o depende de `Date.now()`.
**Por qué duele:** falla sin internet, en otro huso horario o el día que el
servicio cambia.
**Arreglo:** inyectar el puerto y usar un doble de prueba.
**Regla:** manual.
