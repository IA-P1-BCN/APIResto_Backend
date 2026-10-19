"""Herramienta run_pytest: lanza pytest sobre tests/ sin shell y resume el resultado."""

import logging
import re
import subprocess
import sys
import time
from pathlib import PurePosixPath, PureWindowsPath
from typing import NoReturn

from mcp.server.mcpserver.exceptions import ToolError

from mcp_server.config import REPO_ROOT, get_settings

logger = logging.getLogger("mcp_server.tools.pytest_runner")

OUTPUT_TAIL_LINES = 200
BASE_COMMAND = ("-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider")
SUMMARY_PATTERN = re.compile(
    r"\b\d+ (passed|failed|errors?|skipped|deselected|xfailed|xpassed)\b|\bno tests ran\b", re.IGNORECASE
)


def _reject(code: str, detail: str) -> NoReturn:
    """Registra el rechazo y lanza el ToolError con el formato "<code>: <detalle>"."""
    logger.warning("run_pytest rejected: %s", code)
    raise ToolError(f"{code}: {detail}")


def _is_absolute(path_part: str) -> bool:
    """Indica si la ruta es absoluta o lleva unidad, en estilo POSIX o Windows."""
    windows_path = PureWindowsPath(path_part)
    return (
        PurePosixPath(path_part).is_absolute()
        or windows_path.is_absolute()
        or bool(windows_path.drive)
        or path_part.startswith(("/", "\\"))
    )


def validate_target(target: str) -> str:
    """Comprueba que target sea una ruta relativa existente dentro de tests/."""
    if target.lstrip().startswith("-"):
        _reject("invalid_target", "target must not start with '-'")
    path_part = target.split("::", 1)[0]
    if not path_part.strip():
        _reject("invalid_target", "target must include a path inside tests/")
    if _is_absolute(path_part):
        _reject("invalid_target", "target must be a relative path inside tests/")
    tests_root = (REPO_ROOT / "tests").resolve()
    try:
        resolved = (REPO_ROOT / path_part).resolve()
        exists = resolved.exists()
    except (OSError, ValueError):
        _reject("invalid_target", "target is not a valid path")
    if not resolved.is_relative_to(tests_root):
        _reject("invalid_target", "target must be inside tests/")
    if not exists:
        _reject("invalid_target", "target does not exist")
    return target


def validate_keyword(keyword: str) -> str:
    """Comprueba que la expresión de -k no empiece por '-'."""
    if keyword.lstrip().startswith("-"):
        _reject("invalid_keyword", "keyword must not start with '-'")
    return keyword


def build_command(target: str | None = None, keyword: str | None = None) -> list[str]:
    """Construye la lista de argumentos de pytest, sin shell."""
    command = [sys.executable, *BASE_COMMAND]
    if target:
        command.append(target)
    if keyword:
        command.extend(["-k", keyword])
    return command


def find_summary(stdout: str, stderr: str = "") -> str:
    """Devuelve la última línea no vacía que parezca el resumen de pytest, sin los '='."""
    for text in (stdout, stderr):
        for line in reversed(text.splitlines()):
            cleaned = line.strip().strip("=").strip()
            if cleaned and SUMMARY_PATTERN.search(cleaned):
                return cleaned
    return ""


def tail_output(stdout: str, stderr: str, max_lines: int = OUTPUT_TAIL_LINES) -> str:
    """Devuelve las últimas max_lines líneas de stdout seguido de stderr."""
    lines = stdout.splitlines() + stderr.splitlines()
    return "\n".join(lines[-max_lines:])


def _as_text(value: str | bytes | None) -> str:
    """Convierte la salida parcial de un TimeoutExpired a texto."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def run_pytest(target: str | None = None, keyword: str | None = None) -> dict:
    """Lanza pytest (todo o una ruta de tests/) y devuelve código de salida y resumen."""
    if target:
        validate_target(target)
    if keyword:
        validate_keyword(keyword)
    command = build_command(target, keyword)
    timeout = get_settings().MCP_PYTEST_TIMEOUT_SECONDS
    started = time.perf_counter()
    timed_out = False
    exit_code: int | None
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
        exit_code = completed.returncode
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = None
        stdout = _as_text(exc.stdout)
        stderr = _as_text(exc.stderr)
    duration = round(time.perf_counter() - started, 3)
    summary = find_summary(stdout, stderr)
    if timed_out:
        logger.warning("run_pytest timed out after %s seconds", timeout)
        if not summary:
            summary = f"timed out after {timeout} seconds"
    logger.info(
        "run_pytest finished: exit_code=%s duration=%.3fs target=%s keyword=%s",
        exit_code,
        duration,
        target,
        keyword,
    )
    return {
        "exit_code": exit_code,
        "passed": exit_code == 0,
        "timed_out": timed_out,
        "summary": summary,
        "output_tail": tail_output(stdout, stderr),
        "duration_seconds": duration,
        "command": command,
    }
