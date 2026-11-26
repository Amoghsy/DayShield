"""Open-Meteo weather client (free, no API key or billing required)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("dayshield.integrations.weather")

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

WMO_WEATHER_CODES: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Light rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Light snow",
    80: "Light rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
}


class WeatherClient:
    """Async client for Open-Meteo current weather and short-term forecast."""

    def __init__(self, base_url: str = OPEN_METEO_URL, timeout: float = 8.0) -> None:
        self.base_url = base_url
        self.timeout = timeout

    async def get_current_weather(self, latitude: float, longitude: float) -> dict[str, Any]:
        """Fetch current weather conditions from Open-Meteo."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,precipitation,weather_code,wind_speed_10m",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.base_url, params=params)
                resp.raise_for_status()
                data = resp.json()

            current = data.get("current", {})
            code = int(current.get("weather_code", 0))
            condition = WMO_WEATHER_CODES.get(code, f"Weather code {code}")
            temp = current.get("temperature_2m")
            precip = current.get("precipitation", 0.0)

            return {
                "ok": True,
                "data_source": "live",
                "condition": condition,
                "temperature_c": temp,
                "precipitation_mm": precip,
                "wind_speed_kmh": current.get("wind_speed_10m"),
                "summary": f"{condition}, {temp}°C (precip {precip} mm)",
            }
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning("Open-Meteo current weather failed: %s", exc)
            return {
                "ok": False,
                "data_source": "live",
                "error": f"Open-Meteo unavailable: {exc}",
                "condition": "Unknown",
                "summary": "Weather data unavailable",
            }

    async def get_weather_forecast(self, latitude: float, longitude: float) -> dict[str, Any]:
        """Fetch today's hourly precipitation probability & weather codes from Open-Meteo."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "precipitation_probability,weather_code,temperature_2m",
            "forecast_days": 1,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.base_url, params=params)
                resp.raise_for_status()
                data = resp.json()

            hourly = data.get("hourly", {})
            times = hourly.get("time", [])[:8]
            probs = hourly.get("precipitation_probability", [])[:8]
            codes = hourly.get("weather_code", [])[:8]
            temps = hourly.get("temperature_2m", [])[:8]

            slots = [
                {
                    "time": t,
                    "precipitation_probability": p,
                    "condition": WMO_WEATHER_CODES.get(int(c), f"Code {c}"),
                    "temperature_c": temp,
                }
                for t, p, c, temp in zip(times, probs, codes, temps)
            ]

            return {
                "ok": True,
                "data_source": "live",
                "hourly_forecast": slots,
            }
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning("Open-Meteo forecast failed: %s", exc)
            return {
                "ok": False,
                "data_source": "live",
                "error": f"Open-Meteo forecast unavailable: {exc}",
                "hourly_forecast": [],
            }
