"""Ajustes del servidor MCP local, leídos del mismo .env que la API."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT: Path = Path(__file__).resolve().parent.parent


class McpSettings(BaseSettings):
    """Variables de entorno del servidor MCP."""

    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    MCP_DATABASE_URL: str = ""
    DATABASE_URL: str = "sqlite:///./resto.db"
    ENVIRONMENT: str = "development"
    MCP_QUERY_MAX_ROWS: int = 100
    MCP_QUERY_TIMEOUT_SECONDS: int = 10
    MCP_PYTEST_TIMEOUT_SECONDS: int = 600

    @property
    def database_url(self) -> str:
        """URL de la BD de query_database: MCP_DATABASE_URL o, si está vacía, DATABASE_URL."""
        return self.MCP_DATABASE_URL or self.DATABASE_URL


@lru_cache
def get_settings() -> McpSettings:
    """Devuelve los ajustes en caché; los tests la limpian con cache_clear()."""
    return McpSettings()
