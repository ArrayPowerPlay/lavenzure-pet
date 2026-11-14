"""LangGraph tool-calling agent backed directly by the Google Gemini API.

The Gemini client and the agent graph are built lazily on the first chat message (not at import
time), so the pet still starts when ``GEMINI_API_KEY`` is missing; the chat then explains that a
key is needed instead of the whole app crashing.

``run_agent`` can stream: given an ``on_text`` callback it reports the reply text as it grows
(token chunks from the model), so the chat can show the answer while it is still being written.

Every model call gets the system prompt plus the PC's current local date and time (``_prompt``),
so the model understands "tonight" or "tomorrow at 7" when setting reminders. The reminder rules
(ask for a time with a suggestion when none or only a vague one is given; list before cancelling)
are part of the system prompt, with the suggested times read from ``config.yaml``.
"""
from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import datetime

from langchain_core.messages import AIMessageChunk, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

import config
from agent.emotion import EMOTION_INSTRUCTIONS
from agent.errors import MissingApiKeyError
from agent.tools.set_timer_reminder import (
    cancel_reminder,
    dismiss_reminder_bubble,
    list_reminders,
    set_timer_reminder,
)
from agent.tools.system_status import system_status
from agent.tools.weather import get_weather
from agent.tools.web_search import web_search

log = logging.getLogger(__name__)

# Times suggested when the user asks for a reminder without a clear time (round 25).
DEFAULT_SUGGESTED_TIMES = {"morning": "08:00", "noon": "12:00", "afternoon": "15:00",
                           "evening": "20:00", "late night": "22:00"}
DEFAULT_DELAY_MINUTES = 30


def reminder_rules() -> str:
    """The reminder part of the system prompt, with the suggested times from config.yaml."""
    times = config.get("reminders.suggested_times", None) or DEFAULT_SUGGESTED_TIMES
    delay = config.get("reminders.suggested_delay_minutes", DEFAULT_DELAY_MINUTES)
    table = ", ".join(f"{part} {clock}" for part, clock in times.items())
    return (
        "Reminders: writing that a reminder is set does nothing; only a set_timer_reminder "
        "tool call creates one. So when the user asks for a reminder or timer with a clear "
        "time or delay (e.g. 'in 5 minutes', 'hẹn giờ 10 phút' = in 10 minutes, 'at 14h', "
        "'7h sáng mai' = tomorrow 07:00), your FIRST step is the set_timer_reminder call; "
        "only after its result may you tell the user it is set. The same goes for "
        "cancelling (cancel_reminder). Never claim a reminder was set or cancelled when you "
        "did not call the tool in this turn. "
        "Whenever the user wants to be reminded or notified of something later, "
        "in any wording (e.g. 'remind me', 'nhắc mình', 'nhắc tớ', 'nhớ báo mình', "
        "'đừng để mình quên'), handle it as a reminder. "
        "If they give an exact time or delay, call set_timer_reminder right away: pass "
        "'minutes' for a delay or 'at' for a clock time, let the tool work out the exact time, "
        "then confirm the time it reports. "
        "If they give no time, or only a vague one ('tonight', 'this afternoon', 'later', "
        "'soon'), do NOT set it yet: ask what time, and suggest one in the same question "
        f"(by part of the day: {table}; with no time at all: in {delay} minutes). "
        "Set it once they accept the suggestion or give a time. "
        "When the user no longer needs a reminder, or wants to change one, call list_reminders, "
        "then cancel_reminder with its number; to change it, cancel it and set a new one. "
        "If only one reminder could be meant (the only pending one, or the one just discussed), "
        "cancel it without asking; if several could be meant, ask which one and list them. "
        "If they want to turn off a reminder that is showing on the pet right now, call "
        "dismiss_reminder_bubble. "
    )


SYSTEM_PROMPT = (
    "You are Lavenzure, a small, witty fire spirit living on the user's desktop. "
    "Keep replies short, warm, and a little playful. Use tools when the user asks "
    "about weather, needs a web search, or asks about their PC's CPU/RAM/battery status. "
    + reminder_rules()
    + "Always reply in the same language the user writes in. "
    + EMOTION_INSTRUCTIONS
)

# Reminders were switched off on 2026-11-12 and switched back on in round 24 (saved to a file);
# listing / cancelling them came in round 25.
TOOLS = [get_weather, web_search, system_status, set_timer_reminder, list_reminders,
         cancel_reminder, dismiss_reminder_bubble]

_agent = None
_agent_lock = threading.Lock()


def system_prompt(now: datetime) -> str:
    """The system prompt with the current local date and time appended."""
    return f"{SYSTEM_PROMPT} Current local date and time: {now:%A %Y-%m-%d %H:%M}."


def _prompt(state) -> list:
    """Messages sent to the model on every step: the timestamped system prompt + the chat."""
    return [SystemMessage(content=system_prompt(datetime.now())), *state["messages"]]


def _build_agent():
    """Create the Gemini chat model and wrap it in a LangGraph ReAct (tool-calling) agent.

    Raises ``MissingApiKeyError`` when no Gemini key is configured.
    """
    if not config.GEMINI_API_KEY:
        raise MissingApiKeyError("GEMINI_API_KEY is not set in .env")
    model = config.get("llm.model", "gemini-flash-lite-latest")
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
        tools=TOOLS,
        prompt=_prompt,
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


def _text_of(message) -> str:
    """Plain text of a (chunk of a) model message.

    Newer Gemini models return a list of content blocks (text + thought signatures); ``.text``
    joins just the text parts.
    """
    text = getattr(message, "text", None)
    if not isinstance(text, str):
        text = str(getattr(message, "content", message))
    return text


def run_agent(history: list[dict], user_message: str,
              on_text: Callable[[str], None] | None = None) -> str:
    """Invoke the agent with prior turn history plus the new user message; returns the reply text.

    With ``on_text``, the reply is streamed: ``on_text(text_so_far)`` is called (from this same
    thread) every time a new piece of the model's text arrives. If the model first writes a bit
    of text and then calls a tool, the next model message starts over from an empty text.

    The text still starts with the emotion tag (see ``agent.emotion``); the caller splits it off.

    Exceptions (missing key, quota, network, ...) propagate to the caller, which turns them into a
    friendly message with ``agent.errors.friendly_error``.
    """
    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": user_message})
    agent = _get_agent()
    if on_text is None:
        last = agent.invoke({"messages": messages})["messages"][-1]
    else:
        last = _stream(agent, messages, on_text)
    return _text_of(last).strip() or "*crackle* ...I lost my words. Try asking again?"


def _stream(agent, messages: list[dict], on_text: Callable[[str], None]):
    """Run the agent with token streaming; returns the final message of the conversation."""
    final_state = None
    current_id, current_text = None, ""
    for mode, data in agent.stream({"messages": messages}, stream_mode=["messages", "values"]):
        if mode == "values":
            final_state = data      # the full state after each step; the last one wins
            continue
        chunk, _metadata = data
        if not isinstance(chunk, AIMessageChunk):
            continue                # tool results are not shown
        piece = _text_of(chunk)
        if not piece:
            continue
        if chunk.id != current_id:  # a new model message (e.g. after a tool call)
            current_id, current_text = chunk.id, ""
        current_text += piece
        on_text(current_text)
    if final_state is None:
        raise RuntimeError("the agent stream ended without a result")
    return final_state["messages"][-1]
