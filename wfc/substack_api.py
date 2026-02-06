"""
Substack API client for DBD post automation.

This module provides direct API access to Substack using a session cookie,
bypassing the need for browser automation for DRAFT CREATION.

IMPORTANT LIMITATION: Substack's API does not support scheduling posts for
future publication. The schedule_post() method will publish immediately.
To schedule posts, use the Substack web UI or an external scheduler (cron)
to call publish_post() at the desired time.

Usage:
    from wfc.substack_api import SubstackClient

    client = SubstackClient()  # Uses cookie from ~/.wfc/substack_cookie.txt

    # Create a DBD draft (ready for manual scheduling in Substack UI)
    post_id = client.create_dbd_post(
        date="2026-02-02",
        subject="test",
        subtitle="foo",
        lede_photo_url="https://example.com/photo.jpg"
    )
    # Then open https://writeforcalifornia.com/publish/post/{post_id}
    # to schedule via the UI
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

import requests

from .config import STATE_DIR, get_environment, get_site_config
from .dbd_automation import (
    DBD_LOGO_URL,
    DBD_WELCOME_TEXT,
    build_post_content,
    DBDPost
)


def get_cookie_file() -> Path:
    """Get the cookie file for the current environment."""
    env = get_environment()
    if env == "prod":
        return STATE_DIR / "substack_cookie.txt"
    return STATE_DIR / f"substack_cookie_{env}.txt"


class SubstackAPIError(Exception):
    """Raised when a Substack API call fails."""
    pass


class SubstackClient:
    """
    Substack API client using session cookie authentication.

    The session cookie (connect.sid) is loaded from:
    - ~/.wfc/substack_cookie.txt (prod)
    - ~/.wfc/substack_cookie_test.txt (test)

    Set environment with: WFC_ENV=test or `wfc env test`
    """

    def __init__(self, cookie: Optional[str] = None):
        """
        Initialize the client.

        Args:
            cookie: Substack session cookie. If not provided, reads from cookie file.
        """
        site_config = get_site_config()
        self.env = get_environment()
        self.base_url = site_config["base_url"]
        self.site_name = site_config["name"]
        self.api_base = f"{self.base_url}/api/v1"

        if cookie:
            self.cookie = cookie
        else:
            self.cookie = self._load_cookie()

        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Cookie": f"connect.sid={self.cookie}",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })

        print(f"[{self.env.upper()}] Using {self.site_name} ({self.base_url})")

    def _load_cookie(self) -> str:
        """Load cookie from file."""
        cookie_file = get_cookie_file()
        if not cookie_file.exists():
            raise SubstackAPIError(
                f"Cookie file not found: {cookie_file}\n"
                f"Please save your connect.sid cookie value to this file.\n"
                "You can find it in Chrome DevTools > Application > Cookies"
            )
        return cookie_file.read_text().strip()

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an API request."""
        url = f"{self.api_base}/{endpoint}"
        response = self.session.request(method, url, **kwargs)

        if not response.ok:
            raise SubstackAPIError(
                f"API request failed: {method} {endpoint}\n"
                f"Status: {response.status_code}\n"
                f"Response: {response.text[:500]}"
            )

        return response.json() if response.text else {}

    def create_draft(
        self,
        title: str,
        subtitle: str = "",
        body: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Create a new draft post.

        Args:
            title: Post title
            subtitle: Post subtitle
            body: Post body content (Substack doc format)

        Returns:
            Draft post ID
        """
        payload = {
            "draft_title": title,
            "draft_subtitle": subtitle,
            "type": "newsletter",
            "draft_body": json.dumps(body) if body else json.dumps({"type": "doc", "content": [{"type": "paragraph"}]}),
            "draft_bylines": []  # Required field
        }

        # Use the drafts API endpoint
        response = self.session.post(
            f"{self.api_base}/drafts",
            json=payload
        )

        if response.ok:
            data = response.json()
            return data.get("id")

        raise SubstackAPIError(f"Failed to create draft: {response.status_code} - {response.text[:200]}")

    def update_draft(
        self,
        post_id: int,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update an existing draft.

        Args:
            post_id: Draft post ID
            title: New title (optional)
            subtitle: New subtitle (optional)
            body: New body content (optional)

        Returns:
            Updated draft data
        """
        payload = {}

        if title is not None:
            payload["draft_title"] = title
        if subtitle is not None:
            payload["draft_subtitle"] = subtitle
        if body is not None:
            payload["draft_body"] = json.dumps(body)

        return self._request("PUT", f"drafts/{post_id}", json=payload)

    def get_draft(self, post_id: int) -> Dict[str, Any]:
        """Get draft data."""
        return self._request("GET", f"drafts/{post_id}")

    def configure_draft(
        self,
        post_id: int,
        audience: str = "everyone",
        send_email: bool = False
    ) -> Dict[str, Any]:
        """
        Configure draft settings (audience, email, comments).

        Args:
            post_id: Draft post ID
            audience: "everyone", "only_paid", or "only_free"
            send_email: Whether to send email when published

        Returns:
            Updated draft data
        """
        payload = {
            "audience": audience,
            "write_comment_permissions": audience,
            "should_send_email": send_email,
        }
        return self._request("PUT", f"drafts/{post_id}", json=payload)

    def publish_post(
        self,
        post_id: int,
        audience: str = "everyone",
        send_email: bool = False
    ) -> Dict[str, Any]:
        """
        Publish a post immediately.

        Args:
            post_id: Draft post ID
            audience: "everyone", "only_paid", or "only_free"
            send_email: Whether to send email notification

        Returns:
            Response data
        """
        payload = {
            "post_id": post_id,
            "audience": audience,
            "send_email": send_email,
        }

        return self._request("POST", "drafts/publish", json=payload)

    def create_dbd_post(
        self,
        date: str,
        subject: str,
        subtitle: str = "",
        lede_photo_url: Optional[str] = None,
        audience: str = "everyone",
        send_email: bool = False
    ) -> int:
        """
        Create a complete DBD post draft with standard template.

        The draft will be configured with the specified settings and ready
        for scheduling via the Substack UI or immediate publishing.

        NOTE: Substack API does not support scheduling. To schedule:
        1. Open https://writeforcalifornia.com/publish/post/{post_id}
        2. Click "Continue" then use the schedule option

        Args:
            date: Post date in YYYY-MM-DD format
            subject: Subject/theme for the post
            subtitle: Post subtitle
            lede_photo_url: Optional URL for lede photo
            audience: "everyone", "only_paid", or "only_free"
            send_email: Whether to send email when published (default False)

        Returns:
            Post ID
        """
        # Build post config
        post = DBDPost(
            date=date,
            subject=subject,
            subtitle=subtitle,
            lede_photo_url=lede_photo_url,
            schedule_hour=5,  # Not used for API, just for DBDPost
            send_email=send_email
        )

        # Build content
        content = build_post_content(post)

        # Create draft
        print(f"Creating draft: {post.title}")
        post_id = self.create_draft(
            title=post.title,
            subtitle=post.subtitle,
            body=content
        )
        print(f"Created draft with ID: {post_id}")

        # Configure draft settings
        print(f"Configuring: audience={audience}, send_email={send_email}")
        self.configure_draft(
            post_id=post_id,
            audience=audience,
            send_email=send_email
        )

        print(f"\nDraft ready! Open to schedule or publish:")
        print(f"  {self.base_url}/publish/post/{post_id}")

        return post_id


def main():
    """CLI entry point."""
    import argparse
    from .config import set_environment, SITES

    parser = argparse.ArgumentParser(description="Substack API client for DBD posts")
    subparsers = parser.add_subparsers(dest="command")

    # Environment management
    env_parser = subparsers.add_parser("env", help="Show or set environment (prod/test)")
    env_parser.add_argument("target", nargs="?", choices=list(SITES.keys()), help="Environment to switch to")

    # Create DBD post
    create_parser = subparsers.add_parser("create", help="Create a DBD post draft")
    create_parser.add_argument("--date", required=True, help="Date (YYYY-MM-DD)")
    create_parser.add_argument("--subject", required=True, help="Subject")
    create_parser.add_argument("--subtitle", default="", help="Subtitle")
    create_parser.add_argument("--lede-photo", help="Lede photo URL")
    create_parser.add_argument("--audience", default="everyone", choices=["everyone", "only_paid", "only_free"], help="Post audience")
    create_parser.add_argument("--send-email", action="store_true", help="Send email when published")

    # Update existing post
    update_parser = subparsers.add_parser("update", help="Update an existing post")
    update_parser.add_argument("--post-id", type=int, required=True, help="Post ID")
    update_parser.add_argument("--title", help="New title")
    update_parser.add_argument("--subtitle", help="New subtitle")

    # Set cookie
    cookie_parser = subparsers.add_parser("set-cookie", help="Save Substack cookie for current environment")
    cookie_parser.add_argument("cookie", help="connect.sid cookie value")

    args = parser.parse_args()

    if args.command == "env":
        if args.target:
            set_environment(args.target)
            site = SITES[args.target]
            print(f"Switched to {args.target.upper()}: {site['name']} ({site['base_url']})")
        else:
            env = get_environment()
            print(f"Current environment: {env.upper()}")
            for name, site in SITES.items():
                marker = " <-- active" if name == env else ""
                print(f"  {name}: {site['base_url']}{marker}")
        return

    if args.command == "set-cookie":
        cookie_file = get_cookie_file()
        cookie_file.write_text(args.cookie)
        print(f"Cookie saved to {cookie_file}")
        return

    if args.command == "create":
        client = SubstackClient()
        post_id = client.create_dbd_post(
            date=args.date,
            subject=args.subject,
            subtitle=args.subtitle,
            lede_photo_url=args.lede_photo,
            audience=args.audience,
            send_email=args.send_email
        )

    elif args.command == "update":
        client = SubstackClient()
        client.update_draft(
            post_id=args.post_id,
            title=args.title,
            subtitle=args.subtitle
        )
        print(f"Updated post {args.post_id}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
