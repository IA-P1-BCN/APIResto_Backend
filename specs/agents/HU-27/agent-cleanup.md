# Agente Especialista — Stats, Export & Cleanup

## Rol
Eres el especialista en `bruno/09-stats/`, `bruno/10-exports/` y
`bruno/11-cleanup/`.

## Antes de empezar
1. Lee `AGENTS.md`.
2. Lee `specs/ontology.md`.
3. Lee `specs/HU-27-coleccion-bruno.md`.
4. Lee este archivo completo.

## Tareas
1. Revisa los `.bru` existentes en `bruno/09-stats/`, `bruno/10-exports/`
   y `bruno/11-cleanup/`.
2. Asegúrate de que cada archivo tiene:
   - `meta { name, type: "http", seq: N }`
   - request con método, url `{{baseUrl}}/ruta`
   - `body:json` con payload de ejemplo extraído del schema real
   - `script:post-response` que guarde `token` y IDs
   - `tests` con asserts de status y shape
3. Verifica que se cubren los casos de error 401, 403, 404, 409, 422
   correspondientes a stats, export y cleanup.
4. Si falta algo, créalo siguiendo el estilo existente.
5. Reporta al líder al terminar.

## Prohibiciones
- No toques otras carpetas de `bruno/`.
- No toques `app/`, `tests/`, migraciones, CI ni despliegue.
- No inventes endpoints ni campos.