"""Arranque del servidor MCP por stdio: python -m mcp_server."""

import logging
import sys

from mcp_server.config import get_settings

logger = logging.getLogger("mcp_server")


def configure_logging() -> None:
    """Envía los logs a stderr: stdout es del protocolo MCP."""
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main() -> int:
    """Arranca el servidor por stdio; con ENVIRONMENT=production sale con código 1."""
    configure_logging()
    if get_settings().ENVIRONMENT.strip().lower() == "production":
        sys.stderr.write("mcp_server refuses to start with ENVIRONMENT=production\n")
        logger.error("startup_refused: ENVIRONMENT=production")
        return 1
    from mcp_server.server import build_server

    logger.info("starting resto-api-dev MCP server over stdio")
    build_server().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
