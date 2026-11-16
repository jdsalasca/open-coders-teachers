# typescript-teacher

TypeScript 5.9 + ESLint 10 (flat config) + Prettier + `tsc --noEmit`.

```powershell
cd typescript-teacher; npm install      # una vez
python tools/lint.py --fix typescript-teacher/   # desde la raiz
```

Reglas activas: `no-unused-vars`, `max-params: 4`, `max-lines-per-function: 40`,
`complexity: 8`, `member-ordering`, `naming-convention`,
`explicit-function-return-type`, `jsdoc/require-jsdoc` en API publica,
`simple-import-sort`. Formato: Prettier (100 columnas).

Orden de miembros en clase que exige el linter: campos estaticos, campos de
instancia, constructor, metodos.
