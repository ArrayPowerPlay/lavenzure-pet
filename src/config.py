"""Load the non-secret settings from config.yaml (and an optional dev-only .env into os.environ).

API keys are NOT read here: see ``api_keys`` (read when needed, saved in the system key store).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

with open(ROOT_DIR / "config.yaml", encoding="utf-8") as _f:
    _config: dict[str, Any] = yaml.safe_load(_f)


def get(path: str, default: Any = None) -> Any:
    """Read a dotted config path, e.g. get('system_status.poll_interval_seconds')."""
    node: Any = _config
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node

