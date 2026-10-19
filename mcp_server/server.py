"""Construcción del servidor MCP con sus tres herramientas."""

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from mcp_server.tools.database import query_database
from mcp_server.tools.ontology import get_ontology
from mcp_server.tools.pytest_runner import run_pytest

SERVER_NAME = "resto-api-dev"

INSTRUCTIONS = (
    "Local development tools for the Resto-API_Backend repository. "
    "query_database runs one read-only SELECT/WITH query against the local database "
    "(secret columns and tables are rejected or redacted). "
    "run_pytest runs pytest on the whole suite or a path inside tests/ and returns a short summary. "
    "get_ontology returns specs/ontology.md or a single R-xx rule, to cite the project vocabulary exactly."
)

QUERY_DATABASE_DESCRIPTION = (
    "Run a single read-only SELECT or WITH query against the local database and return "
    "columns and rows. Writes, multiple statements and secret columns or tables are rejected; "
    "secret values in the result are redacted. 'limit' caps the rows (default and maximum MCP_QUERY_MAX_ROWS)."
)

RUN_PYTEST_DESCRIPTION = (
    "Run pytest without a shell on the whole suite or on 'target' (a path inside tests/, "
    "optionally with ::node), optionally filtered by 'keyword' (-k). Returns the exit code, "
    "whether it passed, the summary line and the tail of the output."
)

GET_ONTOLOGY_DESCRIPTION = (
    "Return the full specs/ontology.md, or only the row of one rule when 'rule_id' is given "
    "(format R- plus two digits, e.g. R-02), with its priority and exact text."
)


def build_server() -> MCPServer:
    """Crea el servidor MCP y registra query_database, run_pytest y get_ontology."""
    server = MCPServer(SERVER_NAME, instructions=INSTRUCTIONS)
    server.tool(
        name="query_database",
        description=QUERY_DATABASE_DESCRIPTION,
        annotations=ToolAnnotations(read_only_hint=True),
    )(query_database)
    server.tool(
        name="run_pytest",
        description=RUN_PYTEST_DESCRIPTION,
    )(run_pytest)
    server.tool(
        name="get_ontology",
        description=GET_ONTOLOGY_DESCRIPTION,
        annotations=ToolAnnotations(read_only_hint=True),
    )(get_ontology)
    return server
