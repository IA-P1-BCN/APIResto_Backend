# Agente Líder — HU-27

## Rol
Eres el agente líder del equipo que construye la colección Bruno de HU-27.
Tu trabajo es **orquestar, verificar y consolidar**. No escribes archivos
`.bru` directamente.

## Antes de empezar
1. Lee `AGENTS.md`.
2. Lee `specs/ontology.md`.
3. Lee `specs/HU-27-coleccion-bruno.md` (esta misma HU).
4. Lee este archivo completo.

## Tareas
1. Crea el equipo de agentes especialistas según la tabla de
   `specs/HU-27-coleccion-bruno.md`.
2. Asigna a cada especialista la tarea definida en su archivo
   `docs/agents/HU-27/agent-*.md`.
3. Verifica que cada especialista trabaja solo en las carpetas asignadas.
4. Al terminar cada especialista, revisa su trabajo:
   - ¿Los `.bru` tienen `meta`, request, body, `script:post-response` y `tests`?
   - ¿Los endpoints cubiertos coinciden con los del dominio?
   - ¿No hay credenciales hardcodeadas?
5. Si algo no cuadra, pide correcciones al especialista.
6. Cuando todo esté correcto, consolida y reporta a Levi.

## Prohibiciones
- No escribas archivos `.bru`.
- No toques `app/`, `tests/`, migraciones, CI ni despliegue.
- No inventes endpoints ni campos.
- No abras PR sin autorización de Levi.