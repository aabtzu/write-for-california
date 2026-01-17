#!/usr/bin/env python3
"""
Substack Comment Monitor
Monitors the latest DBD post for new comments and sends macOS notifications.
Automatically finds the most recent DBD post each day.
"""

import re
import time
from typing import Tuple

from .config import STATE_DIR
from .utils import (
    get_comment_count,
    get_latest_dbd_url,
    is_active_hours,
    send_notification,
    timestamp,
)

CHECK_INTERVAL = 300  # seconds (5 minutes)
STATE_FILE = STATE_DIR / "monitor_state"


def read_state() -> Tuple[str, int]:
    """Read the stored URL and comment count."""
    if STATE_FILE.exists():
        content = STATE_FILE.read_text().strip()
        lines = content.split('\n')
        if len(lines) >= 2:
            return lines[0], int(lines[1])
    return "", 0


def save_state(url: str, count: int):
    """Save the current URL and comment count."""
    STATE_FILE.write_text(f"{url}\n{count}")


def main():
    print("Substack DBD Comment Monitor")
    print(f"Check interval: {CHECK_INTERVAL // 60} minutes")
    print("Active hours: 6:00 AM - 6:00 PM")
    print("Press Ctrl+C to stop\n")

    current_url = None

    while True:
        # Skip checking outside active hours
        if not is_active_hours():
            print(f"[{timestamp()}] Outside active hours (6am-6pm), sleeping...")
            time.sleep(CHECK_INTERVAL)
            continue

        # Find the latest DBD post
        latest_url = get_latest_dbd_url()

        if latest_url is None:
            print(f"[{timestamp()}] Failed to find latest DBD post")
            time.sleep(CHECK_INTERVAL)
            continue

        # Check if we switched to a new post
        if latest_url != current_url:
            if current_url is not None:
                print(f"[{timestamp()}] New DBD post detected!")
                send_notification(
                    "New DBD Post",
                    "New daily post available",
                    url=latest_url
                )
            current_url = latest_url
            # Extract post name for display
            post_name = re.search(r'/p/([^/]+)/?$', current_url)
            post_name = post_name.group(1) if post_name else current_url
            print(f"[{timestamp()}] Monitoring: {post_name}")
            # Reset count for new post
            save_state(current_url, 0)

        new_count = get_comment_count(current_url)

        if new_count is None:
            print(f"[{timestamp()}] Failed to fetch comment count")
            time.sleep(CHECK_INTERVAL)
            continue

        stored_url, old_count = read_state()

        # If URL changed in state, reset count
        if stored_url != current_url:
            old_count = 0

        if new_count > old_count:
            diff = new_count - old_count
            # Only notify if not the initial fetch
            if old_count > 0:
                send_notification(
                    "Substack Update",
                    f"{diff} new comment(s) on DBD (now {new_count} total)",
                    url=current_url
                )
            print(f"[{timestamp()}] NEW COMMENTS! {old_count} → {new_count} (+{diff})")
            save_state(current_url, new_count)
        else:
            print(f"[{timestamp()}] No new comments (count: {new_count})")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
