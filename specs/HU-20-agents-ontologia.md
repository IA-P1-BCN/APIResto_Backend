# HU-20 · AGENTS.md y ontología del dominio

> Issue: #62 · Prioridad Must · Nivel Esencial · Escribe: Manon · Revisa: Rita ·
> Aprueba: Levi (PO). Vocabulario: `specs/ontology.md`.

## Problem Statement
El equipo usa agentes de IA (Claude Code ×4, OpenCode ×1) sobre el mismo repo. Sin un
contexto común, cada agente inventa nombres, roles y reglas, y cada persona pega a mano
su propio resumen del proyecto. El resultado es código inconsistente y revisiones más
largas.

## Solution
Dos ficheros versionados en el repo: `AGENTS.md` (cómo trabajar aquí y dónde mirar) y
`specs/ontology.md` (vocabulario y reglas del dominio de identidad y acceso). Cualquier
agente los lee al empezar y trabaja con el mismo vocabulario. `CLAUDE.md` los enlaza con
`@AGENTS.md`.

## User Stories
1. Como desarrolladora, quiero que mi agente conozca el stack y los comandos, para no
   tener que explicarlos en cada sesión.
2. Como desarrollador, quiero que el agente sepa qué no puede hacer (secretos, push a
   `dev`, borrar tests), para que no cause daños.
3. Como revisora, quiero que el código generado use los nombres de la ontología, para
   revisar contra un vocabulario único.
4. Como Product Owner, quiero aprobar la ontología, que es la spec general, para
   controlar las reglas de negocio que siguen los agentes.
5. Como usuaria de Claude Code, quiero que `CLAUDE.md` apunte a `AGENTS.md`, para no
   mantener dos copias.
6. Como Carla (OpenCode), quiero que `AGENTS.md` sea neutral respecto a la herramienta,
   para que me sirva igual que a quienes usan Claude Code.
7. Como agente, quiero saber que, sin spec propia de la HU, debo usar la ontología y la
   issue y preguntar ante cualquier regla que falte, para no inventar requisitos.
8. Como Scrum Master, quiero que `AGENTS.md` explique cómo rellenar `docs/ai-log.md`,
   para cumplir el entregable de trazabilidad.
9. Como agente, quiero saber qué roles existen (`admin`, `waiter`, `kitchen`,
   `bartender`, `customer`) y qué estación ve cada uno, para aplicar permisos
   correctos.
10. Como equipo, quiero que la ontología marque qué es Must/Should/Could, para que el
    agente no implemente por su cuenta lo que se ha recortado.

## Implementation Decisions
- `specs/ontology.md`: entidades `User`, `Role` (enum de 5 valores, sin tabla),
  `AccessToken` (JWT sin estado), `RefreshToken`, `RevokedToken` (Must);
  `EmailVerificationToken`, `PasswordResetToken` (Should); `SocialAccount` y TOTP
  (Could). Reglas numeradas R-01…R-13 que las issues, los PR y el ai-log citan por id. Glosario
  EN↔ES. Referencias externas de una línea (`Reservation`, `Order`, `Category.station`).
- Identificadores en inglés, prosa en español.
- `AGENTS.md`: stack, estructura y capas, comandos, convenciones, regla "sin spec
  propia: ontología + issue, y preguntar si falta una regla", los tests son el contrato, lista de "no hagas", revisión de seguridad,
  uso de `docs/ai-log.md`, resumen de la DoD.
- `CLAUDE.md` mínimo: `@AGENTS.md`.
- Decisiones de fondo recogidas en `specs/ontology.md` (alcance, tokens, ciclo de vida de
  `User`, asignación de roles, refresh/logout, invariantes, `station`).
- El contenido refleja el **código real** de `dev` (p. ej. `Role` es enum, la capa de
  datos entonces era `crud/`; HU-29 la sustituyó por `repositories/`), no la documentación de arquitectura, que estaba desfasada.

## Testing Decisions
- Es una HU de documentación: el "test" es la prueba de humo. En una sesión nueva de
  Claude Code y en OpenCode se pregunta: "¿qué roles existen y qué no debes hacer?". La
  respuesta debe coincidir con `ontology.md` y `AGENTS.md`.
- Un buen test comprueba el comportamiento externo (qué responde/hace el agente), no
  el texto literal de los ficheros.
- Punto de prueba único (seam): la sesión del agente. [A confirmar con el equipo.]
- Resultado de la prueba de humo: una entrada en `docs/ai-log.md`.

## Criterios de aceptación
- [ ] `AGENTS.md`, `CLAUDE.md` (`@AGENTS.md`) y `specs/ontology.md` en `dev` vía PR
- [ ] Comandos y estructura de `AGENTS.md` verificados contra el repo real
- [ ] Ontología aprobada por Levi (PO)
- [ ] Prueba de humo superada con Claude Code y con OpenCode, registrada en el ai-log
- [ ] Sin secretos ni contenido de documentación personal en los ficheros
- [ ] PR < 400 líneas, revisado por Rita

## Out of Scope
- Specs de las demás HU: el equipo decidió (13/10) no escribir una spec por HU; la spec
  general es la ontología + `AGENTS.md`.
- Implementar `bartender`, `station` o cualquier entidad en código (otras HU).
- Skills, comandos y subagentes personalizados de OpenCode (Could).
- Configurar herramientas y modelos (HU-21).

## Further Notes
- Resuelto: reparto M/S/C (Levi); caducidad del refresh y rate limiting (los fija
  quien lleve auth en su HU); `bartender` (decidido).
- Revisar `AGENTS.md` cuando HU-23 (Alembic) y la HU de capas lleguen a `dev`.
