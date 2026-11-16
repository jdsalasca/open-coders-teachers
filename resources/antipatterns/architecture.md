# Antipatrones de arquitectura

## Violación de capas

**Síntoma:** el dominio importa la base de datos, el caso de uso importa el
framework web, la vista importa el modelo.
**Por qué duele:** el núcleo deja de ser testeable sin infraestructura y un
cambio de framework arrastra toda la aplicación.
**Arreglo:** dependencias hacia adentro (dominio ← aplicación ←
infraestructura). La infraestructura implementa puertos del dominio.
**Regla:** automática en las cinco carpetas.

| Carpeta | Arquitectura | Herramienta |
|---|---|---|
| `python-teacher` | hexagonal | `import-linter` (`pyproject.toml`) |
| `go-teacher` | hexagonal | `depguard` (`.golangci.yml`) |
| `Java-teacher` | hexagonal | ArchUnit (`ArchitectureTest.java`) |
| `typescript-teacher` | MVC | `dependency-cruiser` |
| `React-teacher` | MVVM | `dependency-cruiser` |

## Dependencia circular

**Síntoma:** `a.ts → b.ts → a.ts`.
**Por qué duele:** no se puede cargar ni probar un módulo sin el otro; los
cambios se propagan en bucle.
**Arreglo:** extraer el contrato compartido a un tercer módulo.
**Regla:** `sin-ciclos` en `dependency-cruiser` (TS y React).

## Lógica de negocio en la vista

**Síntoma:** un componente React que calcula impuestos o decide reglas de
negocio; un controlador que renderiza HTML con condiciones de negocio.
**Por qué duele:** la regla queda duplicada en otra vista y no se puede probar
sin DOM.
**Arreglo:** la vista solo pinta y delega; el cálculo vive en modelo/viewmodel.
**Regla:** React: `vista-sin-modelo` + `modelo-aislado` (el modelo no importa
React). TS: `modelo-aislado` + `vista-sin-controlador`.

## Dominio anémico

**Síntoma:** entidades con solo getters/setters y toda la lógica en servicios.
**Por qué duele:** el negocio no tiene un lugar claro y se esparce.
**Arreglo:** métodos de dominio que protegen invariantes (`task.complete()`).
**Regla:** manual. Ningún linter sabe dónde debería vivir una regla.

## Infraestructura filtrada

**Síntoma:** el dominio importa `sqlalchemy`, `database/sql`, `jakarta.persistence`
o el cliente HTTP.
**Por qué duele:** obliga a mockear la base de datos para probar una suma.
**Arreglo:** puerto en el dominio, adaptador en infraestructura.
**Regla:** hexagonal: dominio aislado (import-linter, depguard, ArchUnit).

## Service locator

**Síntoma:** `ServiceLocator.get(EmailSender.class)` dentro de un método.
**Por qué duele:** las dependencias dejan de ser visibles en la firma y el test
necesita configurar el contenedor global.
**Arreglo:** inyección por constructor.
**Regla:** manual.

## Estado global mutable

**Síntoma:** `let cache = {}`, `static List<T> tareas`, `global contador`.
**Por qué duele:** dos tests se contaminan, el orden de ejecución cambia el
resultado, la concurrencia rompe todo.
**Arreglo:** pasar el estado como dependencia; si es imprescindible, encapsular
con acceso controlado.
**Regla:** parcial. `RUF012` (Python) caza atributos de clase mutables;
`VisibilityModifier` (Java) obliga a encapsular campos. El resto es manual.
