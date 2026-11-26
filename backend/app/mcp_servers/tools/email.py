"""Email MCP tool: draft creation ONLY (never sends emails)."""

from __future__ import annotations

from typing import Any


def create_email_draft(recipient: str, subject: str, body: str) -> dict[str, Any]:
    """Prepare a Gmail draft payload. Never sends an email automatically.

    In Phase 3, this delegates to the authenticated Gmail API drafts endpoint
    only after explicit user approval in the execution service.
    """
    return {
        "status": "draft_prepared",
        "sent": False,
        "recipient": recipient,
        "subject": subject,
        "body": body,
        "note": "Draft-only capability. Automatic email sending is disabled.",
    }
