"""Routing MCP tools backed by OSRM (route-estimate data, not live traffic)."""

from __future__ import annotations

from typing import Any

from app.integrations.osrm_client import OSRMClient

_osrm = OSRMClient()


async def get_route(origin: str, destination: str) -> dict[str, Any]:
    """Get the primary OSRM driving route between 'lat,lon' origin and destination."""
    o_lat, o_lon = (float(x.strip()) for x in origin.split(","))
    d_lat, d_lon = (float(x.strip()) for x in destination.split(","))
    result = await _osrm.get_routes(o_lat, o_lon, d_lat, d_lon, alternatives=False)
    return result


async def get_alternative_routes(origin: str, destination: str) -> dict[str, Any]:
    """Get primary and alternative OSRM driving routes between 'lat,lon' coordinates."""
    o_lat, o_lon = (float(x.strip()) for x in origin.split(","))
    d_lat, d_lon = (float(x.strip()) for x in destination.split(","))
    return await _osrm.get_routes(o_lat, o_lon, d_lat, d_lon, alternatives=True)


def calculate_route_duration(route: dict[str, Any]) -> dict[str, Any]:
    """Extract and label estimated duration from an OSRM route object."""
    duration = int(route.get("duration_minutes", 0))
    return {
        "route_id": route.get("route_id", "unknown"),
        "estimated_duration_minutes": duration,
        "data_source": "estimated",
        "note": "Duration is an OSRM route estimate, not live traffic congestion.",
    }
