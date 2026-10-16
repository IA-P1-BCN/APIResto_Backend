---
description: Genera tests de pytest para un endpoint o módulo del backend
agent: build
---
Genera tests de pytest para: $ARGUMENTS

Antes de escribir, lee `AGENTS.md` (sección "Los tests son el contrato"), `specs/ontology.md` y las fixtures de @tests/conftest.py (`client`, `db`, `make_user`, `auth_headers`, `admin_headers`). Mira cómo están escritos los tests que ya existen del mismo tema y sigue su estilo.

Reglas:
- Un fichero `tests/test_<tema>.py` nuevo o, si ya existe uno del mismo tema y es tuyo, añade ahí. No modifiques tests de otras personas.
- Por cada endpoint: el caso feliz y al menos un error 4xx (401 sin token, 403 por rol, 404, 409 o 422, según aplique). Comprueba también los permisos por rol de `app/core/permissions.py`.
- Comprueba el formato de error estándar `{"detail", "code"}` cuando el endpoint lo devuelve.
- Nombres de test en español que digan el comportamiento (`test_cocina_no_puede_crear_pedidos`).
- Sin red ni servicios externos: si el código llama a uno, se simula.

Al terminar, ejecuta los tests nuevos con el pytest del entorno virtual (`.venv`) y después `ruff check .`. Si un test falla porque el código no hace lo que dice la spec, **no cambies el código de la app ni debilites el test**: explícame el fallo. Termina con una lista de los casos que cubre cada test.
