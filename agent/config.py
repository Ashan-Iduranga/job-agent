"""Paths and settings loaded from .env and sources.yaml."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"
PROMPTS_DIR = ROOT / "prompts"
DB_PATH = DATA_DIR / "jobs.db"
SOURCES_FILE = ROOT / "sources.yaml"
PROFILE_FILE = ROOT / "profile.md"

load_dotenv(ROOT / ".env")

USER_AGENT = "InternshipJobAgent/0.1 (personal, non-commercial; polite crawler)"


def _env_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.split("#")[0].strip().lower() in {"1", "true", "yes", "on"}


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, "").split("#")[0].strip())
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Runtime settings from the environment."""

    dashboard_host: str = os.getenv("DASHBOARD_HOST", "127.0.0.1").split("#")[0].strip()
    dashboard_port: int = _env_int("DASHBOARD_PORT", 8765)
    web_search: bool = _env_bool("WEB_SEARCH", True)
    rank_batch_size: int = _env_int("RANK_BATCH_SIZE", 20)
    request_delay: int = _env_int("REQUEST_DELAY_SECONDS", 4)
    claude_bin: str = os.getenv("CLAUDE_BIN", "claude").split("#")[0].strip()
    claude_timeout: int = _env_int("CLAUDE_TIMEOUT_SECONDS", 600)
    expire_no_deadline_days: int = _env_int("EXPIRE_NO_DEADLINE_DAYS", 45)


SETTINGS = Settings()


def load_sources_config() -> dict[str, Any]:
    """Read sources.yaml as a dict."""
    with SOURCES_FILE.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def ensure_dirs() -> None:
    """Create runtime folders if missing."""
    for d in (DATA_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)
