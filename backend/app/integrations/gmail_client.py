"""Gmail API client: DRAFT CREATION ONLY (automatic sending is prohibited)."""

from __future__ import annotations

import base64
import logging
from email.message import EmailMessage
from typing import Any

from googleapiclient.discovery import build

from app.integrations.google_oauth import oauth_manager

logger = logging.getLogger("dayshield.integrations.gmail")


class GmailDraftClient:
    """Creates Gmail drafts via Gmail API v3. Never sends emails."""

    def create_draft(self, recipient: str, subject: str, body: str) -> dict[str, Any]:
        """Create a Gmail draft (or simulated draft if OAuth is not connected)."""
        creds = oauth_manager.get_credentials()
        if creds is None:
            return {
                "ok": True,
                "mode": "simulated",
                "sent": False,
                "draft_id": "sim_draft_001",
                "recipient": recipient,
                "subject": subject,
                "note": "Google OAuth not connected; simulated draft created (never sent).",
            }

        message = EmailMessage()
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        draft = (
            service.users()
            .drafts()
            .create(userId="me", body={"message": {"raw": encoded}})
            .execute()
        )
        return {
            "ok": True,
            "mode": "live",
            "sent": False,
            "draft_id": draft.get("id"),
            "recipient": recipient,
            "subject": subject,
        }
