# Diagramas de la arquitectura agéntica · HU-27

Documentación visual de cómo se organizó el equipo de agentes (Claude Code) que revisó la colección
Bruno de HU-27 (issue #70). Spec de la HU: [`specs/HU-27-coleccion-bruno.md`](../../../specs/HU-27-coleccion-bruno.md).
Directrices de los agentes: en esta misma carpeta ([`lead.md`](lead.md) y `agent-*.md`).

## Qué muestra cada PNG

| Archivo | Contenido |
|---|---|
| [`lead.md`](lead.md) y `agent-*.md` | Directrices del agente líder y de los 5 especialistas. |
| [`esquema-visual-detallado.png`](esquema-visual-detallado.png) | Jerarquía completa de archivos agénticos, del NIVEL 0 (`AGENTS.md`, briefing, plan v3, ontología) al NIVEL 4 (`bruno/`). Muestra cómo cada nivel alimenta al siguiente y cómo el líder (`lead.md`) reparte las carpetas entre los 5 especialistas. |
| [`mapa-dependencias-agentes.png`](mapa-dependencias-agentes.png) | Dependencias entre agentes: `agent-auth` y `agent-menus` arrancan en paralelo; `agent-orders` y `agent-reservations` esperan a `agent-menus` (consumen `tableId`, `dishId`…); `agent-cleanup` espera a `agent-menus` y `agent-orders`. |
| [`esquema-archivos-por-nivel.png`](esquema-archivos-por-nivel.png) | Árbol del repo con los archivos agénticos etiquetados por nivel (0 directrices · 1 specs generales · 2 spec de HU-27 · 3 directrices de agentes · 4 entregable). Incluye `docs/ai-log.md`, donde está la entrada de HU-27. |

## Datos de la colección

- **141 requests** en 12 carpetas (`00-health` … `11-cleanup`).
- `app/routers/*.py` expone **48 endpoints HTTP**, de los que la colección cubre 44 (más `GET /` y `GET /health` en `app/main.py`, y el
  WebSocket `/ws/kitchen`, que se prueba a mano: ver `bruno/README.md`).

## Cómo regenerarlos

Desde la raíz del repo, con el `.venv` activo:

```bash
pip install matplotlib
python scripts/generate_agent_diagrams.py
```

El script crea esta carpeta si no existe y sobrescribe los tres PNG.

> **Nota:** `scripts/generate_agent_diagrams.py` no forma parte del runtime de la API. `matplotlib` no
> está en `requirements.txt` a propósito: solo se instala para regenerar estos diagramas.
