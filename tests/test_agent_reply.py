"""Tests for agent.graph.run_agent with the LLM faked out (no network)."""
import pytest
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

import api_keys
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
    monkeypatch.setattr(api_keys, "gemini_api_key", lambda: "")
    with pytest.raises(MissingApiKeyError):
        graph.run_agent([], "hi")


def test_reminder_tool_is_offered():
    """Reminders are back on (round 24): the model may call set_timer_reminder."""
    assert "set_timer_reminder" in {t.name for t in graph.TOOLS}


def test_prompt_carries_the_current_time():
    """Every call tells the model the local date and time (for "tonight", "tomorrow at 7")."""
    from datetime import datetime

    text = graph.system_prompt(datetime(2026, 11, 14, 15, 20))
    assert text.endswith("Current local date and time: Saturday 2026-11-14 15:20.")
    messages = graph._prompt({"messages": []})
    assert messages[0].content.startswith(graph.SYSTEM_PROMPT)


def test_prompt_asks_for_user_language_and_emotion_tag():
    """The model answers in the user's language and starts with an emotion tag."""
    assert "same language" in graph.SYSTEM_PROMPT
    assert "[happy]" in graph.SYSTEM_PROMPT and "[other]" in graph.SYSTEM_PROMPT


class FakeStreamingAgent:
    """Mimics ``stream(..., stream_mode=["messages", "values"])``: a first model message that
    calls a tool, the tool result, then the answer arriving in pieces."""

    def stream(self, state, stream_mode):
        """Yield (mode, data) pairs like LangGraph does."""
        assert stream_mode == ["messages", "values"]
        yield "messages", (AIMessageChunk(content="Let me look", id="m1"), {})
        yield "messages", (ToolMessage(content="18 C", tool_call_id="t1"), {})
        yield "messages", (AIMessageChunk(content="[happy", id="m2"), {})
        yield "messages", (AIMessageChunk(content="] It is ", id="m2"), {})
        yield "messages", (AIMessageChunk(content="", id="m2"), {})
        yield "messages", (AIMessageChunk(content="18 C!", id="m2"), {})
        yield "values", {"messages": [*state["messages"], AIMessage(content="[happy] It is 18 C!")]}


def test_streaming_reports_growing_text(monkeypatch):
    """With on_text the reply arrives piece by piece; a new model message starts over and tool
    results are never shown. The return value is the final message."""
    monkeypatch.setattr(graph, "_agent", FakeStreamingAgent())
    seen = []
    reply = graph.run_agent([], "weather?", on_text=seen.append)
    assert seen == ["Let me look", "[happy", "[happy] It is ", "[happy] It is 18 C!"]
    assert reply == "[happy] It is 18 C!"


def test_provider_must_be_known():
    """Only the supported AI providers can be chosen."""
    with pytest.raises(ValueError):
        graph.set_provider("claude")


def test_openai_provider_needs_the_openai_key(monkeypatch):
    """With OpenAI chosen, a Gemini key alone is not enough."""
    monkeypatch.setattr(graph, "_provider", "openai")
    monkeypatch.setattr(api_keys, "gemini_api_key", lambda: "gemini-key")
    monkeypatch.setattr(api_keys, "openai_api_key", lambda: "")
    with pytest.raises(MissingApiKeyError):
        graph._build_llm()


def test_each_provider_builds_its_own_model(monkeypatch):
    """The chosen provider decides the chat model class and the model name from config.yaml."""
    monkeypatch.setattr(api_keys, "gemini_api_key", lambda: "gemini-key")
    monkeypatch.setattr(api_keys, "openai_api_key", lambda: "sk-test")
    monkeypatch.setattr(graph, "_provider", "openai")
    openai_llm = graph._build_llm()
    assert type(openai_llm).__name__ == "ChatOpenAI"
    assert openai_llm.model_name == "gpt-4o-mini"
    monkeypatch.setattr(graph, "_provider", "gemini")
    assert type(graph._build_llm()).__name__ == "ChatGoogleGenerativeAI"


def test_changing_the_provider_drops_the_built_agent(monkeypatch):
    """The next chat after a provider change builds a fresh agent."""
    monkeypatch.setattr(graph, "_agent", object())
    monkeypatch.setattr(graph, "_provider", "gemini")
    graph.set_provider("openai")
    assert graph._agent is None
    graph.set_provider("gemini")
