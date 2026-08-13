"""In-memory chat history for a single session, wiped after a period of inactivity (TTL)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class SessionMemory:
    ttl_seconds: int
    messages: list[dict] = field(default_factory=list)
    _last_activity: float = field(default_factory=time.time)

    def add(self, role: str, content: str) -> None:
        self._last_activity = time.time()
        self.messages.append({"role": role, "content": content})

    def get_history(self) -> list[dict]:
        self._expire_if_needed()
        return list(self.messages)

    def _expire_if_needed(self) -> None:
        if self.messages and time.time() - self._last_activity > self.ttl_seconds:
            self.messages.clear()

    def check_and_clear_if_idle(self) -> bool:
        """Called periodically; returns True if history was just cleared due to inactivity."""
        if self.messages and time.time() - self._last_activity > self.ttl_seconds:
            self.messages.clear()
            return True
        return False
