"""Per-run log file plus console output."""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

from .config import LOG_DIR


def setup_logging(verbose: bool = False) -> Path:
    """Log to logs/run_YYYY-MM-DD_HHMM.log and stdout. Returns the log file path."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / f"run_{datetime.now():%Y-%m-%d_%H%M}.log"
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%H:%M:%S")
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    for h in (logging.FileHandler(path, encoding="utf-8"), logging.StreamHandler(sys.stdout)):
        h.setFormatter(fmt)
        root.addHandler(h)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    return path
