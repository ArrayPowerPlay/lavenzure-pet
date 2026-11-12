"""In-memory chat history for a single session, wiped after a period of inactivity (TTL)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class SessionMemory:
    """Chat turns of the single current session, cleared after ``ttl_seconds`` of inactivity.

    Nothing is ever written to disk (by design).
    """

    ttl_seconds: int
    messages: list[dict] = field(default_factory=list)
    _last_activity: float = field(default_factory=time.time)

    def add(self, role: str, content: str) -> None:
        """Append one message (``role`` is "user" or "assistant") and reset the idle clock."""
        self._last_activity = time.time()
        self.messages.append({"role": role, "content": content})

    def get_history(self) -> list[dict]:
        """Return a copy of the history, clearing it first if the session has expired."""
        self._expire_if_needed()
        return list(self.messages)

    def _expire_if_needed(self) -> None:
        """Clear the history if it has been idle for longer than the TTL."""
        if self.messages and time.time() - self._last_activity > self.ttl_seconds:
            self.messages.clear()

    def check_and_clear_if_idle(self) -> bool:
        """Called periodically; returns True if history was just cleared due to inactivity."""
        if self.messages and time.time() - self._last_activity > self.ttl_seconds:
            self.messages.clear()
            return True
        return False
