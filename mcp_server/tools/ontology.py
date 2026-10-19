"""Herramienta get_ontology: devuelve specs/ontology.md o una regla R-xx de su §4."""

import logging
import re
from typing import NoReturn

from mcp.server.mcpserver.exceptions import ToolError

from mcp_server.config import REPO_ROOT

logger = logging.getLogger("mcp_server.tools.ontology")

ONTOLOGY_RELATIVE_PATH = "specs/ontology.md"
RULE_ID_PATTERN = re.compile(r"R-\d{2}", re.IGNORECASE | re.ASCII)
RULES_SECTION_PATTERN = re.compile(r"^##\s+4\.")
SECTION_PATTERN = re.compile(r"^##\s")
RULE_ROW_PATTERN = re.compile(
    r"^\|\s*(R-\d{2})\s*\|\s*([^|]*?)\s*\|\s*(.*?)\s*\|\s*$", re.ASCII
)


def _reject(code: str, detail: str) -> NoReturn:
    """Registra el rechazo y lanza el ToolError con el formato "<code>: <detalle>"."""
    logger.warning("get_ontology rejected: %s", code)
    raise ToolError(f"{code}: {detail}")


def read_ontology() -> str:
    """Lee la ontología del disco en cada llamada (UTF-8, sin caché)."""
    return (REPO_ROOT / ONTOLOGY_RELATIVE_PATH).read_text(encoding="utf-8")


def parse_rules(content: str) -> dict[str, tuple[str, str]]:
    """Extrae las filas de la tabla de reglas de la §4: {rule_id: (prioridad, texto)}."""
    rules: dict[str, tuple[str, str]] = {}
    in_rules_section = False
    for line in content.splitlines():
        if RULES_SECTION_PATTERN.match(line):
            in_rules_section = True
            continue
        if in_rules_section and SECTION_PATTERN.match(line):
            break
        if not in_rules_section:
            continue
        match = RULE_ROW_PATTERN.match(line.strip())
        if match:
            rule_id, priority, text = match.groups()
            rules[rule_id.upper()] = (priority, text)
    return rules


def get_ontology(rule_id: str | None = None) -> dict:
    """Devuelve la ontología entera o la fila de una regla R-xx con su prioridad."""
    content = read_ontology()
    if rule_id is None:
        logger.info("get_ontology returned the full ontology")
        return {"path": ONTOLOGY_RELATIVE_PATH, "content": content}
    if not RULE_ID_PATTERN.fullmatch(rule_id):
        _reject("invalid_rule_id", "rule_id must look like 'R-02'")
    normalized = rule_id.upper()
    rule = parse_rules(content).get(normalized)
    if rule is None:
        _reject("rule_not_found", f"rule {normalized} does not exist in {ONTOLOGY_RELATIVE_PATH}")
    priority, text = rule
    logger.info("get_ontology returned rule %s", normalized)
    return {"rule_id": normalized, "priority": priority, "text": text}
