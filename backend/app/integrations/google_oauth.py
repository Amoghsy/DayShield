"""Google OAuth 2.0 credential management for DayShield.

Uses free Google Calendar & Gmail APIs (no billing account required).
Gmail scope is restricted to `gmail.compose` (draft creation only, never sending).
"""

from __future__ import annotations

import logging
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.config import get_settings

logger = logging.getLogger("dayshield.integrations.oauth")

# Read-only calendar + Gmail compose (drafts only)
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]


class GoogleOAuthManager:
    """Manages Google OAuth 2.0 flow and in-memory token state."""

    def __init__(self) -> None:
        self._credentials: Credentials | None = None
        self._state: str | None = None

    def is_configured(self) -> bool:
        """Return True if Google OAuth client ID and secret are set."""
        settings = get_settings()
        return bool(settings.google_client_id and settings.google_client_secret)

    def is_connected(self) -> bool:
        """Return True if valid (or refreshable) OAuth credentials are available."""
        if self._credentials is None:
            return False
        if self._credentials.valid:
            return True
        if self._credentials.expired and self._credentials.refresh_token:
            try:
                self._credentials.refresh(Request())
                return self._credentials.valid
            except Exception as exc:
                logger.warning("Failed to refresh Google OAuth token: %s", exc)
                return False
        return False

    def get_credentials(self) -> Credentials | None:
        """Return active Credentials if connected, else None."""
        return self._credentials if self.is_connected() else None

    def set_credentials(self, creds: Credentials) -> None:
        """Store Credentials (used by OAuth callback and tests)."""
        self._credentials = creds

    def _build_flow(self, state: str | None = None) -> Flow:
        settings = get_settings()
        client_config: dict[str, Any] = {
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.google_redirect_uri],
            }
        }
        return Flow.from_client_config(
            client_config=client_config,
            scopes=GOOGLE_SCOPES,
            state=state,
            redirect_uri=settings.google_redirect_uri,
        )

    def get_authorization_url(self) -> dict[str, str]:
        """Generate Google OAuth consent URL."""
        if not self.is_configured():
            raise ValueError(
                "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
            )
        flow = self._build_flow()
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        self._state = state
        return {"authorization_url": auth_url, "state": state}

    def exchange_code(self, code: str, state: str | None = None) -> dict[str, Any]:
        """Exchange authorization code for OAuth tokens."""
        if not self.is_configured():
            raise ValueError("Google OAuth is not configured.")
        flow = self._build_flow(state=state or self._state)
        flow.fetch_token(code=code)
        self._credentials = flow.credentials
        return {
            "connected": True,
            "scopes": list(self._credentials.scopes or GOOGLE_SCOPES),
        }

    def status(self) -> dict[str, Any]:
        """Return current OAuth configuration and connection status."""
        return {
            "configured": self.is_configured(),
            "connected": self.is_connected(),
            "scopes": GOOGLE_SCOPES,
        }


oauth_manager = GoogleOAuthManager()
