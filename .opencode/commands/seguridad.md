---
description: Revisión de seguridad de los cambios (por defecto, la rama actual frente a dev), sin modificar nada
agent: seguridad
subtask: true
---
Revisa la seguridad de este cambio del backend.

Rango de git a revisar: `$ARGUMENTS`. Si está vacío, usa `origin/dev...HEAD` (lo que la rama actual añade sobre `dev`).

Ficheros que cambian en la rama actual frente a `dev`:
!`git diff --stat origin/dev...HEAD`

Obtén el diff completo del rango con `git diff <rango>` y, si necesitas contexto, lee los ficheros afectados.
