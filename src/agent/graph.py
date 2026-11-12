"""LangGraph tool-calling agent backed directly by the Google Gemini API.

The Gemini client and the agent graph are built lazily on the first chat message (not at import
time), so the pet still starts when ``GEMINI_API_KEY`` is missing; the chat then explains that a
key is needed instead of the whole app crashing.
"""
from __future__ import annotations

import logging
import threading

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

import config
from agent.errors import MissingApiKeyError
from agent.tools.set_timer_reminder import set_timer_reminder
from agent.tools.system_status import system_status
from agent.tools.weather import get_weather
from agent.tools.web_search import web_search

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are Calcifer, a small, witty fire spirit living on the user's desktop. "
    "Keep replies short, warm, and a little playful. Use tools when the user asks "
    "about weather, needs a web search, wants a reminder, or asks about their PC's "
    "CPU/RAM/battery status."
)

_agent = None
_agent_lock = threading.Lock()


def _build_agent():
    """Create the Gemini chat model and wrap it in a LangGraph ReAct (tool-calling) agent.

    Raises ``MissingApiKeyError`` when no Gemini key is configured.
    """
    if not config.GEMINI_API_KEY:
        raise MissingApiKeyError("GEMINI_API_KEY is not set in .env")
    model = config.get("llm.model", "gemini-flash-latest")
    llm = ChatGoogleGenerativeAI(
        model=model,
        google_api_key=config.GEMINI_API_KEY,
        temperature=config.get("llm.temperature", 0.7),
        # The "-latest" aliases (e.g. gemini-flash-latest) only exist on the v1beta endpoint.
        api_version=config.get("llm.api_version", "v1beta"),
        # Fail fast with a clear error instead of retrying for minutes (e.g. when out of quota).
        timeout=config.get("llm.timeout_seconds", 60),
        max_retries=config.get("llm.max_retries", 2),
    )
    log.info("Gemini agent created (model=%s)", model)
    return create_react_agent(
        llm,
        tools=[get_weather, web_search, set_timer_reminder, system_status],
        prompt=SYSTEM_PROMPT,
    )


def _get_agent():
    """Return the shared agent, building it on first use.

    Thread-safe: it is called from chat worker threads.
    """
    global _agent
    with _agent_lock:
        if _agent is None:
            _agent = _build_agent()
        return _agent


def run_agent(history: list[dict], user_message: str) -> str:
    """Invoke the agent with prior turn history plus the new user message; returns the reply text.

    Exceptions (missing key, quota, network, ...) propagate to the caller, which turns them into a
    friendly message with ``agent.errors.friendly_error``.
    """
    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": user_message})
    result = _get_agent().invoke({"messages": messages})
    last = result["messages"][-1]
    # Newer Gemini models return a list of content blocks (text + thought signatures);
    # ``.text`` joins just the text parts.
    text = getattr(last, "text", None)
    if not isinstance(text, str):
        text = str(getattr(last, "content", last))
    return text.strip() or "*crackle* ...I lost my words. Try asking again?"
