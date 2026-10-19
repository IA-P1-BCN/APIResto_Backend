"""Tests del servidor MCP (HU-39): registro de herramientas, cliente en proceso, stdio y producción."""

import json
import os
import subprocess
import sys

import anyio
import pytest
from mcp import Client, StdioServerParameters

from mcp_server.config import REPO_ROOT, get_settings
from mcp_server.server import SERVER_NAME, build_server
from mcp_server.tools.database import get_engine
from mcp_server.tools.ontology import get_ontology

EXPECTED_TOOLS = {"query_database", "run_pytest", "get_ontology"}
READ_ONLY_TOOLS = {"query_database", "get_ontology"}
CLIENT_TIMEOUT_SECONDS = 60
SUBPROCESS_TIMEOUT_SECONDS = 60


@pytest.fixture
def mcp_settings(monkeypatch, tmp_path):
    """Apunta el servidor a una SQLite temporal y limpia las cachés de ajustes y motor."""
    database_file = tmp_path / "mcp_server.db"
    monkeypatch.setenv("MCP_DATABASE_URL", f"sqlite:///{database_file.as_posix()}")
    monkeypatch.setenv("ENVIRONMENT", "test")
    get_settings.cache_clear()
    get_engine.cache_clear()
    yield
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_settings.cache_clear()
    get_engine.cache_clear()


def _subprocess_env(**overrides: str) -> dict[str, str]:
    """Entorno para lanzar el servidor como subproceso, basado en el actual."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(overrides)
    return env


def _run(coro_fn):
    """Ejecuta una corrutina con tiempo máximo dentro de un test síncrono."""

    async def _with_timeout():
        with anyio.fail_after(CLIENT_TIMEOUT_SECONDS):
            return await coro_fn()

    return anyio.run(_with_timeout)


def _list_tools_in_process():
    """Lista las herramientas con un cliente MCP en proceso."""

    async def _main():
        async with Client(build_server()) as client:
            return (await client.list_tools()).tools

    return _run(_main)


def _call_tool_in_process(name: str, arguments: dict):
    """Llama a una herramienta con un cliente MCP en proceso."""

    async def _main():
        async with Client(build_server()) as client:
            return await client.call_tool(name, arguments)

    return _run(_main)


def test_build_server_registra_exactamente_las_tres_herramientas(mcp_settings):
    tools = _list_tools_in_process()
    assert {tool.name for tool in tools} == EXPECTED_TOOLS
    assert len(tools) == len(EXPECTED_TOOLS)


def test_cada_herramienta_tiene_descripcion(mcp_settings):
    for tool in _list_tools_in_process():
        assert tool.description and tool.description.strip()


def test_query_database_y_get_ontology_son_de_solo_lectura(mcp_settings):
    tools = {tool.name: tool for tool in _list_tools_in_process()}
    for name in READ_ONLY_TOOLS:
        assert tools[name].annotations is not None
        assert tools[name].annotations.read_only_hint is True


def test_run_pytest_no_se_anota_como_solo_lectura(mcp_settings):
    tools = {tool.name: tool for tool in _list_tools_in_process()}
    annotations = tools["run_pytest"].annotations
    assert annotations is None or annotations.read_only_hint is not True


def test_el_servidor_se_llama_resto_api_dev_y_tiene_instrucciones(mcp_settings):
    async def _main():
        async with Client(build_server()) as client:
            return client.server_info, client.instructions

    server_info, instructions = _run(_main)
    assert SERVER_NAME == "resto-api-dev"
    assert server_info.name == "resto-api-dev"
    assert instructions and "query_database" in instructions


def test_get_ontology_ida_y_vuelta_devuelve_r02(mcp_settings):
    result = _call_tool_in_process("get_ontology", {"rule_id": "R-02"})
    assert result.is_error is False
    payload = json.loads(result.content[0].text)
    assert payload == get_ontology("R-02")
    assert payload["rule_id"] == "R-02"
    assert payload["priority"] == "M"
    assert "8 caracteres" in payload["text"]


def test_tool_error_llega_como_resultado_con_error_no_como_excepcion(mcp_settings):
    result = _call_tool_in_process("get_ontology", {"rule_id": "X-1"})
    assert result.is_error is True
    assert "invalid_rule_id" in result.content[0].text


def test_query_database_ida_y_vuelta_con_sqlite(mcp_settings):
    result = _call_tool_in_process("query_database", {"sql": "SELECT 1 AS one"})
    assert result.is_error is False
    payload = json.loads(result.content[0].text)
    assert payload["columns"] == ["one"]
    assert payload["rows"] == [[1]]
    assert payload["row_count"] == 1


def test_query_database_rechazo_llega_como_error(mcp_settings):
    result = _call_tool_in_process("query_database", {"sql": "DELETE FROM users"})
    assert result.is_error is True
    assert "read_only" in result.content[0].text


def test_arranque_real_por_stdio_lista_las_herramientas(tmp_path):
    env = _subprocess_env(
        ENVIRONMENT="test",
        MCP_DATABASE_URL=f"sqlite:///{(tmp_path / 'stdio.db').as_posix()}",
    )
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server"],
        cwd=str(REPO_ROOT),
        env=env,
    )

    async def _main():
        async with Client(params) as client:
            tools = (await client.list_tools()).tools
            rule = await client.call_tool("get_ontology", {"rule_id": "R-02"})
            return tools, rule

    tools, rule = _run(_main)
    assert {tool.name for tool in tools} == EXPECTED_TOOLS
    assert rule.is_error is False
    assert json.loads(rule.content[0].text)["rule_id"] == "R-02"


def test_con_environment_production_el_servidor_sale_con_codigo_1():
    completed = subprocess.run(
        [sys.executable, "-m", "mcp_server"],
        cwd=REPO_ROOT,
        env=_subprocess_env(ENVIRONMENT="production"),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert "production" in completed.stderr
