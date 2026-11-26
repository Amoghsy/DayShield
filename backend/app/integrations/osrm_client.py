"""OSRM routing client using OpenStreetMap / OSRM public API.

Important: OSRM provides route geometry and estimated travel duration only.
It does NOT provide live traffic congestion data.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("dayshield.integrations.osrm")

OSRM_BASE_URL = "https://router.project-osrm.org"


class OSRMClient:
    """Async client for OSRM route and duration estimation."""

    def __init__(self, base_url: str = OSRM_BASE_URL, timeout: float = 8.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def get_routes(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        alternatives: bool = True,
    ) -> dict[str, Any]:
        """Fetch primary and optional alternative routes from OSRM.

        Returns a dict with `routes`, `data_source="estimated"`, and `disclaimer`.
        On network/HTTP error, returns `ok=False` and `error` details.
        """
        coords = f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
        url = f"{self.base_url}/route/v1/driving/{coords}"
        params = {
            "alternatives": "true" if alternatives else "false",
            "overview": "false",
            "steps": "false",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

            if data.get("code") != "Ok" or not data.get("routes"):
                return {
                    "ok": False,
                    "data_source": "estimated",
                    "error": f"OSRM returned no routes (code={data.get('code')})",
                    "routes": [],
                }

            parsed_routes = []
            for idx, route in enumerate(data["routes"]):
                duration_min = max(1, round(route["duration"] / 60))
                distance_km = round(route["distance"] / 1000, 2)
                parsed_routes.append(
                    {
                        "route_id": f"osrm_route_{idx + 1}",
                        "duration_minutes": duration_min,
                        "distance_km": distance_km,
                        "is_primary": idx == 0,
                    }
                )

            return {
                "ok": True,
                "data_source": "estimated",
                "disclaimer": (
                    "OSRM provides route-estimate duration based on road geometry and "
                    "speed limits, NOT live traffic congestion."
                ),
                "primary_route": parsed_routes[0],
                "routes": parsed_routes,
            }
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning("OSRM request failed: %s", exc)
            return {
                "ok": False,
                "data_source": "estimated",
                "error": f"OSRM service unavailable: {exc}",
                "routes": [],
            }
