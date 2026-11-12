"""Tests for agent.graph.run_agent with the LLM faked out (no network)."""
import pytest
from langchain_core.messages import AIMessage

import config
from agent import graph
from agent.errors import MissingApiKeyError


class FakeAgent:
    """Returns a fixed final message and records what it was given."""

    def __init__(self, message):
        self.message, self.seen = message, None

    def invoke(self, state):
        """Mimic LangGraph's ``invoke`` result shape."""
        self.seen = state["messages"]
        return {"messages": [*state["messages"], self.message]}


def test_block_content_is_joined_to_text(monkeypatch):
    """Newer Gemini replies are lists of blocks; only the text parts reach the chat."""
    fake = FakeAgent(AIMessage(content=[{"type": "text", "text": "Hi ", "extras": {"sig": "x"}},
                                        {"type": "text", "text": "there!"}]))
    monkeypatch.setattr(graph, "_agent", fake)
    assert graph.run_agent([{"role": "user", "content": "a"}], "b") == "Hi there!"
    assert [m["content"] for m in fake.seen] == ["a", "b"]


def test_plain_string_content(monkeypatch):
    """Older string replies still work."""
    monkeypatch.setattr(graph, "_agent", FakeAgent(AIMessage(content="  hello  ")))
    assert graph.run_agent([], "x") == "hello"


def test_missing_key_raises_clear_error(monkeypatch):
    """Without a key the agent is not built and a MissingApiKeyError explains why."""
    monkeypatch.setattr(graph, "_agent", None)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    with pytest.raises(MissingApiKeyError):
        graph.run_agent([], "hi")


def test_reminder_tool_is_switched_off():
    """Reminders are disabled for now: the model is not offered set_timer_reminder."""
    assert "set_timer_reminder" not in {t.name for t in graph.TOOLS}
