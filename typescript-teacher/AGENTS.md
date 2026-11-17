# typescript-teacher

TypeScript 5.9 + ESLint 10 (flat config) + Prettier + `tsc --noEmit` +
**dependency-cruiser**.

```powershell
cd typescript-teacher; npm install             # una vez
npm run dev                                    # http://localhost:5173
python tools/lint.py --fix typescript-teacher  # desde la raiz
```

## Arquitectura MVC

```text
src/model/        estado y reglas puras. No importa view ni controller.
src/view/         DOM: pinta y avisa clics. No importa controller.
src/controller/   orquesta modelo y vista.
src/main.ts       composition root.
```

`npm exec depcruise src` falla con `modelo-aislado`, `vista-sin-controlador` o
`sin-ciclos` si se rompe la direccion.

## Vista

`index.html` + Vite montan `src/main.ts` en `#app`; `src/view/counter-view.scss`
define la tarjeta y los tokens visuales. La vista inyecta el DOM y solo avisa
clics; no conoce el controlador.

## Reglas

`no-unused-vars`, `max-params: 4`, `max-lines-per-function: 40`,
`complexity: 8`, `max-depth: 3`, `member-ordering`, `naming-convention`,
`explicit-function-return-type`, `consistent-type-imports`,
`jsdoc/require-jsdoc` en API publica, `simple-import-sort`.

Con informacion de tipos (`projectService`): `no-floating-promises`,
`no-misused-promises`, `await-thenable`.

Imports relativos con extension `.js` (NodeNext): `"./model/counter.js"`.
Orden de miembros en clase: campos estaticos, campos de instancia, constructor,
metodos.

## Tests

`src/**/*.test.ts` con vitest; cobertura minima 80% en `model` y `controller`.
`npm run test` y `npm run dup` (jscpd: clones de 70+ tokens).

- `eqeqeq`, `no-var`, `prefer-const`, `no-param-reassign`, `no-shadow`.
- `no-non-null-assertion`, `switch-exhaustiveness-check`, `jsdoc/require-description`.
