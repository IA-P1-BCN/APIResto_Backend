# Agente Especialista — Menús & Mesas

## Rol
Eres el especialista en `bruno/03-categories/`, `bruno/04-dishes/` y
`bruno/05-tables/`.

## Antes de empezar
1. Lee `AGENTS.md`.
2. Lee `specs/ontology.md`.
3. Lee `specs/HU-27-coleccion-bruno.md`.
4. Lee este archivo completo.

## Tareas
1. Revisa los `.bru` existentes en `bruno/03-categories/`,
   `bruno/04-dishes/` y `bruno/05-tables/`.
2. Asegúrate de que cada archivo tiene:
   - `meta { name, type: "http", seq: N }`
   - request con método, url `{{baseUrl}}/ruta`
   - `body:json` con payload de ejemplo extraído del schema real
   - `script:post-response` que guarde `token` y IDs
   - `tests` con asserts de status y shape
3. Verifica que se cubren los casos de error 401, 403, 404, 409, 422
   correspondientes a estos dominios.
4. Si falta algo, créalo siguiendo el estilo existente.
5. Reporta al líder al terminar.

## Prohibiciones
- No toques otras carpetas de `bruno/`.
- No toques `app/`, `tests/`, migraciones, CI ni despliegue.
- No inventes endpoints ni campos.