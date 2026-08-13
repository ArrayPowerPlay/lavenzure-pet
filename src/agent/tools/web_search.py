"""Web search tool backed by the Tavily API (requires TAVILY_API_KEY in .env)."""
from __future__ import annotations

import config
from langchain_core.tools import tool
from tavily import TavilyClient

_client = TavilyClient(api_key=config.TAVILY_API_KEY) if config.TAVILY_API_KEY else None


@tool
def web_search(query: str) -> str:
    """Search the web for up-to-date information the model doesn't already know."""
    if _client is None:
        return "Web search isn't configured (missing TAVILY_API_KEY)."
    response = _client.search(query=query, max_results=3)
    results = response.get("results", [])
    if not results:
        return "No results found."
    lines = [f"- {r['title']}: {r['content'][:200]}" for r in results]
    return "\n".join(lines)
