"""
DBD Browser Automation - Agentic Helper.

This module provides helper functions for Claude Code to execute
DBD post automation using semantic element finding rather than
hardcoded selectors.

The main automation logic is in dbd_automation.py. This module
provides utilities for common browser operations.
"""

from typing import Optional

# Re-export main classes for convenience
from .dbd_automation import (
    DBDPost,
    DBDAutomationAgent,
    create_dbd_post,
    build_post_content,
    SUBSTACK_PUBLISH_URL,
    SUBSTACK_NEW_POST_URL,
    DBD_LOGO_URL,
    DBD_WELCOME_TEXT,
)


# ============================================================================
# Semantic Element Descriptions
# ============================================================================
# These describe elements by their purpose, not their selectors.
# Claude Code should use these descriptions with the `find` tool.

ELEMENT_DESCRIPTIONS = {
    # Editor elements
    "title_input": "The post title input field at the top of the editor",
    "subtitle_input": "The subtitle/description input field below the title",
    "content_area": "The main content editing area (contenteditable)",
    "insert_menu_button": "The '+' or insert button in the editor gutter/toolbar",
    "slash_menu": "The slash command menu that appears when typing '/'",

    # Publish dialog elements
    "continue_button": "The 'Continue' or 'Publish' button in the editor header",
    "audience_everyone": "The 'Everyone' option in the audience selector",
    "audience_subscribers": "The 'Subscribers only' option",
    "schedule_toggle": "The toggle/checkbox for 'Schedule time to email and publish'",
    "datetime_input": "The date/time picker input for scheduling",
    "email_checkbox": "The 'Send via email' checkbox",
    "publish_button": "The final publish/schedule confirmation button",

    # Poll elements
    "poll_option": "Poll option in the insert/embed menu",
    "poll_question_input": "Input field for the poll question",
    "poll_option_input": "Input field for a poll answer option",
    "add_option_button": "Button to add another poll option",
    "poll_save_button": "Save/Done button for the poll",

    # Dialog elements
    "subscribe_dialog": "The 'Add subscribe buttons' dialog",
    "publish_without_buttons": "The 'Publish without buttons' button in subscribe dialog",
}


# ============================================================================
# Helper Functions for Browser Automation
# ============================================================================

def get_element_hint(element_name: str) -> str:
    """
    Get a semantic description for an element.

    Use this to help Claude Code find elements without hardcoded selectors.
    """
    return ELEMENT_DESCRIPTIONS.get(element_name, element_name)


def format_schedule_datetime(date_str: str, hour: int = 5, minute: int = 0) -> str:
    """Format a datetime string for the schedule input."""
    return f"{date_str}T{hour:02d}:{minute:02d}"


def get_draft_update_js(post_id: int, title: str, subtitle: str, content: dict) -> str:
    """
    Generate JavaScript to update a draft via API.

    This is more reliable than trying to manipulate the contenteditable editor.
    """
    import json
    return f"""(async () => {{
    const response = await fetch('/api/v1/drafts/{post_id}', {{
        method: 'PUT',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{
            draft_title: {json.dumps(title)},
            draft_subtitle: {json.dumps(subtitle)},
            draft_body: JSON.stringify({json.dumps(content)})
        }})
    }});
    return response.ok ? 'SUCCESS: Draft updated' : 'FAILED: ' + response.status;
}})();"""


def get_create_draft_js() -> str:
    """
    Generate JavaScript to create a new draft and return its ID.
    """
    return """(async () => {
    const response = await fetch('/api/v1/drafts', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            draft_title: 'New DBD Post',
            draft_subtitle: '',
            draft_body: JSON.stringify({"type": "doc", "content": [{"type": "paragraph"}]})
        })
    });
    if (response.ok) {
        const data = await response.json();
        return 'SUCCESS: Draft ID = ' + data.id;
    }
    return 'FAILED: ' + response.status;
})();"""


# ============================================================================
# Quick Reference for Claude Code
# ============================================================================

AUTOMATION_TIPS = """
TIPS FOR AGENTIC BROWSER AUTOMATION:

1. USE SEMANTIC FINDING
   Instead of: document.querySelector('#publish')
   Use: find tool with "Continue or Publish button in editor header"

2. VERIFY BEFORE CLICKING
   Take a screenshot or read the page to verify you're clicking the right thing.

3. WAIT FOR TRANSITIONS
   After clicking, wait for dialogs/menus to appear before proceeding.

4. HANDLE FAILURES GRACEFULLY
   If an element isn't found, try alternative approaches:
   - Look for similar text
   - Try keyboard shortcuts (e.g., Cmd+Enter to publish)
   - Check if element is in a different state

5. USE API WHEN POSSIBLE
   For content updates, the API is more reliable than the contenteditable editor.
   Use JavaScript execution to call /api/v1/drafts/{post_id}

6. POLL CREATION
   Polls must be added via the UI - no API support.
   - Click in content area where poll should go
   - Type '/' or click '+' to open insert menu
   - Select 'Poll' from options
   - Fill in question and options
"""


def print_tips():
    """Print automation tips for Claude Code."""
    print(AUTOMATION_TIPS)


if __name__ == "__main__":
    print_tips()
    print("\n" + "="*60 + "\n")
    print("Element Descriptions:")
    for name, desc in ELEMENT_DESCRIPTIONS.items():
        print(f"  {name}: {desc}")
