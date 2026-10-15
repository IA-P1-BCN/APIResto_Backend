# agent-docs · HU-25

> Equipo: [líder](lead.md) · Depende de: [`agent-router`](agent-router.md) · En paralelo
> con: [`agent-tests`](agent-tests.md)

## Tarea
Documentar los dos endpoints de la HU-25 en `docs/api.md`, con el estilo existente.

## Archivos
Solo `docs/api.md`. No toca código: Swagger lo dejó `agent-router`.

## Lecturas
`AGENTS.md` → `specs/ontology.md` → la spec de HU-25 → `docs/api.md` completo → el código
terminado (router, schemas y servicio) para copiar los `detail` y `code` reales.

## Contenido
- Sección "Perfil propio (`/users/me`) · HU-25", junto a la de Usuarios.
- En la sección de Usuarios, la frase "solo `admin`" nombra la excepción y enlaza a la nueva.
- Cualquier rol autenticado; campos editables y reglas de `null`; `role` / `is_active` → 422;
  email único y en minúsculas (R-01, 409); respuesta `UserOut` sin `password_hash`.
- Cambio de contraseña: body, 204 sin cuerpo, bcrypt (R-02).
- Tabla de errores: 400 `password_not_set`, 401 `unauthorized`, 403
  `invalid_current_password`, 409 `conflict`, 422 `validation_error`, 422 `same_password`.
- Nota: cambiar la contraseña no cierra otras sesiones (queda para la HU de refresh/logout).

## Reglas
No inventa `detail` ni `code`: los copia del código. No crea la colección Bruno (no existe
en `dev`). No hace commit ni push. No toca `docs/ai-log.md`.

## Resultado
Entregado y aceptado sin cambios: 64 líneas añadidas y 1 modificada (la frase de "solo
`admin`"), sin borrar nada.
