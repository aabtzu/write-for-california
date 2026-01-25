"""
DBD (Daily Bear Dump) Post Automation for Substack.

This module provides agentic automation for creating and scheduling DBD posts
on Substack. Instead of hardcoded selectors, it uses semantic descriptions
that Claude Code can interpret flexibly using browser automation.

Usage:
    from wfc.dbd_automation import DBDPost, DBDAutomationAgent

    # Create a post configuration
    post = DBDPost(
        date="2026-01-26",
        subject="Republic Day",
        subtitle="in India",
        lede_photo_url="https://example.com/photo.jpg"  # optional
    )

    # Get automation instructions for Claude Code
    agent = DBDAutomationAgent(post)
    agent.print_instructions()
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List

from .config import BASE_URL

# ============================================================================
# Configuration
# ============================================================================

SUBSTACK_PUBLISH_URL = f"{BASE_URL}/publish"
SUBSTACK_NEW_POST_URL = f"{BASE_URL}/publish/post"

# Google Sheets control document
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1AkWo5PuqnYj5fyl3IbeOSv3_zMgEI2lbmlPv-b79rvo/edit"
SPREADSHEET_ID = "1AkWo5PuqnYj5fyl3IbeOSv3_zMgEI2lbmlPv-b79rvo"

# DBD post template assets
DBD_LOGO_URL = "https://substack-post-media.s3.amazonaws.com/public/images/a239fbb2-15a3-4316-a9cb-214f8bda0edf_550x400.png"

DBD_WELCOME_TEXT = (
    "Welcome to the DBD, a Write for California community board where one can talk "
    "about anything – Cal-related or off-topic. Comment threads are sorted by topic. "
    "Anything is fine, so long as you're generally civil."
)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class DBDPost:
    """Configuration for a DBD post."""
    date: str  # YYYY-MM-DD format
    subject: str
    subtitle: str = ""
    lede_photo_url: Optional[str] = None
    poll_question: Optional[str] = None
    poll_options: List[str] = field(default_factory=list)
    schedule_hour: int = 5  # 5 AM default
    schedule_minute: int = 0
    send_email: bool = False
    post_id: Optional[int] = None

    @property
    def title(self) -> str:
        """Generate the post title."""
        dt = datetime.strptime(self.date, "%Y-%m-%d")
        formatted_date = dt.strftime("%m-%d-%Y")
        return f"DBD {formatted_date}: {self.subject}"

    @property
    def schedule_datetime(self) -> str:
        """Generate the schedule datetime string."""
        return f"{self.date}T{self.schedule_hour:02d}:{self.schedule_minute:02d}"

    @property
    def editor_url(self) -> str:
        """URL for the post editor."""
        if self.post_id:
            return f"{SUBSTACK_NEW_POST_URL}/{self.post_id}"
        return SUBSTACK_NEW_POST_URL


# ============================================================================
# Content Builder
# ============================================================================

def build_post_content(post: DBDPost) -> Dict[str, Any]:
    """
    Build the post content structure.

    Order:
    1. Title (handled via draft_title)
    2. DBD logo
    3. Intro/welcome text
    4. Lede photo (if provided)
    5. Poll (placeholder - must be added via UI)
    """
    content = []

    # DBD Logo
    content.append({
        "type": "captionedImage",
        "content": [{
            "type": "image2",
            "attrs": {
                "src": DBD_LOGO_URL,
                "height": 400,
                "width": 550,
                "resizeWidth": 72,
                "bytes": 5082,
                "type": "image/png",
                "belowTheFold": False,
                "topImage": False,
                "isProcessing": False
            }
        }]
    })

    # Welcome text
    content.append({
        "type": "paragraph",
        "content": [{"type": "text", "text": DBD_WELCOME_TEXT}]
    })

    # Lede photo (if provided)
    if post.lede_photo_url:
        content.append({
            "type": "captionedImage",
            "content": [{
                "type": "image2",
                "attrs": {
                    "src": post.lede_photo_url,
                    "belowTheFold": False,
                    "topImage": False,
                    "isProcessing": False
                }
            }]
        })

    # Empty paragraph (poll placeholder or end)
    content.append({"type": "paragraph"})

    return {"type": "doc", "content": content}


# ============================================================================
# Agentic Automation Instructions
# ============================================================================

@dataclass
class AutomationStep:
    """A single automation step with semantic description."""
    name: str
    description: str
    action_type: str  # 'navigate', 'click', 'type', 'javascript', 'find', 'verify'
    target: Optional[str] = None  # Semantic description of target element
    value: Optional[str] = None  # Value for input/type actions
    fallback: Optional[str] = None  # What to do if step fails
    wait_for: Optional[str] = None  # What to wait for after action
    optional: bool = False  # Whether step can be skipped


class DBDAutomationAgent:
    """
    Agentic automation for DBD posts.

    Instead of hardcoded selectors, this provides semantic descriptions
    that Claude Code can interpret using its browser automation capabilities.
    """

    def __init__(self, post: DBDPost):
        self.post = post

    def get_steps(self) -> List[AutomationStep]:
        """Get all automation steps for the post."""
        steps = []

        # Phase 1: Navigate and set up content
        steps.extend(self._content_steps())

        # Phase 2: Add poll if specified
        if self.post.poll_question:
            steps.extend(self._poll_steps())

        # Phase 3: Schedule the post
        steps.extend(self._scheduling_steps())

        return steps

    def _content_steps(self) -> List[AutomationStep]:
        """Steps to set up post content."""
        steps = [
            AutomationStep(
                name="navigate_to_editor",
                description=f"Navigate to the post editor",
                action_type="navigate",
                target=self.post.editor_url,
                wait_for="Editor loaded - title input visible"
            ),
            AutomationStep(
                name="update_via_api",
                description="Update post content via Substack API",
                action_type="javascript",
                value=self._generate_update_script(),
                wait_for="API returns SUCCESS",
                fallback="If API fails, manually set title and content"
            ),
            AutomationStep(
                name="refresh_editor",
                description="Refresh to see updated content",
                action_type="navigate",
                target=self.post.editor_url,
                wait_for="Content visible in editor"
            ),
        ]
        return steps

    def _poll_steps(self) -> List[AutomationStep]:
        """Steps to add a poll."""
        steps = [
            AutomationStep(
                name="position_cursor",
                description="Click at the end of the post content, after the lede photo",
                action_type="click",
                target="Empty paragraph at end of post content",
                wait_for="Cursor positioned in editor"
            ),
            AutomationStep(
                name="open_insert_menu",
                description="Open the insert menu to add a poll",
                action_type="find",
                target="Plus button or insert menu in editor toolbar, or type '/' to open slash menu",
                fallback="Look for a '+' icon in the editor gutter or toolbar"
            ),
            AutomationStep(
                name="select_poll",
                description="Select 'Poll' from the insert menu",
                action_type="click",
                target="Poll option in the insert/embed menu",
                wait_for="Poll creation dialog or inline poll editor appears"
            ),
            AutomationStep(
                name="enter_poll_question",
                description=f"Enter the poll question: {self.post.poll_question}",
                action_type="type",
                target="Poll question input field",
                value=self.post.poll_question,
            ),
        ]

        # Add steps for each poll option
        for i, option in enumerate(self.post.poll_options):
            steps.append(AutomationStep(
                name=f"enter_poll_option_{i+1}",
                description=f"Enter poll option {i+1}: {option}",
                action_type="type",
                target=f"Poll option {i+1} input field",
                value=option,
            ))

        steps.append(AutomationStep(
            name="save_poll",
            description="Save/confirm the poll",
            action_type="click",
            target="Save, Done, or confirm button for the poll",
            wait_for="Poll appears in post content",
            optional=True  # Some UIs auto-save
        ))

        return steps

    def _scheduling_steps(self) -> List[AutomationStep]:
        """Steps to schedule the post."""
        steps = [
            AutomationStep(
                name="open_publish_dialog",
                description="Open the publish/schedule dialog",
                action_type="click",
                target="'Continue' or 'Publish' button (usually top-right of editor)",
                wait_for="Publish dialog opens with audience and scheduling options"
            ),
            AutomationStep(
                name="select_audience",
                description="Select 'Everyone' as the audience",
                action_type="click",
                target="'Everyone' radio button or option in audience selector",
                wait_for="'Everyone' is selected"
            ),
            AutomationStep(
                name="enable_scheduling",
                description="Enable the scheduling option",
                action_type="click",
                target="'Schedule' toggle or checkbox - look for 'Schedule time to email and publish'",
                wait_for="Date/time picker becomes visible"
            ),
            AutomationStep(
                name="set_schedule_time",
                description=f"Set schedule to {self.post.schedule_datetime}",
                action_type="type",
                target="datetime-local input or date/time picker",
                value=self.post.schedule_datetime,
                wait_for="Time is set correctly"
            ),
        ]

        if not self.post.send_email:
            steps.append(AutomationStep(
                name="disable_email",
                description="Disable email notification",
                action_type="click",
                target="'Send via email' checkbox - uncheck if checked",
                wait_for="Email option is unchecked",
                optional=True  # May already be unchecked
            ))

        steps.extend([
            AutomationStep(
                name="confirm_schedule",
                description="Confirm and schedule the post",
                action_type="click",
                target="'Schedule' or 'Send to everyone' button",
                wait_for="Confirmation that post is scheduled"
            ),
            AutomationStep(
                name="handle_subscribe_dialog",
                description="Dismiss 'Add subscribe buttons' dialog if it appears",
                action_type="click",
                target="'Publish without buttons' or 'Skip' button",
                wait_for="Dialog dismissed",
                optional=True  # Dialog may not appear
            ),
        ])

        return steps

    def _generate_update_script(self) -> str:
        """Generate JavaScript to update post via API."""
        content = build_post_content(self.post)

        if self.post.post_id:
            return f"""(async () => {{
    const response = await fetch('/api/v1/drafts/{self.post.post_id}', {{
        method: 'PUT',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{
            draft_title: {json.dumps(self.post.title)},
            draft_subtitle: {json.dumps(self.post.subtitle)},
            draft_body: JSON.stringify({json.dumps(content)})
        }})
    }});
    return response.ok ? 'SUCCESS' : 'FAILED: ' + response.status;
}})();"""
        else:
            return "// Need post_id to update via API - create draft first"

    def print_instructions(self):
        """Print human-readable instructions for Claude Code."""
        print(f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                         DBD Post Automation                              ║
╠══════════════════════════════════════════════════════════════════════════╣
║ Title:    {self.post.title:<62} ║
║ Subtitle: {self.post.subtitle:<62} ║
║ Schedule: {self.post.schedule_datetime:<62} ║
║ Post ID:  {str(self.post.post_id or 'NEW'):<62} ║
╚══════════════════════════════════════════════════════════════════════════╝

INSTRUCTIONS FOR CLAUDE CODE:

Use browser automation (mcp__Claude_in_Chrome tools) to complete these steps.
Use semantic element finding - don't rely on exact selectors.
""")

        for i, step in enumerate(self.get_steps(), 1):
            optional = " (OPTIONAL)" if step.optional else ""
            print(f"\n{'─'*74}")
            print(f"STEP {i}: {step.name.upper()}{optional}")
            print(f"{'─'*74}")
            print(f"Action: {step.action_type}")
            print(f"Description: {step.description}")

            if step.target:
                print(f"Target: {step.target}")
            if step.value and step.action_type != 'javascript':
                print(f"Value: {step.value}")
            if step.wait_for:
                print(f"Wait for: {step.wait_for}")
            if step.fallback:
                print(f"Fallback: {step.fallback}")

            if step.action_type == 'javascript' and step.value:
                print(f"\nJavaScript:\n{step.value}")

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary."""
        return {
            "post": {
                "date": self.post.date,
                "subject": self.post.subject,
                "subtitle": self.post.subtitle,
                "title": self.post.title,
                "lede_photo_url": self.post.lede_photo_url,
                "poll_question": self.post.poll_question,
                "poll_options": self.post.poll_options,
                "schedule_datetime": self.post.schedule_datetime,
                "send_email": self.post.send_email,
                "post_id": self.post.post_id,
                "editor_url": self.post.editor_url,
            },
            "steps": [
                {
                    "name": s.name,
                    "description": s.description,
                    "action_type": s.action_type,
                    "target": s.target,
                    "value": s.value if s.action_type != 'javascript' else "[script]",
                    "optional": s.optional,
                }
                for s in self.get_steps()
            ]
        }


# ============================================================================
# Poll API JavaScript Generator
# ============================================================================

def generate_poll_script(
    post_id: int,
    poll_question: str,
    poll_options: List[str],
    poll_expiry_hours: int = 24
) -> str:
    """
    Generate JavaScript to create a poll and add it to a post via Substack API.

    This script can be run in the browser console on the Substack editor page.

    Args:
        post_id: The draft post ID
        poll_question: The poll question text
        poll_options: List of poll option labels
        poll_expiry_hours: Hours until poll closes (default 24)

    Returns:
        JavaScript code as string to run in browser console
    """
    options_json = json.dumps([{"label": opt} for opt in poll_options])

    return f"""(async () => {{
    // Step 1: Create the poll
    console.log('Creating poll...');
    const pollResponse = await fetch('/api/v1/poll', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{
            question: {json.dumps(poll_question)},
            options: {options_json},
            expiry: {poll_expiry_hours},
            audience: "all_subscribers",
            votes_hidden: false
        }})
    }});

    if (!pollResponse.ok) {{
        console.error('Failed to create poll:', pollResponse.status);
        return 'FAILED: Could not create poll';
    }}

    const pollData = await pollResponse.json();
    console.log('Poll created with ID:', pollData.id);

    // Step 2: Get current draft body
    console.log('Fetching current draft...');
    const draftResponse = await fetch('/api/v1/drafts/{post_id}');
    if (!draftResponse.ok) {{
        console.error('Failed to fetch draft:', draftResponse.status);
        return 'FAILED: Could not fetch draft';
    }}

    const draftData = await draftResponse.json();
    const body = JSON.parse(draftData.draft_body);

    // Step 3: Insert poll before subscribeWidget (or at end)
    const subscribeIndex = body.content.findIndex(n => n.type === 'subscribeWidget');
    const pollNode = {{type: "poll", attrs: {{id: pollData.id}}}};

    if (subscribeIndex >= 0) {{
        body.content.splice(subscribeIndex, 0, pollNode);
    }} else {{
        body.content.push(pollNode);
    }}

    // Step 4: Update draft with new body
    console.log('Updating draft with poll...');
    const updateResponse = await fetch('/api/v1/drafts/{post_id}', {{
        method: 'PUT',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{
            draft_body: JSON.stringify(body)
        }})
    }});

    if (updateResponse.ok) {{
        console.log('SUCCESS! Poll added. Refresh the page to see it.');
        return 'SUCCESS: Poll ID ' + pollData.id + ' added to post';
    }} else {{
        console.error('Failed to update draft:', updateResponse.status);
        return 'FAILED: Could not update draft';
    }}
}})();"""


def print_poll_script(
    post_id: int,
    poll_question: str,
    poll_options: List[str],
    poll_expiry_hours: int = 24
):
    """Print the poll creation script with instructions."""
    script = generate_poll_script(post_id, poll_question, poll_options, poll_expiry_hours)

    print(f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                    Poll Creation Script for Substack                     ║
╠══════════════════════════════════════════════════════════════════════════╣
║ Post ID:  {post_id:<64} ║
║ Question: {poll_question:<64} ║
║ Options:  {', '.join(poll_options):<64} ║
║ Expiry:   {poll_expiry_hours} hours{' ':<57} ║
╚══════════════════════════════════════════════════════════════════════════╝

INSTRUCTIONS:
1. Open the post editor in Chrome: https://writeforcalifornia.com/publish/post/{post_id}
2. Open browser console (Cmd+Option+J on Mac, Ctrl+Shift+J on Windows)
3. Paste and run the following script:

{'─'*76}
{script}
{'─'*76}

4. Refresh the page to see the poll in the editor
""")


# ============================================================================
# Convenience Functions
# ============================================================================

def create_dbd_post(
    date: str,
    subject: str,
    subtitle: str = "",
    post_id: Optional[int] = None,
    lede_photo_url: Optional[str] = None,
    poll_question: Optional[str] = None,
    poll_options: Optional[List[str]] = None,
) -> DBDAutomationAgent:
    """
    Create a DBD post automation agent.

    Args:
        date: Date in YYYY-MM-DD format
        subject: Subject/theme for the post
        subtitle: Subtitle for the post
        post_id: Existing draft post ID (optional)
        lede_photo_url: URL for lede photo (optional)
        poll_question: Poll question (optional)
        poll_options: List of poll options (optional)

    Returns:
        DBDAutomationAgent configured for the post
    """
    post = DBDPost(
        date=date,
        subject=subject,
        subtitle=subtitle,
        post_id=post_id,
        lede_photo_url=lede_photo_url,
        poll_question=poll_question,
        poll_options=poll_options or [],
    )
    return DBDAutomationAgent(post)


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    """CLI entry point for DBD automation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Create and schedule DBD posts on Substack"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Main post automation command
    post_parser = subparsers.add_parser("post", help="Generate post automation instructions")
    post_parser.add_argument("--date", required=True, help="Date (YYYY-MM-DD)")
    post_parser.add_argument("--subject", required=True, help="Post subject")
    post_parser.add_argument("--subtitle", default="", help="Post subtitle")
    post_parser.add_argument("--post-id", type=int, help="Existing draft post ID")
    post_parser.add_argument("--lede-photo", help="URL for lede photo")
    post_parser.add_argument("--poll-question", help="Poll question")
    post_parser.add_argument("--poll-option", action="append", dest="poll_options",
                             help="Poll option (can specify multiple)")
    post_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Poll script command
    poll_parser = subparsers.add_parser("poll", help="Generate poll creation script")
    poll_parser.add_argument("--post-id", type=int, required=True, help="Draft post ID")
    poll_parser.add_argument("--question", required=True, help="Poll question")
    poll_parser.add_argument("--option", action="append", dest="options", required=True,
                             help="Poll option (can specify multiple, min 2)")
    poll_parser.add_argument("--expiry", type=int, default=24,
                             help="Hours until poll closes (default: 24)")
    poll_parser.add_argument("--script-only", action="store_true",
                             help="Output only the JavaScript (no instructions)")

    args = parser.parse_args()

    if args.command == "poll":
        if len(args.options) < 2:
            parser.error("At least 2 poll options required")
        if args.script_only:
            print(generate_poll_script(args.post_id, args.question, args.options, args.expiry))
        else:
            print_poll_script(args.post_id, args.question, args.options, args.expiry)

    elif args.command == "post":
        agent = create_dbd_post(
            date=args.date,
            subject=args.subject,
            subtitle=args.subtitle,
            post_id=args.post_id,
            lede_photo_url=args.lede_photo,
            poll_question=args.poll_question,
            poll_options=args.poll_options,
        )

        if args.json:
            print(json.dumps(agent.to_dict(), indent=2))
        else:
            agent.print_instructions()

    else:
        # Default: show help
        parser.print_help()


if __name__ == "__main__":
    main()
