"""Weather tool backed by the free Open-Meteo geocoding + forecast APIs (no API key needed)."""
from __future__ import annotations

import requests
from langchain_core.tools import tool

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


@tool
def get_weather(location: str) -> str:
    """Get the current weather for a place name mentioned by the user, e.g. 'Hanoi' or 'Tokyo'."""
    geo = requests.get(GEOCODE_URL, params={"name": location, "count": 1}, timeout=10).json()
    results = geo.get("results")
    if not results:
        return f"I couldn't find a place called '{location}'."
    place = results[0]
    lat, lon = place["latitude"], place["longitude"]

    forecast = requests.get(
        FORECAST_URL,
        params={"latitude": lat, "longitude": lon, "current_weather": "true"},
        timeout=10,
    ).json()
    current = forecast.get("current_weather", {})
    temp = current.get("temperature")
    wind = current.get("windspeed")
    return (
        f"Weather in {place.get('name', location)}, {place.get('country', '')}: "
        f"{temp}\u00b0C, wind {wind} km/h."
    )
