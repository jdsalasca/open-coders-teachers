# Catálogo de antipatrones

Qué se rompe cuando un agente escribe código rápido, cómo se detecta y **qué
regla del repo lo bloquea**. Si una entrada dice *manual*, ningún linter la
puede ver: requiere revisión humana y por eso está escrita aquí.

| Antipatrón | Dónde | Estado |
|---|---|---|
| [Método largo](code.md#método-largo) | todos | automático |
| [Demasiados parámetros](code.md#demasiados-parámetros) | todos | automático |
| [Bandera booleana como parámetro](code.md#bandera-booleana-como-parámetro) | todos | manual |
| [Anidamiento profundo](code.md#anidamiento-profundo) | todos | automático |
| [Código muerto](code.md#código-muerto) | todos | automático |
| [Duplicación](code.md#duplicación) | Go, React, Java* | parcial |
| [Números mágicos](code.md#números-mágicos) | todos | manual |
| [Nombres que no dicen nada](code.md#nombres-que-no-dicen-nada) | todos | automático |
| [Obsesión por primitivos](code.md#obsesión-por-primitivos) | todos | manual |
| [Clase todopoderosa](code.md#clase-todopoderosa) | Java, TS | parcial |
| [Envidia de características](code.md#envidia-de-características) | todos | manual |
| [Acoplamiento temporal oculto](code.md#acoplamiento-temporal-oculto) | todos | manual |
| [Violación de capas](architecture.md#violación-de-capas) | todos | automático |
| [Dependencia circular](architecture.md#dependencia-circular) | TS, React | automático |
| [Lógica de negocio en la vista](architecture.md#lógica-de-negocio-en-la-vista) | React, TS | automático |
| [Dominio anémico](architecture.md#dominio-anémico) | todos | manual |
| [Infraestructura filtrada](architecture.md#infraestructura-filtrada) | Python, Go, Java | automático |
| [Service locator](architecture.md#service-locator) | todos | manual |
| [Estado global mutable](architecture.md#estado-global-mutable) | todos | parcial |
| [Componente dios](frontend.md#componente-dios) | React | manual |
| [Estilos inline](frontend.md#estilos-inline) | React | automático |
| [Estilos duplicados](frontend.md#estilos-duplicados) | React | automático |
| [useEffect para estado derivado](frontend.md#useeffect-para-estado-derivado) | React | manual |
| [Índice como key](frontend.md#índice-como-key) | React | automático |
| [Componente anidado inestable](frontend.md#componente-anidado-inestable) | React | automático |
| [Prop drilling](frontend.md#prop-drilling) | React | manual |
| [Mutación de estado](frontend.md#mutación-de-estado) | React, TS | parcial |

\* Java no tiene detector de duplicación en este repo: `mvn pmd:cpd-check` es la
vía cuando el curso lo necesite.

## Cómo se leen las reglas

Cada entrada trae una línea `Regla:` con el identificador exacto que aparece en
el reporte de `python tools/lint.py`. Si aparece en el reporte, se corrige la
causa; no se silencia.
