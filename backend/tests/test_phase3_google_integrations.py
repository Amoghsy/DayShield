"""Phase 3 tests: Google OAuth 2.0, Google Calendar read, Gmail draft creation, and API routes."""

from __future__ import annotations

from fastapi.testclient import TestClient
from google.oauth2.credentials import Credentials

from app.integrations.google_calendar import GoogleCalendarClient
from app.integrations.google_oauth import GOOGLE_SCOPES, oauth_manager
from app.integrations.gmail_client import GmailDraftClient
from app.main import app


def test_calendar_falls_back_to_labeled_sample_when_disconnected():
    """When OAuth is not connected, calendar returns clearly labeled sample data."""
    oauth_manager._credentials = None
    res = GoogleCalendarClient().get_today_events()
    assert res["data_source"] == "sample"
    assert res["oauth_connected"] is False
    assert len(res["events"]) >= 1


def test_calendar_reads_live_events_when_oauth_connected(monkeypatch):
    """When OAuth is connected, GoogleCalendarClient parses Google Calendar API events."""
    fake_creds = Credentials(token="fake-access-token")
    oauth_manager.set_credentials(fake_creds)

    class FakeEventsResource:
        def list(self, **kwargs):
            return self

        def execute(self):
            return {
                "items": [
                    {
                        "id": "gcal_evt_1",
                        "summary": "Thesis Defense",
                        "start": {"dateTime": "2026-11-26T09:00:00+05:30"},
                        "end": {"dateTime": "2026-11-26T10:00:00+05:30"},
                        "location": "Main Auditorium",
                        "attendees": [{"email": "examiner@university.edu"}],
                        "hangoutLink": "https://meet.google.com/abc-defg-hij",
                    }
                ]
            }

    class FakeCalendarService:
        def events(self):
            return FakeEventsResource()

    monkeypatch.setattr(
        "app.integrations.google_calendar.build",
        lambda *args, **kwargs: FakeCalendarService(),
    )

    try:
        res = GoogleCalendarClient().get_today_events()
        assert res["data_source"] == "live"
        assert res["oauth_connected"] is True
        assert res["events"][0]["event_id"] == "gcal_evt_1"
        assert res["events"][0]["can_join_online"] is True
    finally:
        oauth_manager._credentials = None


def test_gmail_draft_creation_only_never_sends(monkeypatch):
    """Verify GmailDraftClient creates a draft and never sends an email."""
    fake_creds = Credentials(token="fake-access-token")
    oauth_manager.set_credentials(fake_creds)

    class FakeDraftsResource:
        def create(self, userId, body):
            assert userId == "me"
            assert "raw" in body["message"]
            return self

        def execute(self):
            return {"id": "draft_xyz_123"}

    class FakeUsersResource:
        def drafts(self):
            return FakeDraftsResource()

    class FakeGmailService:
        def users(self):
            return FakeUsersResource()

    monkeypatch.setattr(
        "app.integrations.gmail_client.build",
        lambda *args, **kwargs: FakeGmailService(),
    )

    try:
        res = GmailDraftClient().create_draft(
            recipient="client@acmecorp.com",
            subject="Running 15 minutes late",
            body="Apologies, I am delayed by ~15 minutes.",
        )
        assert res["ok"] is True
        assert res["mode"] == "live"
        assert res["sent"] is False
        assert res["draft_id"] == "draft_xyz_123"
    finally:
        oauth_manager._credentials = None


def test_oauth_scopes_exclude_gmail_send():
    """Security check: gmail.send scope must NOT be requested."""
    assert all("gmail.send" not in s for s in GOOGLE_SCOPES)
    assert "https://www.googleapis.com/auth/gmail.compose" in GOOGLE_SCOPES


def test_calendar_and_integrations_endpoints():
    """Verify GET /api/calendar/today and GET /api/integrations/status."""
    oauth_manager._credentials = None
    client = TestClient(app)

    cal_resp = client.get("/api/calendar/today")
    assert cal_resp.status_code == 200
    assert cal_resp.json()["data_source"] == "sample"

    int_resp = client.get("/api/integrations/status")
    assert int_resp.status_code == 200
    data = int_resp.json()
    assert data["google_oauth"]["connected"] is False
    assert data["osrm"]["mode"] == "route_estimate_only"
