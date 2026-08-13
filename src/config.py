"""Load non-secret settings from config.yaml and secrets from .env."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

with open(ROOT_DIR / "config.yaml", "r", encoding="utf-8") as _f:
    _config: dict[str, Any] = yaml.safe_load(_f)


def get(path: str, default: Any = None) -> Any:
    """Read a dotted config path, e.g. get('system_status.poll_interval_seconds')."""
    node: Any = _config
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
