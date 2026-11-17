# ADR-0022 — UI de TypeScript, audit de runtime y null guard Java

- **Estado:** aceptada
- **Fecha:** 2026-11-17

## Contexto

React tenía una UI cuidada, pero TypeScript solo exponía un `bootstrap` sin
página ejecutable. Además, `npm audit --audit-level=high` empezó a fallar por
advisories de tooling (Vite/picomatch) sin parche compatible con React 19, y
`TaskController.create(null)` no daba un error claro.

## Decisiones

1. **TypeScript con Vite**: `index.html`, `npm run dev`, `main.ts` monta en
   `#app`, `counter-view.scss` define la tarjeta y los tokens visuales. `sass` y
   `vite` quedan en `devDependencies`.
2. **UI accesible**: contador con `aria-live`, botón con foco visible, contraste
   y `prefers-reduced-motion`; el screenshot vive en
   `docs/images/typescript-teacher.png` y se enlaza en el README.
3. **Audit de runtime**: `npm audit --omit=dev --audit-level=high` para TS,
   React y `tools/node`. Los advisories de tooling se siguen con Dependabot, que
   actualiza devDependencies. El SBOM y OSV siguen cubriendo dependencias.
4. **Java null-safe**: `TaskController.create` usa
   `Objects.requireNonNull(request, "request")` y hay test de petición nula.
5. **React**: `sass` pasa de `dependencies` a `devDependencies`; el build no
   necesita SASS en runtime.
6. **Salidas de consola**: Python, Java y Rust imprimen tablas/JSON legibles.

## Consecuencias

- Los dos teachers frontend tienen una página ejecutable y un screenshot.
- El audit ya no falla por vulnerabilidades de herramientas sin parche.
- `create(null)` falla en la frontera con un mensaje claro.
- El build de React no arrastra SASS como dependencia de producción.

## Límites

- El audit de devDependencies no bloquea; Dependabot y el SBOM son el
  complemento.
- El screenshot es revisión manual, no regresión visual automática.
- TypeScript no tiene E2E con axe; la accesibilidad se revisó en la vista y el
  screenshot.
- Los advisories de tooling pueden quedar abiertos hasta que sus mantenedores
  publiquen un parche compatible.
