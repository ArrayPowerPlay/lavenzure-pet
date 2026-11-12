# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Calcifer-style desktop pet for **Windows only, single monitor, personal use** (fan-art of a copyrighted character — never distribute or use original film assets). A flame character lives in an always-on-top transparent window, wanders around the screen, reacts to clicks/drags, and opens a chat window (right-click) backed by a tool-calling LangGraph agent on Gemini.

Design docs (Vietnamese) are the source of truth for decisions — read them before changing behavior, and update them when a design decision changes:
- `CONTEXT.md` — goals, architecture diagram, locked technical decisions table, change log (§7).
- `implementation_plan.md` — phase checklist and current implementation status.
- `ANIMATION_TUTORIAL.md` — superseded PNG-cutout plan (kept for reference only).

The user writes in Vietnamese; all **on-screen pet lines** (click reactions, facts/jokes, alerts) must be **English**.

## Environment & commands

The repo lives in WSL and has **two venvs** (both git-untracked):

- `.venv-win` — **Windows** venv (Python 3.13, PySide6, includes `pywin32`). Use it for the real app: run it from WSL and real windows open on the Windows desktop. Required for `src/main.py`, autostart and (future) PyInstaller packaging, since the pet is Windows-only.
- `.venv` — **Linux** venv (Python 3.12, no `pywin32`). Only for quick animation previews through WSLg; transparency / always-on-top / click-through behave differently there, so never use it to judge overlay behavior.

```bash
.venv-win/Scripts/python.exe src/main.py                        # run the app (real Windows desktop)
.venv-win/Scripts/python.exe -m pip install -r requirements.txt # install deps (Windows venv)
QT_QPA_PLATFORM=offscreen .venv-win/Scripts/python.exe src/main.py   # headless smoke test
.venv-win/Scripts/python.exe src/autostart/install_startup.py   # create Startup-folder shortcut (pythonw.exe)
.venv-win/Scripts/python.exe src/character_preview.py           # try every mood/motion of the character in a normal window
.venv/bin/python src/character_preview.py                       # same preview via WSLg (Linux venv)
```

- If `.venv-win/Scripts/*.exe` gives "Permission denied" from WSL after recreating the venv, run `chmod +x .venv-win/Scripts/*.exe`.
- The Linux venv is installed from `requirements.txt` minus the `pywin32` line (it has no Linux wheel).
- `src/` is the import root: modules use `import config`, `from overlay.x import ...` (no `src.` prefix). Run scripts as `src/main.py` (script dir goes on `sys.path`), or set `PYTHONPATH=src`.
- No tests, linter, or build step exist yet. Packaging (PyInstaller) is a future phase.
- `src/agent/graph.py` builds the Gemini client at import time, so `main.py` crashes without `GEMINI_API_KEY`; for UI-only testing pass a dummy key: `GEMINI_API_KEY=dummy WSLENV=GEMINI_API_KEY .venv-win/Scripts/python.exe ...`. Importing the app over the `\\wsl.localhost` share takes ~50 s on first run.
- To inspect the character without a display, render `FlameCharacter.paint()` into a `QImage` under `QT_QPA_PLATFORM=offscreen` and save a PNG.
- Secrets: copy `.env.example` → `.env` with `GEMINI_API_KEY`, `TAVILY_API_KEY`. Non-secret settings live in `config.yaml`, read via `config.get("dotted.path", default)`.
- Source files use **CRLF** line endings; preserve them (a whole-file diff with no real change is usually a line-ending flip).

## Architecture

Single process, single `QApplication`. `src/main.py` (`CalciferApp`) constructs every component and wires them together with Qt signals — components don't reference each other directly; trace behavior by following the connections in `_wire_signals`.

- **Overlay** (`src/overlay/`):
  - `character.py` `FlameCharacter` — the pet itself, drawn entirely with QPainter vectors (no image assets). Plain model+renderer, not a widget: `update(dt, window_pos, cursor)` then `paint(painter)`. Body language (lean, stretch, landing squash, walking hops, embers trailing in screen space) is **derived from the window's own movement**, so movement code never animates the body directly. Mood = base flags (`set_alert`, `set_thinking`) overridden by transient `play(mood, seconds)`; all face parameters blend via the `Expression` dataclass.
  - `fire_field.py` `FireField` — the flame shape (needs `numpy`): a particle sim of flame "tongues" summed into a metaball density field; the three color layers are marching-squares contours of that field (holes/nested loops dropped). Tuning constants live at the top of the file; check perf with ~3-5 ms/frame as the budget.
  - `overlay_window.py` `OverlaySprite` — frameless, `WindowStaysOnTopHint | Tool`, translucent; runs the frame timer (`character.fps`) and hosts `.character`. Keeps a float window position (`exactPos` Qt property; move the pet with `set_exact_pos`, not `move`) and draws the sub-pixel remainder as an offset; its frame loop is a `QAbstractAnimation` so it ticks in the same pass as the movement animations. Emits `clicked` (press+release without moving), `drag_started`/`drag_ended` (after a 6px threshold), `right_clicked`. Click-through relies on Windows per-pixel-alpha hit-testing of layered windows — do **not** add `setMask()` (it would clip the glow/embers); keep the glow fading to alpha 0.
  - `behavior.py` `BehaviorController` — `PetState` machine (IDLE/WALK/FLOAT/JUMP random loop weighted by `behavior.state_weights`; DRAGGED/REACT/ALERT set `_locked` to override the loop) and maps states to character moods. It moves the *whole window* (`animation.py`: speed-based moves, parabolic jump). Uses restartable single-shot `QTimer`s, not `QTimer.singleShot`, so stale timeouts can't double-advance the loop.
  - `speech_bubble.py` — separate top-level window, centered over `sprite.bubble_anchor()`; `auto_hide_ms=None` = sticky (used for alerts).
- **Chat** (`src/chat/chat_window.py`) — emits `message_sent`; main runs the agent in a fresh `QThread` + `AgentWorker` and posts the reply back via signals. Never call the agent on the UI thread.
- **Agent** (`src/agent/`) — `graph.py` `run_agent(history, message)`: LangGraph tool-calling loop over `ChatGoogleGenerativeAI` (model from `config.yaml`). Tools in `agent/tools/`: `weather` (Open-Meteo geocode+forecast, no key), `web_search` (Tavily), `set_timer_reminder`, `system_status` (psutil). `memory.py` `SessionMemory` is RAM-only history cleared after 10 min inactivity — no persistence by design.
- **Background monitor** (`src/monitor/background_monitor.py`) — QTimers that poll psutil (alert thresholds in `config.yaml`), fire reminders registered by the `set_timer_reminder` tool, and emit an idle fact/joke from `data/facts_jokes.json`. Alerts stay until the user clicks the pet (`_on_pet_clicked` clears both behavior and monitor alert state).
- `random_fact_or_joke` is ambient behavior in the monitor, **not** an LLM tool.

## Conventions

- Every file starts with a module docstring; every class and function gets a docstring.
- Keep the chat window and overlay always-on-top; only the overlay is click-through.
