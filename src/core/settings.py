# src/core/settings.py
# Loads config.yaml from the project root and exposes typed constants used by all modules.
# This is the single source of truth for all configurable values.
# Supports environment variable overrides for production deployments (12-factor app).
# Import from here — never hardcode paths or config values in other modules.

import os
import yaml
from pathlib import Path

# Project root is two levels up from this file: src/core/settings.py -> src/core -> src -> project root
_PROJECT_ROOT = Path(__file__).parent.parent.parent

_CONFIG_PATH = _PROJECT_ROOT / "config.yaml"

if not _CONFIG_PATH.is_file():
    raise FileNotFoundError(
        f"config.yaml not found at {_CONFIG_PATH}. "
        "Ensure you are running from the project root and config.yaml exists."
    )

with open(_CONFIG_PATH, "r", encoding="utf-8") as _f:
    _cfg = yaml.safe_load(_f)

# --- API metadata ---
API_TITLE: str = _cfg["api"]["title"]
API_DESCRIPTION: str = _cfg["api"]["description"]
API_VERSION: str = _cfg["api"]["version"]
API_PREFIX: str = _cfg["api"]["prefix"]

# --- Server settings (with environment variable overrides for production) ---
SERVER_HOST: str = os.getenv("CONTEXT_API_HOST", _cfg["server"]["host"])
SERVER_PORT: int = int(os.getenv("CONTEXT_API_PORT", _cfg["server"]["port"]))
SERVER_RELOAD: bool = os.getenv("CONTEXT_API_RELOAD", str(_cfg["server"]["reload"])).lower() in ("true", "1")

# --- Context paths (all absolute, derived from project root) ---
_base = _PROJECT_ROOT / _cfg["context"]["base_path"]
DOMAINS_PATH: Path = _base / _cfg["context"]["domains_subdir"]
GLOBAL_PATH: Path = _base / _cfg["context"]["global_subdir"]
INTENT_MAP_PATH: Path = (
    _base
    / _cfg["context"]["mappings_subdir"]
    / _cfg["context"]["intent_map_file"]
)

# --- Intent resolution ---
DEFAULT_INTENT: str = _cfg["context"]["default_intent"]

# --- Validation ---
MAX_IDENTIFIER_LENGTH: int = _cfg["validation"]["max_identifier_length"]
