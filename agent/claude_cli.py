"""Run headless Claude Code (`claude -p`) from Python."""
from __future__ import annotations

import logging
import shutil
import subprocess

from .config import ROOT, SETTINGS

log = logging.getLogger(__name__)


class ClaudeError(RuntimeError):
    """claude -p failed or is not installed."""


def run_claude(prompt: str, allowed_tools: str, timeout: int | None = None) -> str:
    """Run `claude -p <prompt> --allowedTools <tools>` in the project root and return stdout."""
    exe = shutil.which(SETTINGS.claude_bin)
    if not exe:
        raise ClaudeError(f"'{SETTINGS.claude_bin}' not found on PATH (set CLAUDE_BIN in .env)")
    cmd = [exe, "-p", prompt, "--allowedTools", allowed_tools, "--output-format", "text"]
    log.info("Running claude -p (tools: %s)", allowed_tools)
    try:
        proc = subprocess.run(
            cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout or SETTINGS.claude_timeout, stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as exc:
        raise ClaudeError(f"claude -p timed out after {exc.timeout}s") from exc
    if proc.returncode != 0:
        raise ClaudeError(f"claude -p exited {proc.returncode}: {(proc.stderr or proc.stdout)[-500:]}")
    return proc.stdout
