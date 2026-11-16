# ADR-0003 — Adaptadores de entrada, DTOs y naming de puertos

- **Estado:** aceptada
- **Fecha:** 2026-11-16

## Contexto

La regla anterior prohibía a **toda** la infraestructura depender de la
aplicación. Eso es correcto para un adaptador de salida (persistencia), pero
incorrecto para uno de entrada (web): un controller debe llamar a los casos de
uso. Además, el controller devolvía entidades de dominio, acoplando la API a la
persistencia.

## Decisión

1. **Adaptadores de entrada** (`..infrastructure.web..`) pueden depender de
   `application`, pero **no** de `domain`: reciben y devuelven DTOs.
2. **Adaptadores de salida** (`..infrastructure.persistence..`) implementan
   puertos del dominio y **no** dependen de `application`.
3. La aplicación expone DTOs (`TaskView`) y los construye desde el dominio.
4. Los puertos del dominio se llaman `*Port` (`TaskRepositoryPort`) y sus
   adaptadores `*Repository` o `*Adapter`.
5. Los beans singleton de Spring no pueden tener estado mutable: ArchUnit lo
   verifica si `@Service`, `@Component` o `@RestController` están en el
   classpath.

## Consecuencias

- El controller no puede filtrar entidades: la regla de capas falla si lo hace.
- Un adaptador nuevo debe declarar si es de entrada o de salida.
- La regla antigua `infraestructura_sin_aplicacion` se reemplaza por
  `persistencia_sin_aplicacion`, más precisa.

## Alternativas descartadas

- **Prohibir toda dependencia de infraestructura hacia aplicación:** rompe el
  patrón de adaptador de entrada.
- **Dejar el DTO como convención:** sin regla, el agente devuelve la entidad.
- **Spring en el classpath solo para la regla:** la regla usa nombres
  cualificados y se activa cuando Spring exista.
