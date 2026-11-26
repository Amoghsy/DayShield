"""Calendar API routes (read-only)."""

from __future__ import annotations

from fastapi import APIRouter

from app.integrations.google_calendar import GoogleCalendarClient

router = APIRouter(prefix="/api/calendar", tags=["Calendar"])


@router.get("/today", summary="Get today's calendar events (OAuth or labeled sample)")
async def get_today_calendar(scenario: str = "scenario_a") -> dict:
    """Return today's calendar events via Google Calendar API or clearly labeled sample data."""
    client = GoogleCalendarClient()
    return client.get_today_events(scenario=scenario)
