"""Check the reminder behaviour of the real AI (Gemini) - run it after changing the system prompt.

Unlike the unit tests, this talks to the real model, so it costs a little quota and takes a
minute or two. Every case runs in a fresh chat against a real ``BackgroundMonitor`` that keeps
its reminders in a temporary file (the user's own reminders are never touched), and checks what
really happened to the reminder list, not what the reply claims:

- ``set``    - a clear time or delay: exactly one new reminder must exist afterwards.
- ``ask``    - no time or a vague one: nothing may be set, and the reply must ask (contain "?").
- ``cancel`` - reminders are prepared first; the message must cancel exactly the named one.

Usage (Windows venv, needs ``GEMINI_API_KEY`` in ``.env``)::

    .venv-win/Scripts/python.exe src/reminder_check.py            # every case twice
    .venv-win/Scripts/python.exe src/reminder_check.py --repeat 4

Exit code 0 = every run passed, 1 = at least one failed (round 26: a prompt change once made the
model claim "done" without calling the tool; this script catches that).
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtWidgets import QApplication  # noqa: E402


@dataclass
class Case:
    """One check: what the user says (one or more turns) and what must happen.

    ``prepare`` lists reminders (message, minutes from now) created before the chat, and
    ``target`` names the one a ``cancel`` case must remove."""

    expect: str
    turns: list[str]
    prepare: list[tuple[str, float]] = field(default_factory=list)
    target: str = ""


CASES = [
    Case("set", ["remind me to stretch in 5 minutes"]),
    Case("set", ["hẹn giờ 10 phút"]),
    Case("set", ["nhắc mình 14h họp"]),
    Case("set", ["nhắc tôi uống nước sau 1 phút"]),
    Case("set", ["nhớ báo mình lúc 7h sáng mai đi chạy bộ"]),
    Case("set", ["đừng để mình quên uống thuốc sau 45 phút"]),
    Case("ask", ["nhắc mình gọi mẹ nhé"]),
    Case("ask", ["tối nay nhắc tớ đi đổ rác"]),
    Case("set", ["tối nay nhắc tớ đi đổ rác", "ok"]),
    Case("cancel", ["thôi khỏi nhắc vụ đổ rác nữa"],
         prepare=[("đi đổ rác", 300), ("gọi mẹ", 90)], target="đi đổ rác"),
    Case("cancel", ["thôi không cần nhắc nữa"], prepare=[("uống nước", 30)],
         target="uống nước"),
]


def pump(app: QApplication, seconds: float = 0.3) -> None:
    """Let queued signals (the tools' hand-offs to the monitor) arrive."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.01)


def run_case(app: QApplication, case: Case) -> tuple[bool, str]:
    """Run one case in a fresh chat; returns (passed, last reply)."""
    from agent.emotion import split_emotion
    from agent.graph import run_agent
    from monitor.background_monitor import BackgroundMonitor

    monitor = BackgroundMonitor(reminders_path=Path(tempfile.mkdtemp()) / "reminders.json")
    for timer in (monitor._status_timer, monitor._reminder_timer, monitor._idle_timer):
        timer.stop()
    for message, minutes in case.prepare:
        monitor.schedule_reminder(time.time() + minutes * 60, message)
    pump(app)
    before = monitor.pending_reminders()
    history: list[dict] = []
    reply = ""
    for turn in case.turns:
        raw = run_agent(history, turn)
        history += [{"role": "user", "content": turn}, {"role": "assistant", "content": raw}]
        reply = split_emotion(raw)[1]
        pump(app)
    after = monitor.pending_reminders()
    if case.expect == "set":
        passed = len(after) == len(before) + 1
    elif case.expect == "ask":
        passed = len(after) == len(before) and "?" in reply
    else:
        left = [r.message for r in after]
        passed = (case.target not in left
                  and len(after) == len(before) - 1)
    return passed, reply


def main() -> int:
    """Run every case ``--repeat`` times and print a PASS / FAIL table."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repeat", type=int, default=2, help="runs per case (default 2)")
    args = parser.parse_args()
    app = QApplication.instance() or QApplication([])

    import config
    if not config.GEMINI_API_KEY:
        print("GEMINI_API_KEY is not set (.env); nothing to check.")
        return 1

    failures = 0
    for case in CASES:
        results = [run_case(app, case) for _ in range(args.repeat)]
        passed = sum(ok for ok, _ in results)
        failures += args.repeat - passed
        status = "PASS" if passed == args.repeat else "FAIL"
        said = " / ".join(case.turns)
        print(f"{status} {passed}/{args.repeat}  [{case.expect}] {said}")
        for ok, reply in results:
            if not ok:
                print(f"       reply: {reply[:150]!r}")
    print("all passed" if failures == 0 else f"{failures} run(s) failed")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
