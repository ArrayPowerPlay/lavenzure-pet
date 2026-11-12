"""Application-wide logging to a rotating file (plus the console when there is one).

When the pet is started by autostart it runs under ``pythonw.exe``, which has no console, so
without a log file every error would vanish. Logs go to
``%LOCALAPPDATA%\\Lavenzure\\logs\\lavenzure.log`` (``logs/`` in the project folder off Windows).
"""
from __future__ import annotations

import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def log_dir() -> Path:
    """Folder that holds the log files (created if missing)."""
    base = os.environ.get("LOCALAPPDATA")
    if base:
        folder = Path(base) / "Lavenzure" / "logs"
    else:
        folder = Path(__file__).resolve().parent.parent / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def setup_logging(level: int = logging.INFO) -> Path:
    """Send all log records to a rotating file (1 MB x 3) and stderr if available.

    Also routes uncaught exceptions (main thread and worker threads) into the log.
    Returns the log file path.
    """
    log_file = log_dir() / "lavenzure.log"
    root = logging.getLogger()
    root.setLevel(level)
    formatter = logging.Formatter(LOG_FORMAT)

    file_handler = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    if sys.stderr is not None:  # None under pythonw.exe
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        root.addHandler(console)

    # Third-party HTTP clients are chatty at INFO.
    for noisy in ("httpx", "httpcore", "urllib3", "google_genai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    def _log_uncaught(exc_type, exc, tb) -> None:
        """Write an uncaught main-thread exception to the log instead of losing it."""
        logging.getLogger("uncaught").critical("Uncaught exception", exc_info=(exc_type, exc, tb))

    def _log_thread_uncaught(args) -> None:
        """Write an uncaught exception from a Python thread to the log."""
        logging.getLogger("uncaught").critical(
            "Uncaught exception in thread %s", getattr(args.thread, "name", "?"),
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = _log_uncaught
    threading.excepthook = _log_thread_uncaught
    return log_file
