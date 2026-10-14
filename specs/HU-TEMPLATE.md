# HU-XX · Título de la historia

> Plantilla de spec por HU. Copia este fichero a `specs/HU-XX-descripcion.md`, rellénalo
> **antes de escribir código** y bórrate esta guía. Vocabulario: `specs/ontology.md`.

<!--
CÓMO ESTABLECER LA SPEC (15-30 min, al empezar la sesión de la HU)

1. Lee la issue, `specs/ontology.md` (reglas R-xx) y el código que vas a tocar.
   No preguntes lo que ya responden; cítalo ("R-04", "`user_service.py`").
2. Copia esta plantilla y rellena lo que ya sabes. Lo que no sepas va en
   "Preguntas abiertas" con `[NEEDS CLARIFICATION: ...]`. No rellenes huecos adivinando.
3. Resuelve las preguntas abiertas de una en una, empezando por las que condicionan a
   las demás, con una persona del equipo o con tu agente (Claude Code: skill
   `grill-me-with-docs`; otro agente: pídele que te entreviste con una pregunta cada
   vez, 2-4 opciones y una recomendada). Tras cada respuesta, anótala al momento en
   "Decisiones de la sesión" (decisión, por qué, alternativas rechazadas).
4. Lo aplazado a propósito va en "Out of Scope", no se descarta en silencio.
5. Cuando no quede ningún `[NEEDS CLARIFICATION]`, commitea la spec como primer commit
   de la rama (`docs(HU-XX): spec`) y solo entonces planifica e implementa.
6. Si una decisión toca una regla de la ontología o el contrato de otra persona,
   avísala y actualiza `specs/ontology.md` en el mismo PR.
-->

> Issue: #NN · Prioridad Must/Should/Could · Escribe: ... · Revisa: ... ·
> Aprueba: Levi (PO).

## Problem Statement
Qué falla o falta hoy y para quién, en pocas líneas.

## Solution
Qué se va a construir, a alto nivel.

## User Stories
1. Como <rol>, quiero <capacidad>, para <beneficio>.

## Implementation Decisions
- Modelo: tablas/campos nuevos o cambiados (y migración de Alembic).
- Endpoints: método, ruta, rol permitido, códigos de respuesta.
- Reglas de negocio aplicables (`R-xx`) y casos límite.
- Capas afectadas (router → service → repository).

## Testing Decisions
- Casos felices y 4xx por endpoint; qué se prueba y qué no.

## Criterios de aceptación
- [ ] Criterio verificable 1.

## Out of Scope
- Lo que no se hace en esta HU (y dónde queda anotado).

## Preguntas abiertas
- [NEEDS CLARIFICATION: ...] (vacío = spec lista para implementar)

## Decisiones de la sesión
### <Título de la decisión>
- **Decisión**:
- **Por qué**:
- **Alternativas rechazadas**:
