"""Shared configuration for WFC tools."""

import os
from pathlib import Path

# State files directory
STATE_DIR = Path.home() / ".wfc"
STATE_DIR.mkdir(exist_ok=True)

# Environment file for site selection
ENV_FILE = STATE_DIR / "environment"

# Site configurations
SITES = {
    "prod": {
        "name": "Write For California",
        "base_url": "https://writeforcalifornia.com",
    },
    "test": {
        "name": "WFC Test",
        "base_url": "https://wfctest.substack.com",
    },
}

def get_environment() -> str:
    """Get current environment (prod or test)."""
    # Check env var first, then file, default to prod
    env = os.environ.get("WFC_ENV")
    if env and env in SITES:
        return env
    if ENV_FILE.exists():
        env = ENV_FILE.read_text().strip()
        if env in SITES:
            return env
    return "prod"

def set_environment(env: str) -> None:
    """Set the environment (prod or test)."""
    if env not in SITES:
        raise ValueError(f"Unknown environment: {env}. Must be one of: {list(SITES.keys())}")
    ENV_FILE.write_text(env)

def get_site_config() -> dict:
    """Get the current site configuration."""
    return SITES[get_environment()]

# Current site configuration (for backward compatibility)
_site = get_site_config()
BASE_URL = _site["base_url"]
ARCHIVE_URL = f"{BASE_URL}/archive"

# Active hours for monitoring (6am - 6pm)
ACTIVE_HOUR_START = 6
ACTIVE_HOUR_END = 18
