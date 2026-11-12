"""Tests for SessionMemory: RAM-only history wiped after the inactivity TTL."""
from agent import memory as memory_module
from agent.memory import SessionMemory


def test_history_kept_within_ttl(monkeypatch):
    """Messages added recently are returned in order."""
    now = [1000.0]
    monkeypatch.setattr(memory_module.time, "time", lambda: now[0])
    mem = SessionMemory(ttl_seconds=600)
    mem.add("user", "hi")
    mem.add("assistant", "hello")
    now[0] += 599
    assert [m["content"] for m in mem.get_history()] == ["hi", "hello"]


def test_history_cleared_after_ttl(monkeypatch):
    """After more than ``ttl_seconds`` without activity the history is empty."""
    now = [1000.0]
    monkeypatch.setattr(memory_module.time, "time", lambda: now[0])
    mem = SessionMemory(ttl_seconds=600)
    mem.add("user", "hi")
    now[0] += 601
    assert mem.get_history() == []
    assert mem.check_and_clear_if_idle() is False  # already cleared


def test_get_history_returns_copy():
    """Callers (the worker thread) get a snapshot, not the live list."""
    mem = SessionMemory(ttl_seconds=600)
    mem.add("user", "hi")
    snapshot = mem.get_history()
    mem.add("assistant", "hello")
    assert len(snapshot) == 1
