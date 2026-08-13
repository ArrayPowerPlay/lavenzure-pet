"""LangGraph tool-calling agent backed directly by the Google Gemini API."""
from __future__ import annotations

import config
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from agent.tools.set_timer_reminder import set_timer_reminder
from agent.tools.system_status import system_status
from agent.tools.weather import get_weather
from agent.tools.web_search import web_search

SYSTEM_PROMPT = (
    "You are Calcifer, a small, witty fire spirit living on the user's desktop. "
    "Keep replies short, warm, and a little playful. Use tools when the user asks "
    "about weather, needs a web search, wants a reminder, or asks about their PC's "
    "CPU/RAM/battery status."
)

_llm = ChatGoogleGenerativeAI(
    model=config.get("llm.model", "gemini-2.0-flash"),
    google_api_key=config.GEMINI_API_KEY,
    temperature=config.get("llm.temperature", 0.7),
)

_agent = create_react_agent(
    _llm,
    tools=[get_weather, web_search, set_timer_reminder, system_status],
    prompt=SYSTEM_PROMPT,
)


def run_agent(history: list[dict], user_message: str) -> str:
    """Invoke the agent with prior turn history plus the new user message; returns the reply text."""
    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": user_message})
    result = _agent.invoke({"messages": messages})
    last = result["messages"][-1]
    return getattr(last, "content", str(last))
