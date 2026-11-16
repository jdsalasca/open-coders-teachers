# Seguridad

## Reportar una vulnerabilidad

No abras un issue público. Usa **GitHub Security Advisories**:
<https://github.com/jdsalasca/open-coders-teachers/security/advisories/new>

Incluye:

- versión o commit afectado,
- pasos para reproducir,
- impacto esperado,
- si lo deseas, una propuesta de parche.

Recibirás respuesta en un plazo de 7 días hábiles.

## Alcance

Este repositorio contiene **configuración de linters y scripts de calidad**, no
una aplicación en producción. Los fallos relevantes son, por ejemplo:

- una regla de seguridad que no se ejecuta (falso negativo),
- un skip o supresión que permite código inseguro sin justificación,
- un secreto filtrado en el historial,
- una acción de CI con Supply-chain débil.

## Lo que ya se revisa

| Capa | Herramienta |
|---|---|
| Secretos | `gitleaks` |
| Patrones inseguros | `semgrep p/ci` |
| Go | `gosec` |
| Python | `ruff S` (bandit) |
| Node | `eslint-plugin-security` |
| Dependencias | `npm audit`, `govulncheck`, `pip-audit` |
| CI | acciones fijadas por SHA, sin `curl \| sh` |

## Versiones soportadas

Solo la rama `main`. No hay versiones publicadas.
