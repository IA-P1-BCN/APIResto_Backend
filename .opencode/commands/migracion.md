---
description: Crea la migración de Alembic de un cambio de modelos con el siguiente número libre (sin argumentos, solo informa)
agent: build
---
Cambio de modelos: $ARGUMENTS

Migraciones que ya hay en `dev`:
!`git ls-tree --name-only origin/dev migrations/versions/`

Migraciones de la rama actual:
!`git ls-files migrations/versions`

Usa siempre el `alembic` del entorno virtual (`.venv`). La base de datos se elige con la variable `DATABASE_URL` (por ejemplo, `sqlite:///./tmp-migraciones.db`); no inventes otras variables ni nombres de fichero: cópialos de la lista de arriba. Pasos:
1. Comprueba en las listas de arriba que no hay dos migraciones con el mismo número y, al generar, que `alembic heads` da **una sola cabeza**. Si no, para y explícalo: hay que renumerar una antes de seguir.
2. El número nuevo es el mayor de `dev` y de la rama, más uno. Avisa de que si otra PR abierta usa ese mismo número, la que entre segunda tendrá que renumerarse (pasó con la `0005`).
3. **Si `$ARGUMENTS` está vacío, para aquí sin ejecutar ningún comando**: con las dos listas de arriba basta. Responde solo con tres líneas (si hay números repetidos, última migración y número siguiente) y no describas los pasos siguientes.
4. Genera la migración contra una BD SQLite temporal al día: `alembic revision --autogenerate --rev-id NNNN -m "descripción corta"`.
5. Déjala como las que ya hay: sin los comentarios que añade Alembic y con valores por defecto válidos también en PostgreSQL (`sa.false()`, `'0'`). Si cambia datos existentes, convierte los datos en `upgrade` y al revés en `downgrade`.
6. Prueba `alembic upgrade head`, `alembic downgrade -1`, otra vez `upgrade head` y `alembic check` en la BD temporal, y `pytest tests/test_migrations.py`.
7. Recuerda añadir la migración a la lista de `docs/deploy.md` (sección "Migraciones con Alembic").
