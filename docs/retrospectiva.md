# Retrospectiva P3 · Uso de IA en RestoAPI

Oct 21, 2026 · @Rita

## Resumen

Los agentes escribieron código correcto la mayoría de las veces; lo que falló fue el contexto que se les dio y lo que afirmaron sin comprobar.

La bitácora (`docs/ai-log.md`) recoge 40 entradas reales entre el 14 y el 20 de octubre de 2026: Anna 17, Rita 8, Levi 6, Carla 5 y Manon 4. Se usó Claude Code (Opus 5.5 y Sonnet 5.5), Claude en la app y OpenCode con modelos gratuitos (`big-pickle` y `deepseek-v4.1-flash-free`) para probar comandos y revisar PRs.

Tres hallazgos resumen el periodo:

- El fallo más repetido fue trabajar sobre un `dev` que ya no era el real.
- Los tests en verde no bastaron: varios errores solo se vieron usando el resultado.
- Escribir la spec primero y revisar con un segundo agente atrapó fallos reales.

## Qué ha funcionado

Cuatro prácticas dieron resultados comprobables en la bitácora.

- **Spec antes del código.** En HU-24, HU-26, HU-31 y HU-45 la issue llegó sin criterios de aceptación y la spec los fijó con preguntas una a una. Las decisiones humanas quedaron escritas con nombre, y el campo "trabajo descartado" se usó de verdad (los `replace()` anidados, `FORWARDED_ALLOW_IPS`, los pragmas de cobertura).
- **Revisión automática con OpenCode (HU-36).** El revisor encontró fallos reales en HU-37 (códigos de recuperación cortos y una carrera al gastar un código) y en HU-52 (dos peticiones a la vez con el mismo token). En ambos casos se corrigió y se comprobó en Postgres.
- **Probar los tests en falso.** En HU-45 ningún test detectaba restar los totales en lugar de sumar por líneas. En HU-31 se metieron 18 errores a propósito y los tests los detectaron todos. En la #158 y la #163 el diagrama se validó aplicando las migraciones en una BD vacía.
- **Equipos de agentes con archivos exclusivos (HU-25, HU-33, HU-34, HU-39).** El código salió bien a la primera. Los fallos de esas sesiones fueron de contexto o de reparto, no de código. En HU-39 el líder cerró un hueco de seguridad (leer datos sensibles pidiendo la fila entera) antes de seguir.

## Qué ha fallado

Los fallos se agrupan en seis patrones, y la causa raíz casi siempre es que alguien dio algo por sabido sin comprobarlo.

| Patrón | Dónde salió | Causa raíz |
| --- | --- | --- |
| Trabajar sobre un `dev` que no era el real | HU-53, HU-25, HU-26, HU-27, HU-31, HU-34, #158, #163 y las migraciones 0005 (#116 y #119) y 0009/0010 (HU-33 y HU-37) | Se dio contexto o se midió sin traer `dev`; nadie miró las PRs abiertas. La 0005 dejó el CI de `dev` en rojo |
| El agente afirma sin comprobar | HU-24 ("probado con Postgres", los tests usan SQLite), HU-31 (`FORWARDED_ALLOW_IPS`), HU-35 (`ALCHEMY_DATABASE_URL` inventada), HU-34 (12 tests en vez de 10), HU-26 (todo 422 con `errors`) | No leyó el código, el config o la versión instalada antes de afirmar |
| Tests en verde que no prueban lo que importa | HU-37 (QR sin `xmlns`), HU-15 (barras iguales), Frontend #54 (botón fuera de vista), HU-14 (CSV roto en Excel) | Solo se vio al usar el resultado real: navegador, captura medida o Excel |
| Alcance y entorno | HU-51 (`ruff format` sobre unos 30 archivos ajenos, `pip install` en el Python global), HU-26 (el agente ejecutó git en el ordenador de Rita) | Formateó una carpeta en vez de sus archivos; entendió un "puedes" como una orden |
| Specs sin casos límite | HU-45 (pedido vacío), HU-51 (zona horaria), HU-52 y HU-37 (concurrencia), HU-25 y HU-38 (cuenta sin contraseña) | La spec describía el caso normal y nadie preguntó qué pasa en el borde |
| Entrada floja | HU-31 (título "logout"), HU-34 (pedía un 80 % que ya se superaba), HU-24 y HU-26 (sin criterios) | La issue no se contrastó con el estado real antes de empezar |

## Lecciones y acciones propuestas

Siete reglas salen de lecciones que se repiten en dos o más entradas, el umbral que fija la propia bitácora para llevarlas a `AGENTS.md`. Se dejan como propuesta; pasarlas a una PR depende de si el equipo sigue usando el repositorio.

1. **Partir de `dev` actualizado.** Revisarlo al empezar y antes de cada paso: `AGENTS.md`, `specs/`, el Out of Scope de las HU recién integradas y el número de migración más alto, incluidas las PRs abiertas.
2. **No afirmar sin comprobar.** Ni "probado en X" ni una configuración de seguridad sin haber leído el código o el config de la versión que usa el proyecto.
3. **Probar los tests en falso.** Meter errores a propósito: que pasen a la primera no demuestra que comprueben lo que importa.
4. **Mirar el resultado real.** Lo que sale a un usuario o a un archivo se prueba en el navegador, en pantallas bajas o con el programa con el que se va a abrir (Excel).
5. **Acotar el alcance del agente.** Formatear y editar solo los archivos de la HU, usar siempre el `.venv`, y que el agente pase los comandos de git para ejecutarlos una persona.
6. **Casos límite en la spec.** Un apartado fijo con vacío, concurrencia, zona horaria y usuario sin contraseña.
7. **Buscar marcas de conflicto antes de commitear un merge.** `grep -n '^<<<<<<<\|^=======\|^>>>>>>>'` sobre los archivos tocados. Pasó dos veces: la #157 dejó 17 líneas de marcas y la #165 las reintrodujo, las dos en `docs/ai-log.md` dentro de `dev`.

Además, medir antes de elegir un modelo para CI (HU-36: `big-pickle` tardó más de 10 minutos y se cambió a `deepseek`) y pasar el revisor automático antes de pedir la revisión humana (HU-52).

## Estado de la bitácora y pendientes

La bitácora es útil, pero tiene huecos que conviene conocer antes de usarla como evidencia.

- **Conflicto resuelto.** Las marcas de la #157 se limpiaron en la #164; la #165 las reintrodujo y borró una entrada, y la #166 lo arregló; `docs/ai-log.md` queda sin marcas y con las 40 entradas.
- **HU sin entrada.** HU-28 ya tiene entradas, las de Carla. HU-20, HU-32 y HU-44 tienen spec en `specs/` y HU-30 aparece en la #163, pero ninguna de las cuatro tiene entrada en la bitácora.
- **Las entradas de Carla no cuentan sesiones de IA.** Sus 5 entradas (HU-28) diseñan categorías de log de la aplicación (ia, token y websocket) con la plantilla de la bitácora. Dos pares son casi idénticos (ia y token, ambos del 19/10), la issue sigue como #N y en todas el modelo es "OpenCode · modelo gratuito" sin nombrarlo. Como todas dicen "nada" en errores, no sirven para comparar OpenCode con Claude; esa comparación descansa en las pruebas de Anna.
- **Calidad desigual.** La entrada de HU-40 deja la lección en `//` y pone las preguntas de la spec en el campo del prompt. La lección de HU-39 es una explicación larga, no una línea.
- **Plantilla desfasada.** La entrada de HU-24 anota que `specs/HU-TEMPLATE.md` y la DoD de `AGENTS.md` siguen diciendo que aprueba Levi.
- **Migración sin número.** La #163 anota que la migración de tokens se llama `c50fc2ad47e1` y que `refresh_tokens.token_hash` no tiene `UNIQUE` ni índice. Renombrarla a `0011` cambia un id que Render y Neon pueden tener guardado, así que lo decide Anna.
