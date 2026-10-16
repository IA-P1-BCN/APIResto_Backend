---
description: Revisión de una PR (por defecto, la rama actual frente a dev), sin modificar nada
agent: revisor
---
Revisa este cambio del backend.

Rango de git a revisar: `$ARGUMENTS`. Si está vacío, usa `origin/dev...HEAD` (lo que la rama actual añade sobre `dev`).

Si te han adjuntado el diff (`pr.diff`), revisa ese diff y no lo vuelvas a pedir. Si no, empieza con `git diff --stat <rango>` y lee el diff con `git diff <rango>`, fichero a fichero si es grande.

Lee solo los ficheros que necesites para entender un posible problema (como mucho cinco) y no recorras el repositorio entero: tu respuesta es lo único que importa.
