# Errores observados en proyectos reales

Inventario de solo lectura sobre ~65 proyectos de `Programming-personal`
(Rust, TypeScript/React, Python, Java, Godot) para convertir lo que más se
repite en reglas del runner. No se nombran proyectos; los números son
agregados y sirven para priorizar.

| Área | Lo que más apareció | Regla que lo caza ahora |
|---|---|---|
| Rust | `unwrap` (1000+), `expect` (1400+), `panic!` (360+), `println!` (290+), `#[allow]` (140+) | clippy portable estricto (`unwrap_used`, `expect_used`, `panic`, `todo`, `unimplemented`, `dbg_macro`) sobre lib/bin/example |
| TypeScript/React | `any` (250+ en un proyecto), `console.log` (200+, 130, 130), `localStorage` (70, 43, 36), `dangerouslySetInnerHTML` (26+), `eslint-disable` (53), `key={index}` | `no-explicit-any`, `no-console`, React `no-array-index-key`/`no-danger`, `no-eval`, `eqeqeq` |
| Python | `except Exception`/bare except (47 en un proyecto), `Any` (660+), `pickle.load`, `shell=True`, `eval` | ruff `BLE`, `T20`, `A`, `S` y el resto del baseline |
| Java | `System.out` (190+), `printStackTrace` (37+), `catch (Exception)` (300+), `@SuppressWarnings` (1900+, casi todo en un fork de Spring) | Semgrep: `java-system-out`, `java-print-stack-trace`, `java-catch-exception` |
| Godot/GDScript | scripts de 4800, 4000 y 2300 líneas; casi ningún test ni CI | `gdlint`, `gdformat --check`, límite de 400 líneas y aviso de tests/CI |
| Todos | archivos de 4000+ líneas, `venv`/`node_modules` escaneados por error, roots políglotas mezclados | límite portable de 400 líneas, `SKIP` de artefactos y descubrimiento por extensión |

## Lo que cambió en el runner

1. **Descubrimiento por extensión y manifiesto**: un root con `package.json` y
   `requirements.txt` ya no manda todo a Node; los `.py` van a Python y los
   `.ts` a Node.
2. **Workspace Rust**: los crates miembros se funden en el root para no repetir
   clippy ni avisos de CI/README.
3. **Rust estricto**: `unwrap`, `expect`, `panic`, `todo`, `unimplemented` y
   `dbg_macro` son error en código de producción (no en tests).
4. **Java con reglas propias**: `System.out` fuera de `Main`/`Application`,
   `printStackTrace` y `catch (Exception)`.
5. **Godot**: `gdlint` y `gdformat --check` para proyectos con `project.godot`.
6. **Tamaño e higiene**: fuentes de más de 400 líneas fallan; faltar tests, CI
   o README se avisa sin bloquear.
7. **Artefactos fuera**: `venv`, `env`, `site-packages`, `.tox`, `.tmp`,
   `.godot`, `jdk`, `.toolchains`, `vendor` y `third_party` no se escanean.

## Lo que sigue siendo manual

- Decidir si un `any` es legítimo en una frontera.
- Separar un archivo grande en módulos con responsabilidades claras.
- Arreglar un `catch (Exception)` que de verdad necesita capturar todo.
- Añadir tests y CI a proyectos que no los tienen.
- Revisar secretos y `.env`: el baseline portable no los escanea.

Ver [ADR-0016](../../docs/adr/0016-portable-baseline-aprendizajes.md).
