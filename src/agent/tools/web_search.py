"""Web search tool backed by the Tavily API (requires TAVILY_API_KEY in .env).

Any failure (bad query, network, quota) is returned as text so the model can explain it or retry
with a better query, instead of the whole chat turn failing.
"""
from __future__ import annotations

import logging

from langchain_core.tools import tool
from tavily import TavilyClient

import config

log = logging.getLogger(__name__)

_client = TavilyClient(api_key=config.TAVILY_API_KEY) if config.TAVILY_API_KEY else None


@tool
def web_search(query: str) -> str:
    """Search the web for up-to-date information the model doesn't already know."""
    if _client is None:
        return "Web search isn't configured (missing TAVILY_API_KEY)."
    try:
        response = _client.search(query=query, max_results=3)
    except Exception as exc:  # noqa: BLE001 - Tavily raises many types; report them all to the model
        log.warning("Web search for %r failed: %s", query, exc)
        return f"Web search failed: {exc}. Try rephrasing the query with plain search words."
    results = response.get("results", [])
    if not results:
        return "No results found."
    lines = [f"- {r.get('title', '')}: {r.get('content', '')[:200]}" for r in results]
    return "\n".join(lines)
