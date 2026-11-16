# React-teacher

React 19 + TypeScript + Vite + **SCSS modules**. Linters: ESLint, Stylelint,
Prettier, `tsc`, **knip** y **dependency-cruiser**.

```powershell
npm install                                # una vez
python tools/lint.py --fix React-teacher   # desde la raiz
npm run dev                                # http://localhost:5173
```

## Arquitectura MVVM

```text
src/model/        estado puro, sin React
src/viewmodel/    hooks: estado + acciones, sin JSX
src/view/         componentes y estilos; no importa model
src/styles/       tokens y estilos globales
src/main.tsx      composition root
```

`npm exec depcruise src` falla con `modelo-aislado`, `viewmodel-sin-vista` o
`vista-sin-modelo` si se salta una capa.

## Estilos

- Un archivo `.scss` por componente (`Button.module.scss`), importado como
  `styles.button`. **Nada de `style={{ ... }}`**: ESLint lo marca.
- **Nada de `.css`**: el runner rechaza el archivo.
- Los valores (color, espacio, radio) salen de `src/styles/_tokens.scss`.
- `@use "..."` con namespace; `@import` está prohibido por Stylelint.
- Reglas que cazan estilos duplicados: `declaration-block-no-duplicate-properties`,
  `no-duplicate-selectors`, `shorthand-property-no-redundant-values`.
- Clases en kebab-case, máximo 3 niveles de anidamiento.

## Dependencias

`knip` falla si una dependencia no se importa, si un import no está declarado o
si un archivo/export queda sin usar. `npm audit --audit-level=high` revisa
vulnerabilidades (`--audit`, requiere red).

## Nota de versiones

Este proyecto usa **ESLint 9** porque `eslint-plugin-react` todavía no declara
soporte para ESLint 10. `typescript-teacher` sí usa 10. No unifiques versiones
sin comprobar los peer deps.

## Tests

`src/**/*.test.ts(x)` con vitest + jsdom; cobertura minima 80% en `model` y
`viewmodel`. `npm run test` y `npm run dup` (jscpd). Tipos vagos (`{}`,
`Object`, `Function`, `any`) son error.

- `eqeqeq`, `no-var`, `prefer-const`, `no-param-reassign`, `no-shadow`.
- `no-non-null-assertion`, `switch-exhaustiveness-check`, `jsdoc/require-description`.
