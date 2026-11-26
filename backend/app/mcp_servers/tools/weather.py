"""Weather MCP tools backed by Open-Meteo."""

from __future__ import annotations

from typing import Any

from app.integrations.weather_client import WeatherClient

_weather = WeatherClient()


async def get_current_weather(latitude: float, longitude: float) -> dict[str, Any]:
    """Get current weather conditions at the specified coordinates via Open-Meteo."""
    return await _weather.get_current_weather(latitude, longitude)


async def get_weather_forecast(latitude: float, longitude: float) -> dict[str, Any]:
    """Get today's hourly weather forecast at the specified coordinates via Open-Meteo."""
    return await _weather.get_weather_forecast(latitude, longitude)
