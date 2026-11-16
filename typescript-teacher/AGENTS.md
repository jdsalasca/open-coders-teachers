# typescript-teacher

TypeScript 5.9 + ESLint 10 (flat config) + Prettier + `tsc --noEmit` +
**dependency-cruiser**.

```powershell
cd typescript-teacher; npm install             # una vez
python tools/lint.py --fix typescript-teacher  # desde la raiz
```

## Arquitectura MVC

```
src/model/        estado y reglas puras. No importa view ni controller.
src/view/         DOM: pinta y avisa clics. No importa controller.
src/controller/   orquesta modelo y vista.
src/main.ts       composition root.
```

`npm exec depcruise src` falla con `modelo-aislado`, `vista-sin-controlador` o
`sin-ciclos` si se rompe la direccion.

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
