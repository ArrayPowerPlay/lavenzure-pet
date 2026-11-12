# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Calcifer-style desktop pet for **Windows only, single monitor, personal use** (fan-art of a copyrighted character — never distribute or use original film assets). A flame character lives in an always-on-top transparent window, wanders around the screen, reacts to clicks/drags, and opens a chat bubble (right-click menu → Chat) backed by a tool-calling LangGraph agent on Gemini.

Design docs (Vietnamese) are the source of truth for decisions — read them before changing behavior, and update them when a design decision changes:
- `docs/CONTEXT.md` — goals, architecture diagram, locked technical decisions table, change log (§7).
- `docs/implementation_plan.md` — phase checklist, current status and the A-F roadmap.
- `docs/DECISION_LOG.md` — dated log of decisions agreed with the user, plus open questions. Append to it whenever a decision is made.
- `docs/ANIMATION_TUTORIAL.md` — superseded PNG-cutout plan (kept for reference only).

The user writes in Vietnamese; all **on-screen pet lines** (click reactions, facts/jokes, alerts) must be **English**.

## Environment & commands

The repo lives on the Windows drive at `D:\workspace\pet` (WSL path `/mnt/d/workspace/pet`; an older copy under the WSL home is stale) and has **two venvs** (both git-untracked):

- `.venv-win` — **Windows** venv (Python 3.13, PySide6, includes `pywin32`). Use it for the real app: run it from WSL and real windows open on the Windows desktop. Required for `src/main.py`, autostart and (future) PyInstaller packaging, since the pet is Windows-only.
- `.venv` — **Linux** venv (Python 3.12, no `pywin32`). Only for quick animation previews through WSLg; transparency / always-on-top / click-through behave differently there, so never use it to judge overlay behavior.

```bash
.venv-win/Scripts/python.exe src/main.py                        # run the app (real Windows desktop)
.venv-win/Scripts/python.exe -m pip install -r requirements.txt # install deps (Windows venv)
QT_QPA_PLATFORM=offscreen .venv-win/Scripts/python.exe src/main.py   # headless smoke test
.venv-win/Scripts/python.exe src/autostart/install_startup.py   # create Startup-folder shortcut (pythonw.exe)
.venv-win/Scripts/python.exe src/character_preview.py [renderer ...]  # compare flame renderers, try every mood/motion
.venv-win/Scripts/python.exe src/perf_check.py --minutes 60          # CPU/RAM/GPU of the real app (quit the running pet first)
.venv-win/Scripts/python.exe src/desktop_check.py                     # read-only always-on-top / click-through checks of the running pet
.venv-win/Scripts/python.exe src/bake_flame.py                  # re-run the offline fire sim for the `baked` renderer
.venv/bin/python src/character_preview.py                       # same preview via WSLg (Linux venv)
.venv-win/Scripts/python.exe -m pip install -r requirements-dev.txt  # pytest + ruff
.venv-win/Scripts/python.exe -m pytest                         # headless test suite (tests/)
.venv-win/Scripts/python.exe -m ruff check .                   # lint (config in pyproject.toml)
```

- If `.venv-win/Scripts/*.exe` gives "Permission denied" from WSL after recreating the venv, run `chmod +x .venv-win/Scripts/*.exe`.
- The Linux venv is installed from `requirements.txt` minus the `pywin32` line (it has no Linux wheel).
- `src/` is the import root: modules use `import config`, `from overlay.x import ...` (no `src.` prefix). Run scripts as `src/main.py` (script dir goes on `sys.path`), or set `PYTHONPATH=src`.
- Tests run headless (`tests/conftest.py` sets `QT_QPA_PLATFORM=offscreen` and fakes network/psutil); `pyproject.toml` puts `src` on the path. No build step yet; packaging (PyInstaller) is deferred.
- `src/agent/graph.py` builds the Gemini client lazily on the first chat message, so the app starts without `GEMINI_API_KEY` (the chat then says a key is needed). Model is `gemini-flash-lite-latest` (no thinking; chosen 2026-11-13 because `gemini-flash-latest` = 3.8-flash took 4-8 s per reply) on the `v1beta` endpoint (`llm.api_version`); `-latest` aliases don't exist on `v1`. Env vars only reach the Windows python through `WSLENV`, e.g. `QT_QPA_PLATFORM=offscreen WSLENV=QT_QPA_PLATFORM ...` (`PYTHONPATH` is not forwarded — scratch scripts should `sys.path.insert` the `src` dir).
- Logs: `%LOCALAPPDATA%\Lavenzure\logs\lavenzure.log` (rotating; includes uncaught exceptions).
- To inspect the character without a display, render `FlameCharacter.paint()` into a `QImage` under `QT_QPA_PLATFORM=offscreen` and save a PNG.
- Secrets: copy `.env.example` → `.env` with `GEMINI_API_KEY`, `TAVILY_API_KEY`. Non-secret settings live in `config.yaml`, read via `config.get("dotted.path", default)`.
- Line endings are mixed (most `src/overlay/*.py` and the Markdown docs are CRLF, many others LF; git stores LF via `.gitattributes`). Preserve each file's existing endings.

## Architecture

Single process, single `QApplication`. `main()` sets up logging (`app_logging.py`), then `single_instance.py` (`QLockFile` + `QLocalServer`) makes sure only one pet runs — a second start pings the first, which opens its chat, and exits. `src/main.py` (`LavenzureApp`) constructs every component and wires them together with Qt signals — components don't reference each other directly; trace behavior by following the connections in `_wire_signals`.

- **Overlay** (`src/overlay/`):
  - `character.py` `FlameCharacter` — the pet itself, drawn entirely in code (no image assets). Plain model+renderer, not a widget: `update(dt, window_pos, cursor)` then `paint(painter)`. Body language (lean, stretch, landing squash, walking hops, embers trailing in screen space) is **derived from the window's own movement**, so movement code never animates the body directly. Mood priority: transient `play(mood, seconds)` > alert > sleep (`set_sleeping`) > thinking > riding the log (`set_riding`) > normal; `set_night(amount)` switches to the muted night palette and calmer fire; `talk(seconds)` moves the mouth on top of any mood. It owns these parts:
    - `face.py` `Face` — eyes/lids/brows/mouth; all face parameters blend via the `Expression` dataclass with springs, anticipation kicks and a mouth delay. `MOOD_TARGETS` maps each `Mood` to one or more `Expression` variants (one picked at random per start, e.g. the two happy faces). `Expression` also carries the body shape (`body_w`, `body_h`, `boxy`, `jag`, `arms`, `snooze`), which only the `shader` renderer fully understands. Every feature is scaled to stay inside the face safe-area ellipse on the yellow body. Expressions follow the user's picked reference figures (`docs/references/calcipher_picked.jpg`, local only, never committed). When the user asks for a face to be copied exactly, trace it into `face_refs.py` (eye radial profiles + lip curves in reference-image pixels) and blend it in with an `Expression` weight (`fig1`, `fig7`) instead of tuning parameters.
    - `props.py` — `LogProp` (the log ridden while airborne: pops in with sparks, crumbles into embers), `PanProp` (frying pan with bacon and eggs for `chill`), `Snores` (floating "z"s while asleep).
    - `flame_common.py` — shared body geometry (`BODY_*`, `FACE_*`), `FireWeather` (calm/gust/crackle/lull), the `FlameRenderer` interface (`flare`, `step(FlameDrive)`, `paint(painter, FlameColors)`, `top_points` for ember spawns) and `make_flame_renderer()`.
    - Flame body renderer, chosen by `character.flame_renderer` (default and user-chosen: `shader`): `metaball` (`fire_field.py`, numpy metaballs), `shader` (`flame_shader.py`, GLSL on an offscreen QOpenGL 3.3 context, read back to a QImage) or `baked` (`flame_baked.py`, plays back `assets/flame/baked_flame.npz`, regenerated with `src/bake_flame.py`). `shader`/`baked` fall back to `metaball` if they fail to start.
  - `overlay_window.py` `OverlaySprite` — frameless, `WindowStaysOnTopHint | Tool`, translucent; runs the frame timer (`character.fps`) and hosts `.character`. Keeps a float window position (`exactPos` Qt property; move the pet with `set_exact_pos`, not `move`) and draws the sub-pixel remainder as an offset; its frame loop is a `QAbstractAnimation` so it ticks in the same pass as the movement animations. Emits `clicked` (press+release without moving), `drag_started`/`drag_ended` (after a 6px threshold), `right_clicked`. Click-through relies on Windows per-pixel-alpha hit-testing of layered windows — do **not** add `setMask()` (it would clip the glow/embers); keep the glow fading to alpha 0.
  - `behavior.py` `BehaviorController` — `PetState` machine: IDLE/WALK/FLOAT/JUMP random loop weighted by `behavior.state_weights`, plus DRAGGED, REACT, ALERT, CHAT (stand still), SETTLE (glide down to sleep) and SLEEP. Overrides are flags resolved by `_resume()` in priority order: dragging > alert > reacting > chatting > resting (`set_resting`, menu Idle) / dozing (`set_dozing`) > wandering, so a drag, chat or alert wakes a sleeping pet and it goes back to sleep afterwards. Left-click reactions are methods decorated with `@reaction("name")`; the decorator registers them in `REACTIONS`, so a new animation joins the click pool just by being defined (`play_random_reaction` never repeats the last one; alert/sleep are not reactions). The `speak` reaction emits `speak_requested` (main shows a line from `data/click_reactions.json`). Airborne = riding the log (`_update_riding`). `set_night` slows movement. It moves the *whole window* (`animation.py`: speed-based moves, parabolic jump). Uses restartable single-shot `QTimer`s, not `QTimer.singleShot`, so stale timeouts can't double-advance the loop.
  - `speech_bubble.py` — separate top-level window built with an anchor callback (`sprite.bubble_anchor`); while visible it re-centres over the pet every ~16 ms so it follows movement. `show_text(text, auto_hide_ms)`; `auto_hide_ms=None` = sticky (alerts, `is_sticky()`). Jokes/short replies never replace a sticky alert; while the pet is hidden, `LavenzureApp._say` uses a tray notification instead.
- **Chat** (`src/chat/chat_bubble.py` `ChatBubble`) — a speech-bubble window attached to the pet (follows it via an anchor callback); emits `message_sent` / `closed`; auto-closes after `chat.auto_close_seconds` without chatting (not while typing or waiting for the AI). Main runs the agent in a fresh `QThread` + `AgentWorker` and posts the reply back via signals. Never call the agent on the UI thread. User text is inserted as plain text (escaped); Lavenzure's replies are rendered from Markdown. Each reply starts with an emotion tag (`agent/emotion.py` `split_emotion`): the tag stays in memory, the chat shows clean text and the pet plays that mood for 5 s (`[other]` = no change).
- **UI** (`src/ui/`) — `menus.py` (`themed_menu()` cream/maroon `QMenu`; `PetMenu` right-click menu Chat / Idle↔Wander), `tray_icon.py` (tray icon rendered from `FlameCharacter`), `settings_window.py` (empty placeholder). Tray menu: Hide/Show Pet, Settings, Quit App. Worker failures are turned into in-character English messages by `agent/errors.py` (`friendly_error`), with the traceback logged.
- **Agent** (`src/agent/`) — `graph.py` `run_agent(history, message)`: LangGraph tool-calling loop over `ChatGoogleGenerativeAI` (model from `config.yaml`). Tools in `agent/tools/`: `weather` (Open-Meteo geocode+forecast, no key), `web_search` (Tavily), `system_status` (psutil); `set_timer_reminder` exists but is not in `graph.TOOLS` (reminders switched off). The system prompt asks for the user's language and a leading emotion tag. Tools catch their own network/API errors and return text so a failure never aborts the whole turn. `memory.py` `SessionMemory` is RAM-only history cleared after `chat.idle_timeout_minutes` (15) without chatting — no persistence by design.
- **Background monitor** (`src/monitor/background_monitor.py`) — QTimers that poll psutil (alert thresholds in `config.yaml`), fire reminders registered by the `set_timer_reminder` tool (the tool runs on the worker thread; `schedule_reminder` only emits a queued signal, so reminder state stays on the UI thread; due reminders call `BehaviorController.trigger_notice`), and emit an idle fact/joke from `data/facts_jokes.json`. Alerts stay until the user clicks the pet (`_on_pet_clicked` clears both behavior and monitor alert state).
- **User activity** (`src/monitor/user_activity.py` `UserActivityWatcher`) — polls Windows `GetLastInputInfo` and the clock every second: `dozing_changed` after `behavior.doze_after_minutes` without input (wakes on input), `night_changed` for `behavior.night_start_hour`..`night_end_hour` (night never forces sleep).
- `random_fact_or_joke` is ambient behavior in the monitor, **not** an LLM tool; it is skipped while the pet sleeps.

## Conventions

- Every file starts with a module docstring; every class and function gets a docstring.
- Keep the chat bubble and overlay always-on-top; only the overlay is click-through.
