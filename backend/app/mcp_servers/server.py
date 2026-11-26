"""Modular FastMCP server exposing DayShield routing, weather, calendar, and email-draft tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.mcp_servers.tools.calendar import (
    get_available_slots,
    get_event_details,
    get_today_events,
)
from app.mcp_servers.tools.email import create_email_draft
from app.mcp_servers.tools.routing import (
    calculate_route_duration,
    get_alternative_routes,
    get_route,
)
from app.mcp_servers.tools.weather import get_current_weather, get_weather_forecast

mcp = FastMCP("dayshield-tools")

# Routing tools
mcp.tool()(get_route)
mcp.tool()(get_alternative_routes)
mcp.tool()(calculate_route_duration)

# Weather tools
mcp.tool()(get_current_weather)
mcp.tool()(get_weather_forecast)

# Calendar tools (read-only)
mcp.tool()(get_today_events)
mcp.tool()(get_event_details)
mcp.tool()(get_available_slots)

# Email tools (draft-only)
mcp.tool()(create_email_draft)


if __name__ == "__main__":
    mcp.run()
