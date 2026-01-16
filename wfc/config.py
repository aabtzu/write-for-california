"""Shared configuration for WFC tools."""

from pathlib import Path

# Site configuration
BASE_URL = "https://writeforcalifornia.com"
ARCHIVE_URL = f"{BASE_URL}/archive"

# State files directory
STATE_DIR = Path.home() / ".wfc"
STATE_DIR.mkdir(exist_ok=True)

# Active hours for monitoring (6am - 6pm)
ACTIVE_HOUR_START = 6
ACTIVE_HOUR_END = 18
