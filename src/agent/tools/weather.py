"""Weather tool backed by the free Open-Meteo geocoding + forecast APIs (no API key needed).

Network/API failures are caught and returned as text, so the model can tell the user what went
wrong instead of the whole chat turn failing.
"""
from __future__ import annotations

import logging

import requests
from langchain_core.tools import tool

log = logging.getLogger(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SECONDS = 10


def _get_json(url: str, params: dict) -> dict:
    """GET ``url`` and return the decoded JSON body; raises on HTTP or network errors."""
    response = requests.get(url, params=params, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


@tool
def get_weather(location: str) -> str:
    """Get the current weather for a place name mentioned by the user, e.g. 'Hanoi' or 'Tokyo'."""
    try:
        geo = _get_json(GEOCODE_URL, {"name": location, "count": 1})
        results = geo.get("results")
        if not results:
            return f"I couldn't find a place called '{location}'."
        place = results[0]
        forecast = _get_json(
            FORECAST_URL,
            {"latitude": place["latitude"], "longitude": place["longitude"],
             "current_weather": "true"},
        )
    except (requests.RequestException, ValueError, KeyError) as exc:
        log.warning("Weather lookup for %r failed: %s", location, exc)
        return f"The weather service couldn't be reached right now ({type(exc).__name__})."

    current = forecast.get("current_weather", {})
    temp = current.get("temperature")
    wind = current.get("windspeed")
    return (
        f"Weather in {place.get('name', location)}, {place.get('country', '')}: "
        f"{temp}°C, wind {wind} km/h."
    )
