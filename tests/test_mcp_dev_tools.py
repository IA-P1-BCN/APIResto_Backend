"""Tests de run_pytest y get_ontology del servidor MCP (HU-39); pytest nunca se lanza de verdad."""

import subprocess
import sys

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from mcp_server.config import REPO_ROOT, get_settings
from mcp_server.tools import pytest_runner
from mcp_server.tools.ontology import get_ontology, parse_rules, read_ontology
from mcp_server.tools.pytest_runner import (
    BASE_COMMAND,
    OUTPUT_TAIL_LINES,
    find_summary,
    run_pytest,
    tail_output,
)

PYTEST_TIMEOUT = 42
EXPECTED_BASE = [sys.executable, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider"]


class FakeRun:
    """Sustituto de subprocess.run que registra las llamadas y devuelve una respuesta fija."""

    def __init__(self, returncode=0, stdout="", stderr="", raises=None):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.raises = raises
        self.calls = []

    def __call__(self, args, **kwargs):
        self.calls.append((args, kwargs))
        if self.raises is not None:
            raise self.raises
        return subprocess.CompletedProcess(args, self.returncode, self.stdout, self.stderr)


@pytest.fixture
def pytest_settings(monkeypatch):
    """Fija el tiempo máximo de run_pytest y limpia la caché de ajustes."""
    monkeypatch.setenv("MCP_PYTEST_TIMEOUT_SECONDS", str(PYTEST_TIMEOUT))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def fake_run(monkeypatch, pytest_settings):
    """Instala un FakeRun que pasa y lo devuelve para inspeccionarlo."""
    fake = FakeRun(stdout="...\n3 passed in 0.12s\n")
    monkeypatch.setattr(pytest_runner.subprocess, "run", fake)
    return fake


def _error_code(exc_info) -> str:
    """Código del ToolError (lo que va antes de ':')."""
    return str(exc_info.value).split(":", 1)[0]


def test_base_command_es_el_de_la_spec():
    assert [sys.executable, *BASE_COMMAND] == EXPECTED_BASE


def test_run_pytest_lanza_el_comando_exacto_sin_shell(fake_run):
    result = run_pytest("tests/test_health.py", "health and not cors")
    assert len(fake_run.calls) == 1
    args, kwargs = fake_run.calls[0]
    expected = [*EXPECTED_BASE, "tests/test_health.py", "-k", "health and not cors"]
    assert args == expected
    assert kwargs["cwd"] == REPO_ROOT
    assert kwargs["shell"] is False
    assert kwargs["timeout"] == PYTEST_TIMEOUT
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["check"] is False
    assert kwargs["stdin"] is subprocess.DEVNULL
    assert result["command"] == expected


def test_keyword_va_como_un_solo_argumento(fake_run):
    run_pytest(keyword="a and (b or c) and not d")
    args, _ = fake_run.calls[0]
    assert args[args.index("-k") + 1] == "a and (b or c) and not d"
    assert args.count("-k") == 1


def test_sin_argumentos_lanza_la_suite_entera(fake_run):
    run_pytest()
    args, _ = fake_run.calls[0]
    assert args == EXPECTED_BASE


def test_target_con_nodo_se_acepta(fake_run):
    run_pytest("tests/test_health.py::test_health")
    args, _ = fake_run.calls[0]
    assert args[-1] == "tests/test_health.py::test_health"


def test_resultado_cuando_pasa(fake_run):
    result = run_pytest("tests/test_health.py")
    assert result["exit_code"] == 0
    assert result["passed"] is True
    assert result["timed_out"] is False
    assert result["summary"] == "3 passed in 0.12s"
    assert isinstance(result["duration_seconds"], float)


def test_resultado_cuando_falla(monkeypatch, pytest_settings):
    fake = FakeRun(
        returncode=1,
        stdout="F..\n=========== 1 failed, 2 passed in 0.30s ===========\n",
    )
    monkeypatch.setattr(pytest_runner.subprocess, "run", fake)
    result = run_pytest("tests/test_health.py")
    assert result["exit_code"] == 1
    assert result["passed"] is False
    assert result["summary"] == "1 failed, 2 passed in 0.30s"


def test_output_tail_se_recorta_a_las_ultimas_lineas(monkeypatch, pytest_settings):
    stdout = "\n".join(f"line {i}" for i in range(300)) + "\n"
    fake = FakeRun(stdout=stdout, stderr="warning final\n")
    monkeypatch.setattr(pytest_runner.subprocess, "run", fake)
    result = run_pytest()
    lines = result["output_tail"].splitlines()
    assert len(lines) == OUTPUT_TAIL_LINES == 200
    assert lines[-1] == "warning final"
    assert lines[-2] == "line 299"
    assert "line 0" not in lines


def test_timeout_devuelve_timed_out_sin_error(monkeypatch, pytest_settings):
    fake = FakeRun(
        raises=subprocess.TimeoutExpired(cmd=["pytest"], timeout=PYTEST_TIMEOUT, output=b"partial\n")
    )
    monkeypatch.setattr(pytest_runner.subprocess, "run", fake)
    result = run_pytest()
    assert result["timed_out"] is True
    assert result["exit_code"] is None
    assert result["passed"] is False
    assert result["summary"] == f"timed out after {PYTEST_TIMEOUT} seconds"
    assert "partial" in result["output_tail"]


@pytest.mark.parametrize(
    "target",
    [
        "../app",
        "tests/../app",
        "app/main.py",
        str(REPO_ROOT / "tests" / "test_health.py"),
        "/etc/passwd",
        "C:/Windows",
        "tests/does_not_exist.py",
        "--cov",
        "-p",
    ],
)
def test_target_invalido_se_rechaza_sin_lanzar_pytest(fake_run, target):
    with pytest.raises(ToolError) as exc_info:
        run_pytest(target)
    assert _error_code(exc_info) == "invalid_target"
    assert fake_run.calls == []


@pytest.mark.parametrize("keyword", ["-p x", "--cov=app", " -x"])
def test_keyword_invalido_se_rechaza_sin_lanzar_pytest(fake_run, keyword):
    with pytest.raises(ToolError) as exc_info:
        run_pytest(keyword=keyword)
    assert _error_code(exc_info) == "invalid_keyword"
    assert fake_run.calls == []


def test_find_summary_toma_la_ultima_linea_de_resumen():
    stdout = "AssertionError: 1 == 2\n==== 2 failed, 5 passed, 1 skipped in 1.00s ====\n"
    assert find_summary(stdout) == "2 failed, 5 passed, 1 skipped in 1.00s"
    assert find_summary("", "no tests ran in 0.01s\n") == "no tests ran in 0.01s"
    assert find_summary("ImportError while loading conftest\n") == ""


def test_tail_output_une_stdout_y_stderr():
    assert tail_output("a\nb\n", "c\n", max_lines=2) == "b\nc"


def test_get_ontology_sin_argumentos_devuelve_el_archivo():
    result = get_ontology()
    assert result["path"] == "specs/ontology.md"
    assert result["content"] == (REPO_ROOT / "specs" / "ontology.md").read_text(encoding="utf-8")
    assert result["content"] == read_ontology()


@pytest.mark.parametrize("rule_id", ["R-02", "r-02"])
def test_get_ontology_devuelve_la_fila_de_r02(rule_id):
    result = get_ontology(rule_id)
    assert set(result) == {"rule_id", "priority", "text"}
    assert result["rule_id"] == "R-02"
    assert result["priority"] == "M"
    assert result["text"].startswith("Contraseña ≥ 8 caracteres")
    assert "password_hash" in result["text"]


def test_get_ontology_regla_inexistente_es_rule_not_found():
    with pytest.raises(ToolError) as exc_info:
        get_ontology("R-99")
    assert _error_code(exc_info) == "rule_not_found"


@pytest.mark.parametrize("rule_id", ["X-1", "R-2", "R-002", "R-02\n", ""])
def test_get_ontology_formato_invalido_es_invalid_rule_id(rule_id):
    with pytest.raises(ToolError) as exc_info:
        get_ontology(rule_id)
    assert _error_code(exc_info) == "invalid_rule_id"


def test_parse_rules_solo_lee_la_tabla_de_la_seccion_4():
    content = (
        "## 3. Otra\n"
        "| R-50 | M | fuera de la sección |\n"
        "## 4. Reglas\n"
        "| ID | Prioridad | Regla |\n"
        "|---|---|---|\n"
        "| R-01 | M | Primera regla |\n"
        "| R-02 | S | Segunda con `código` |\n"
        "## 5. Siguiente\n"
        "| R-03 | C | tampoco |\n"
    )
    assert parse_rules(content) == {
        "R-01": ("M", "Primera regla"),
        "R-02": ("S", "Segunda con `código`"),
    }
