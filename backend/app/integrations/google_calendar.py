"""Google Calendar API client (read-only for agents; write reserved for approved executor)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from googleapiclient.discovery import build

from app.config import get_settings
from app.integrations.google_oauth import oauth_manager

logger = logging.getLogger("dayshield.integrations.calendar")


def _sample_today_events(scenario: str = "scenario_a") -> dict[str, Any]:
    """Return clearly labeled sample calendar data when Google OAuth is unavailable."""
    if scenario == "scenario_b":
        events = [
            {
                "event_id": "sample_evt_201",
                "title": "Internal Sprint Sync",
                "start_time": "09:00",
                "end_time": "09:45",
                "location": "Room 302 / Google Meet",
                "attendees": ["teammate1@example.com", "teammate2@example.com"],
                "has_external_attendees": False,
                "is_online": False,
                "can_join_online": True,
                "event_category": "internal_meeting",
            },
            {
                "event_id": "sample_evt_202",
                "title": "Gym & Errands",
                "start_time": "17:00",
                "end_time": "18:00",
                "location": "Local Gym",
                "attendees": [],
                "has_external_attendees": False,
                "is_online": False,
                "can_join_online": False,
                "event_category": "personal_task",
            },
        ]
    else:
        events = [
            {
                "event_id": "sample_evt_101",
                "title": "Client Project Review",
                "start_time": "09:00",
                "end_time": "10:00",
                "location": "MSRIT Innovation Lab",
                "attendees": ["client.lead@acmecorp.com", "mentor@msrit.edu"],
                "has_external_attendees": True,
                "is_online": False,
                "can_join_online": True,
                "event_category": "client_meeting",
            },
            {
                "event_id": "sample_evt_102",
                "title": "Internal Standup",
                "start_time": "10:30",
                "end_time": "11:00",
                "location": "Online",
                "attendees": ["team@dayshield.local"],
                "has_external_attendees": False,
                "is_online": True,
                "can_join_online": True,
                "event_category": "internal_meeting",
            },
        ]

    return {
        "data_source": "sample",
        "oauth_connected": False,
        "events": events,
        "free_slots": [
            {"start_time": "11:00", "end_time": "12:30", "duration_minutes": 90},
            {"start_time": "14:00", "end_time": "15:30", "duration_minutes": 90},
        ],
    }


class GoogleCalendarClient:
    """Wrapper around Google Calendar API v3 with safe sample fallback."""

    def get_today_events(self, scenario: str = "scenario_a") -> dict[str, Any]:
        """Fetch today's events from Google Calendar if connected, else sample data."""
        creds = oauth_manager.get_credentials()
        if creds is None:
            return _sample_today_events(scenario=scenario)

        try:
            service = build("calendar", "v3", credentials=creds, cache_discovery=False)
            now_utc = datetime.now(timezone.utc)
            start_of_day = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)

            result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=start_of_day.isoformat(),
                    timeMax=end_of_day.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            items = result.get("items", [])
            events = []
            for item in items:
                start_raw = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date", "")
                end_raw = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date", "")
                attendees = [
                    a.get("email", "")
                    for a in item.get("attendees", [])
                    if a.get("email") and not a.get("self", False)
                ]
                has_hangout = bool(item.get("hangoutLink") or item.get("conferenceData"))
                events.append(
                    {
                        "event_id": item.get("id", ""),
                        "title": item.get("summary", "Untitled Event"),
                        "start_time": start_raw,
                        "end_time": end_raw,
                        "location": item.get("location", ""),
                        "attendees": attendees,
                        "has_external_attendees": len(attendees) > 0,
                        "is_online": has_hangout and not bool(item.get("location")),
                        "can_join_online": has_hangout,
                        "event_category": "other",
                    }
                )

            return {
                "data_source": "live",
                "oauth_connected": True,
                "timezone": get_settings().user_timezone,
                "events": events,
                "free_slots": [],
            }
        except Exception as exc:
            logger.warning("Google Calendar API call failed, falling back to sample: %s", exc)
            fallback = _sample_today_events(scenario=scenario)
            fallback["calendar_error"] = str(exc)
            return fallback

    def reschedule_event(
        self,
        event_id: str,
        new_start_iso: str,
        new_end_iso: str,
    ) -> dict[str, Any]:
        """Update event start/end time. ONLY called by approval-controlled executor."""
        creds = oauth_manager.get_credentials()
        if creds is None:
            return {
                "ok": True,
                "mode": "simulated",
                "event_id": event_id,
                "new_start": new_start_iso,
                "new_end": new_end_iso,
                "note": "Google OAuth not connected; simulated reschedule recorded.",
            }

        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        updated = (
            service.events()
            .patch(
                calendarId="primary",
                eventId=event_id,
                body={
                    "start": {"dateTime": new_start_iso},
                    "end": {"dateTime": new_end_iso},
                },
            )
            .execute()
        )
        return {
            "ok": True,
            "mode": "live",
            "event_id": updated.get("id", event_id),
            "html_link": updated.get("htmlLink"),
        }
