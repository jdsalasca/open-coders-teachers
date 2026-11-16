# Antipatrones de frontend (React + SCSS)

## Componente dios

**Síntoma:** un `.tsx` de 400 líneas con fetch, estado, formato y markup.
**Por qué duele:** cualquier cambio re-renderiza todo y los tests necesitan
mockear medio navegador.
**Arreglo:** separar en vista + viewmodel + componentes de presentación.
**Regla:** parcial. `max-lines-per-function: 40` limita funciones y
`knip` detecta archivos huérfanos, pero el tamaño del archivo es manual.

## Estilos inline

**Síntoma:** `<div style={{ color: "red", margin: 8 }}>`.
**Por qué duele:** esquiva el sistema de tokens, no se puede reutilizar, no
participa de media queries y gana en especificidad sin querer.
**Arreglo:** clase en el `.module.scss` del componente.
**Regla:** `react/forbid-dom-props` con `style` prohibido.

## Estilos duplicados

**Síntoma:** la misma propiedad dos veces en un bloque, dos selectores con el
mismo nombre, o el color repetido en cinco archivos.
**Por qué duele:** el navegador aplica la última y el resto es basura invisible;
cambiar un color obliga a buscar en todo el proyecto.
**Arreglo:** tokens en `_tokens.scss` y un selector por bloque.
**Regla:** `declaration-block-no-duplicate-properties`,
`no-duplicate-selectors`, `shorthand-property-no-redundant-values`.

## useEffect para estado derivado

**Síntoma:** `useEffect(() => setTotal(a * b), [a, b])`.
**Por qué duele:** un render extra, un estado que puede desincronizarse y un
bug difícil de reproducir.
**Arreglo:** calcular en el render (`const total = a * b`) o en el viewmodel.
**Regla:** manual; `react-hooks/exhaustive-deps` solo caza dependencias
faltantes, no el diseño.

## Índice como key

**Síntoma:** `items.map((item, i) => <Row key={i} />)`.
**Por qué duele:** al reordenar o borrar, React reutiliza el nodo equivocado y
se pierde el estado del input.
**Arreglo:** `key={item.id}` con un id estable.
**Regla:** `react/no-array-index-key`.

## Componente anidado inestable

**Síntoma:** definir un componente dentro de otro y usarlo en JSX.
**Por qué duele:** cada render crea un tipo nuevo y React desmonta/remonta el
subárbol completo, perdiendo foco y estado.
**Arreglo:** moverlo fuera del componente.
**Regla:** `react/no-unstable-nested-components`.

## Prop drilling

**Síntoma:** pasar una prop por cinco niveles que solo la reenvían.
**Por qué duele:** cualquier componente intermedio queda acoplado a datos que
no usa.
**Arreglo:** composición (`children`), contexto con valor estable, o viewmodel.
**Regla:** manual; si se usa contexto, `react/jsx-no-constructed-context-values`
evita recrear el valor en cada render.

## Mutación de estado

**Síntoma:** `state.items.push(x); setState(state)` o reasignar un objeto
`readonly` por cast.
**Por qué duele:** React compara por referencia y no re-renderiza; el bug es
silencioso.
**Arreglo:** crear una copia (`[...items, x]`) o un reducer.
**Regla:** parcial. Los contratos `readonly` del modelo y `no-unsafe-*` de
TypeScript lo dificultan; la mutación deliberada es manual.
