# React-teacher

React 19 + TypeScript + Vite + **SCSS modules**. Linters: ESLint (React +
typescript-eslint), Stylelint, Prettier, `tsc` y **knip** para dependencias.

```powershell
npm install                                # una vez
python tools/lint.py --fix React-teacher   # desde la raiz
npm run dev                                # http://localhost:5173
```

## Estilos

- Un archivo `.scss` por componente (`Button.module.scss`), importado como
  `styles.button`. **Nada de `style={{ ... }}`**: ESLint lo marca.
- **Nada de `.css`**: el runner rechaza el archivo.
- Los valores (color, espacio, radio) salen de `src/styles/_tokens.scss`.
  Nunca escribas `#c2542d` dos veces.
- `@use "..."` con namespace; `@import` está prohibido por Stylelint.
- Reglas que cazan estilos duplicados: `declaration-block-no-duplicate-properties`,
  `no-duplicate-selectors`, `shorthand-property-no-redundant-values`.
- Clases en kebab-case (`button-primary`), máximo 3 niveles de anidamiento.

## Dependencias

`knip` (en el runner y en `npm run deps`) falla si:

- una dependencia de `package.json` no se importa en ningún lado,
- un import no está declarado en `package.json`,
- un archivo o un export queda sin usar.

`npm audit --audit-level=high` revisa vulnerabilidades (requiere red, no corre
en el hook).

## Nota de versiones

Este proyecto usa **ESLint 9** porque `eslint-plugin-react` todavía no declara
soporte para ESLint 10. `typescript-teacher` sí usa 10. No unifiques versiones
sin comprobar los peer deps.
