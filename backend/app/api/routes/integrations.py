"""Integrations status and Google OAuth 2.0 routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.config import get_settings
from app.integrations.google_oauth import oauth_manager

router = APIRouter(prefix="/api/integrations", tags=["Integrations"])


@router.get("/status", summary="Check status of all external integrations")
async def get_integrations_status() -> dict:
    """Report configuration and connection status for Gemini, OSRM, Open-Meteo, and Google OAuth."""
    settings = get_settings()
    google_status = oauth_manager.status()
    return {
        "simulation_mode": settings.simulation_mode,
        "gemini": {
            "configured": bool(settings.gemini_api_key),
            "model": settings.gemini_model,
        },
        "osrm": {
            "available": True,
            "mode": "route_estimate_only",
            "note": "OSRM does not provide live traffic congestion.",
        },
        "open_meteo": {
            "available": True,
            "requires_key": False,
        },
        "google_oauth": google_status,
    }


@router.get("/google/login", summary="Get Google OAuth 2.0 authorization URL")
async def google_oauth_login() -> dict:
    """Return the Google OAuth consent URL for Calendar (read) and Gmail (drafts only)."""
    try:
        return oauth_manager.get_authorization_url()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/google/callback", summary="Handle Google OAuth 2.0 callback")
async def google_oauth_callback(
    code: str = Query(...),
    state: str | None = Query(default=None),
) -> dict:
    """Exchange OAuth authorization code for credentials."""
    try:
        return oauth_manager.exchange_code(code=code, state=state)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth callback failed: {exc}",
        ) from exc
