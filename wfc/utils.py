"""Shared utilities for WFC tools."""

import re
import subprocess
from datetime import datetime
from typing import Optional

import requests

from .config import ARCHIVE_URL, BASE_URL, ACTIVE_HOUR_START, ACTIVE_HOUR_END


def send_notification(title: str, message: str, url: Optional[str] = None):
    """Send a macOS alert popup with option to open URL."""
    if url:
        # Dialog with two buttons - "Go to page" and "OK thanks"
        script = f'''
        set theResult to display alert "{title}" message "{message}" buttons {{"OK thanks", "Go to page"}} default button "Go to page"
        if button returned of theResult is "Go to page" then
            open location "{url}/comments"
        end if
        '''
        subprocess.run(["osascript", "-e", script])
    else:
        subprocess.run([
            "osascript", "-e",
            f'display alert "{title}" message "{message}"'
        ])


def timestamp() -> str:
    """Return current time formatted for logging."""
    return datetime.now().strftime("%H:%M:%S")


def is_active_hours() -> bool:
    """Check if we're within active monitoring hours."""
    hour = datetime.now().hour
    return ACTIVE_HOUR_START <= hour < ACTIVE_HOUR_END


def get_latest_dbd_url() -> Optional[str]:
    """Fetch the archive and find the most recent DBD post URL."""
    try:
        response = requests.get(ARCHIVE_URL, timeout=30)
        response.raise_for_status()

        # Find all DBD post URLs (pattern: /p/dbd-MM-DD-YYYY-slug)
        matches = re.findall(r'/p/(dbd-\d{2}-\d{2}-\d{4}-[^"\']+)', response.text)

        if matches:
            # Return the first match (most recent)
            return f"{BASE_URL}/p/{matches[0]}"
        return None
    except requests.RequestException as e:
        print(f"[{timestamp()}] Error fetching archive: {e}")
        return None


def get_comment_count(url: str) -> Optional[int]:
    """Fetch the page and extract the comment count."""
    try:
        comments_url = f"{url}/comments" if not url.endswith("/comments") else url
        # Add cache-busting to get fresh data
        headers = {"Cache-Control": "no-cache", "Pragma": "no-cache"}
        response = requests.get(f"{comments_url}?t={int(datetime.now().timestamp())}",
                                headers=headers, timeout=30)
        response.raise_for_status()

        # Look for "N Comments" pattern in the page
        match = re.search(r'(\d+)\s*[Cc]omments', response.text)
        if match:
            return int(match.group(1))
        return None
    except requests.RequestException as e:
        print(f"[{timestamp()}] Error fetching page: {e}")
        return None
